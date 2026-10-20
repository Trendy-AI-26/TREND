from uuid import uuid4

import pytest

from app.routers import generations
from app.services import generation_lock
from app.services.credits import CreditsError
from app.services.providers.base import ProviderError
from tests import test_generation_idempotency as idempotency
from tests.test_generation_admission import admit

db = idempotency.db
endpoint = idempotency.endpoint


def request(client, key="settlement-intent-key", brand=None):
    return client.post(
        f"/brands/{brand or uuid4()}/generate",
        json=idempotency.payload(),
        headers={"Idempotency-Key": key},
    )


def test_success_is_not_published_before_both_commits(endpoint, monkeypatch):
    client, _, database = endpoint
    calls = []

    def commit(*args, **kwargs):
        assert database.rows("generations")[0]["status"] == "processing"
        assert database.storage.bucket.uploaded_files
        calls.append("commit")

    monkeypatch.setattr(generations, "commit_credits", commit)
    monkeypatch.setattr(generations, "commit_generation_slot", commit)
    assert request(client).status_code == 200
    assert len(calls) == 2


def test_logging_failure_does_not_undo_success(endpoint, monkeypatch):
    client, _, database = endpoint

    def fail(**_):
        raise RuntimeError("logging unavailable")

    monkeypatch.setattr(
        generations,
        "UsageTimer",
        lambda **_: type(
            "Timer",
            (),
            {
                "start": lambda _: None,
                "finish": lambda _, **kw: fail(**kw),
                "usage_id": "test",
            },
        )(),
    )
    assert request(client).status_code == 200
    assert database.rows("generations")[0]["status"] == "succeeded"


def test_failed_settlement_preserves_output_and_retry_does_not_redispatch(
    endpoint, monkeypatch
):
    client, provider, database = endpoint
    brand = uuid4()
    releases = []

    def fail(_):
        raise CreditsError("CREDITS_OPERATION_FAILED", "lost commit response")

    monkeypatch.setattr(generations, "commit_credits", fail)
    monkeypatch.setattr(
        generations, "release_credits", lambda _: releases.append("credit")
    )
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    first = request(client, brand=brand)
    assert first.status_code == 503
    assert database.rows("generations")[0]["status"] == "processing"
    assert database.storage.bucket.uploaded_files
    assert releases == []
    monkeypatch.setattr(generations, "commit_credits", lambda _: None)
    assert request(client, brand=brand).status_code == 200
    assert provider.await_count == 1


def test_timeout_is_unknown_and_does_not_release_reservations(endpoint, monkeypatch):
    client, provider, database = endpoint
    provider.side_effect = ProviderError("TIMEOUT", "unknown")
    releases = []
    monkeypatch.setattr(
        generations, "release_credits", lambda _: releases.append("credit")
    )
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    response = request(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GENERATION_OUTCOME_UNKNOWN"
    assert database.rows("generations")[0]["status"] == "processing"
    assert releases == []


def test_provider_failure_attempts_both_releases_independently(endpoint, monkeypatch):
    client, provider, database = endpoint
    provider.side_effect = ProviderError("INVALID_KEY", "rejected")
    calls = []

    def fail(**_):
        calls.append("quota")
        raise RuntimeError("quota unavailable")

    monkeypatch.setattr(generations, "release_generation_slot", fail)
    monkeypatch.setattr(
        generations, "release_credits", lambda _: calls.append("credit")
    )
    response = request(client)
    assert response.status_code == 503
    assert calls == ["quota", "credit"]
    assert (
        database.rows("idempotency_records")[0]["response_body"]["phase"]
        == "cleanup_pending"
    )


def test_expired_lock_does_not_authorize_takeover_of_unfinished_generation(db):
    admit()
    db.table("generation_locks").update(
        {"expires_at": "2000-01-01T00:00:00+00:00"}
    ).execute()
    old = db.rows("generation_locks")[0]
    with pytest.raises(generation_lock.GenerationLockError):
        generation_lock.acquire_generation_lock(
            user_id="user-123", generation_id=uuid4()
        )
    assert db.rows("generation_locks") == [old]


def test_old_owner_cannot_release_new_owner_lock(db):
    admit()
    old = db.rows("generation_locks")[0]
    generation_lock.release_generation_lock(user_id="user-123", generation_id=uuid4())
    assert db.rows("generation_locks") == [old]


@pytest.mark.parametrize("point", ["quota", "generation", "idempotency"])
def test_interrupted_settlement_replays_original_receipt(endpoint, monkeypatch, point):
    client, provider, database = endpoint
    brand = uuid4()
    receipts = []

    def commit(reservation):
        receipts.append(reservation)
        if point == "generation":
            database.fail = ("generations", "update", "after")
        elif point == "idempotency":
            database.fail = ("idempotency_records", "update", "before")

    monkeypatch.setattr(generations, "commit_credits", commit)

    def quota(**_):
        if point == "quota":
            raise RuntimeError("quota commit response lost")

    monkeypatch.setattr(generations, "commit_generation_slot", quota)
    assert request(client, brand=brand).status_code == 503
    assert (
        database.rows("idempotency_records")[0]["response_body"]["phase"]
        == "output_ready"
    )
    monkeypatch.setattr(
        generations, "commit_credits", lambda receipt: receipts.append(receipt)
    )
    monkeypatch.setattr(generations, "commit_generation_slot", lambda **_: None)
    assert request(client, brand=brand).status_code == 200
    assert receipts[0] == receipts[1]
    assert provider.await_count == 1
    assert database.rows("generation_locks") == []


def test_cleanup_retry_is_bounded_and_does_not_redispatch(endpoint, monkeypatch):
    client, provider, database = endpoint
    brand = uuid4()
    provider.side_effect = ProviderError("INVALID_KEY", "rejected")
    calls = []

    def fail(_):
        calls.append("credit")
        raise RuntimeError("release unavailable")

    monkeypatch.setattr(generations, "release_credits", fail)
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: calls.append("quota")
    )
    assert request(client, brand=brand).status_code == 503
    assert request(client, brand=brand).status_code == 503
    assert calls == ["quota", "credit", "quota", "credit"]
    monkeypatch.setattr(generations, "release_credits", lambda _: None)
    assert request(client, brand=brand).status_code == 502
    assert database.rows("generations")[0]["status"] == "failed"
    assert database.rows("generation_locks") == []
    assert provider.await_count == 1


@pytest.mark.parametrize("code", ["TIMEOUT", "NETWORK", "PROVIDER_SERVER_ERROR"])
def test_unknown_outcome_replays_without_dispatch_or_expired_lock_takeover(
    endpoint, code
):
    client, provider, database = endpoint
    brand = uuid4()
    provider.side_effect = ProviderError(code, "unknown")
    assert request(client, brand=brand).status_code == 503
    assert request(client, brand=brand).status_code == 503
    database.table("generation_locks").update(
        {"expires_at": "2000-01-01T00:00:00+00:00"}
    ).execute()
    assert (
        request(client, key="another-generation-intent", brand=brand).status_code == 409
    )
    assert len(database.rows("generations")) == 1
    assert provider.await_count == 1


def test_checkpoint_lost_response_retains_output_for_replay(endpoint, monkeypatch):
    client, provider, database = endpoint
    brand = uuid4()
    upload = database.storage.bucket.upload

    def upload_then_fail(*args, **kwargs):
        result = upload(*args, **kwargs)
        database.fail = ("idempotency_records", "update", "after")
        return result

    monkeypatch.setattr(database.storage.bucket, "upload", upload_then_fail)
    assert request(client, brand=brand).status_code == 503
    assert database.rows("generations")[0]["status"] == "processing"
    assert request(client, brand=brand).status_code == 200
    assert provider.await_count == 1


def test_lock_cleanup_failure_cannot_downgrade_success(endpoint, monkeypatch):
    client, _, database = endpoint

    def fail(**_):
        raise RuntimeError("lock delete unavailable")

    monkeypatch.setattr(generations, "release_generation_lock", fail)
    assert request(client).status_code == 200
    assert database.rows("generations")[0]["status"] == "succeeded"


def test_ambiguous_credit_reserve_response_is_not_refunded(endpoint, monkeypatch):
    client, provider, database = endpoint

    def fail(**_):
        raise CreditsError("CREDITS_RPC_EMPTY_RESPONSE", "lost response")

    monkeypatch.setattr(generations, "reserve_credits", fail)
    assert request(client).status_code == 503
    assert (
        database.rows("idempotency_records")[0]["response_body"]["phase"]
        == "outcome_unknown"
    )
    assert provider.await_count == 0


def test_stale_expiry_read_cannot_delete_a_replacement_lock(db, monkeypatch):
    from tests.test_generation_admission import Query

    admit()
    old = db.rows("generations")[0]
    generations._mark_failed(old["id"], "TEST_REJECTION", "rejected")
    db.table("generation_locks").update(
        {"expires_at": "2000-01-01T00:00:00+00:00"}
    ).execute()
    replacement = str(uuid4())
    db.table("generations").insert(
        {"id": replacement, "user_id": "user-123", "status": "pending"}
    ).execute()
    execute = Query.execute

    def raced_execute(query):
        if query.name == "generation_locks" and query.action == "delete":
            db.table("generation_locks").update(
                {
                    "generation_id": replacement,
                    "expires_at": "2099-01-01T00:00:00+00:00",
                }
            ).execute()
        return execute(query)

    monkeypatch.setattr(Query, "execute", raced_execute)
    with pytest.raises(generation_lock.GenerationLockError):
        generation_lock.acquire_generation_lock(
            user_id="user-123", generation_id=replacement
        )
    assert db.rows("generation_locks")[0]["generation_id"] == replacement


def test_checkpoint_failure_before_write_blocks_without_refunding(
    endpoint, monkeypatch
):
    client, provider, database = endpoint
    brand = uuid4()
    upload = database.storage.bucket.upload

    def uploaded(*args, **kwargs):
        upload(*args, **kwargs)
        database.fail = ("idempotency_records", "update", "before")

    monkeypatch.setattr(database.storage.bucket, "upload", uploaded)
    releases = []
    monkeypatch.setattr(
        generations, "release_credits", lambda _: releases.append("credit")
    )
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    assert request(client, brand=brand).status_code == 503
    assert request(client, brand=brand).status_code == 409
    assert database.storage.bucket.uploaded_files
    assert releases == []
    assert provider.await_count == 1
    assert database.rows("generation_locks")


def test_simultaneous_settlement_replays_use_identical_receipts(endpoint, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi.testclient import TestClient

    from app.main import app

    client, provider, database = endpoint
    brand = uuid4()

    def fail(_):
        raise RuntimeError("commit response lost")

    monkeypatch.setattr(generations, "commit_credits", fail)
    assert request(client, brand=brand).status_code == 503
    barrier = Barrier(2)
    receipts = []

    def commit(receipt):
        receipts.append(receipt)
        barrier.wait(timeout=5)

    monkeypatch.setattr(generations, "commit_credits", commit)

    def replay(_):
        # Separate event loops model separate deployed workers. Sync DB calls
        # serialize requests within a single ASGI loop.
        with TestClient(app) as worker:
            return request(worker, brand=brand)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(replay, range(2)))
    assert [response.status_code for response in results] == [200, 200]
    assert receipts[0] == receipts[1]
    assert provider.await_count == 1
    assert database.rows("generation_locks") == []


@pytest.mark.asyncio
async def test_provider_cancellation_preserves_reservations_and_lock(
    endpoint, monkeypatch
):
    import asyncio

    from app.core.auth import User
    from app.models.generation import GenerateRequest

    _, provider, database = endpoint
    provider.side_effect = asyncio.CancelledError()
    releases = []
    monkeypatch.setattr(
        generations, "release_credits", lambda _: releases.append("credit")
    )
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    with pytest.raises(asyncio.CancelledError):
        await generations.generate_image(
            brand_id=uuid4(),
            body=GenerateRequest.model_validate(idempotency.payload()),
            current_user=User(
                id="user-123", email="test@example.invalid", access_token="fake"
            ),
            idempotency_key="cancelled-generation-intent",
        )
    assert (
        database.rows("idempotency_records")[0]["response_body"]["phase"]
        == "outcome_unknown"
    )
    assert database.rows("generation_locks")
    assert releases == []
