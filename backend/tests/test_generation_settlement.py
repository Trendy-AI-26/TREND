"""Settlement, recovery and lock behaviour of POST /brands/{id}/generate.

Uses ``FakeStore`` (tests/generation_fakes.py). The credit/quota functions are
replaced by recorders, so these tests check the order and independence of the
settlement steps, not the SQL behind them (see migration 0003).
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.auth import User
from app.main import app
from app.models.generation import GenerateRequest
from app.routers import generations
from app.services import generation_lock
from app.services.credits import CreditsError
from app.services.providers.base import ProviderError
from app.services.quota import QuotaError
from tests.generation_fakes import USER_ID
from tests.test_generation_admission import admit
from tests.test_generation_idempotency import payload


def request(client, key="settlement-intent-key", brand=None):
    return client.post(
        f"/brands/{brand or uuid4()}/generate",
        json=payload(),
        headers={"Idempotency-Key": key},
    )


def phase(store):
    return store.rows("idempotency_records")[0]["response_body"]["phase"]


def test_success_is_not_published_before_both_commits(endpoint, monkeypatch):
    client, _, store = endpoint
    calls = []

    def commit(*args, **kwargs):
        assert store.rows("generations")[0]["status"] == "processing"
        assert store.objects
        calls.append("commit")

    monkeypatch.setattr(generations, "commit_credits", commit)
    monkeypatch.setattr(generations, "commit_generation_slot", commit)
    assert request(client).status_code == 200
    assert len(calls) == 2
    assert store.rows("generations")[0]["status"] == "succeeded"
    assert store.rows("idempotency_records")[0]["status"] == "succeeded"
    assert store.rows("generation_locks") == []


def test_logging_failure_does_not_undo_success(endpoint, monkeypatch):
    client, _, store = endpoint

    def fail(**_):
        raise RuntimeError("logging unavailable")

    monkeypatch.setattr(
        generations,
        "UsageTimer",
        lambda **_: SimpleNamespace(usage_id="test", start=lambda: None, finish=fail),
    )
    assert request(client).status_code == 200
    assert store.rows("generations")[0]["status"] == "succeeded"


def test_usage_start_failure_does_not_block_generation(endpoint, monkeypatch):
    client, provider, _ = endpoint

    def fail():
        raise RuntimeError("usage insert failed")

    monkeypatch.setattr(
        generations,
        "UsageTimer",
        lambda **_: SimpleNamespace(usage_id=None, start=fail, finish=lambda **_: None),
    )
    assert request(client).status_code == 200
    assert provider.await_count == 1


def test_failed_settlement_preserves_output_and_retry_does_not_redispatch(
    endpoint, monkeypatch
):
    client, provider, store = endpoint
    brand = uuid4()
    releases = []

    def fail(_):
        raise CreditsError("CREDITS_OPERATION_FAILED", "lost commit response")

    monkeypatch.setattr(generations, "commit_credits", fail)
    monkeypatch.setattr(generations, "release_credits", lambda _: releases.append("credit"))
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    first = request(client, brand=brand)
    assert first.status_code == 503
    assert first.json()["error"]["code"] == "GENERATION_SETTLEMENT_PENDING"
    assert store.rows("generations")[0]["status"] == "processing"
    assert store.objects
    assert releases == []  # an uncertain commit is never refunded
    monkeypatch.setattr(generations, "commit_credits", lambda _: None)
    assert request(client, brand=brand).status_code == 200
    assert provider.await_count == 1


def test_timeout_is_unknown_and_does_not_release_reservations(endpoint, monkeypatch):
    client, provider, store = endpoint
    provider.side_effect = ProviderError("TIMEOUT", "unknown")
    releases = []
    monkeypatch.setattr(generations, "release_credits", lambda _: releases.append("credit"))
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    response = request(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GENERATION_OUTCOME_UNKNOWN"
    assert store.rows("generations")[0]["status"] == "processing"
    assert phase(store) == "outcome_unknown"
    assert releases == []


def test_provider_failure_attempts_both_releases_independently(endpoint, monkeypatch):
    client, provider, store = endpoint
    provider.side_effect = ProviderError("INVALID_KEY", "rejected")
    calls = []

    def fail(**_):
        calls.append("quota")
        raise RuntimeError("quota unavailable")

    monkeypatch.setattr(generations, "release_generation_slot", fail)
    monkeypatch.setattr(generations, "release_credits", lambda _: calls.append("credit"))
    response = request(client)
    assert response.status_code == 503
    assert calls == ["quota", "credit"]
    assert phase(store) == "cleanup_pending"


def test_quota_rejection_finalizes_without_reserving_credits(endpoint, monkeypatch):
    client, provider, store = endpoint
    reserved = []

    def reject(**_):
        raise QuotaError("DAILY_GENERATION_LIMIT_REACHED", "daily limit")

    monkeypatch.setattr(generations, "reserve_generation_slot", reject)
    monkeypatch.setattr(generations, "reserve_credits", lambda **_: reserved.append(1))
    response = request(client)
    assert response.status_code == 402
    assert response.json()["error"]["code"] == "DAILY_GENERATION_LIMIT_REACHED"
    assert reserved == []
    assert store.rows("generations")[0]["status"] == "failed"
    record = store.rows("idempotency_records")[0]
    assert (record["status"], record["response_status"]) == ("failed", 402)
    assert store.rows("generation_locks") == []
    provider.assert_not_awaited()


@pytest.mark.parametrize("point", ["quota", "generation", "idempotency"])
def test_interrupted_settlement_replays_original_receipt(endpoint, monkeypatch, point):
    client, provider, store = endpoint
    brand = uuid4()
    receipts = []

    def commit(reservation):
        receipts.append(reservation)
        if point == "generation":
            store.fail.add(("mark_succeeded", "after"))
        elif point == "idempotency":
            store.fail.add(("finish_idempotency", "before"))

    monkeypatch.setattr(generations, "commit_credits", commit)

    def quota(**_):
        if point == "quota":
            raise RuntimeError("quota commit response lost")

    monkeypatch.setattr(generations, "commit_generation_slot", quota)
    assert request(client, brand=brand).status_code == 503
    assert phase(store) == "output_ready"
    monkeypatch.setattr(generations, "commit_credits", lambda receipt: receipts.append(receipt))
    monkeypatch.setattr(generations, "commit_generation_slot", lambda **_: None)
    assert request(client, brand=brand).status_code == 200
    assert receipts[0] == receipts[1]
    assert provider.await_count == 1
    assert store.rows("generation_locks") == []


def test_cleanup_retry_is_bounded_and_does_not_redispatch(endpoint, monkeypatch):
    client, provider, store = endpoint
    brand = uuid4()
    provider.side_effect = ProviderError("INVALID_KEY", "rejected")
    calls = []

    def fail(_):
        calls.append("credit")
        raise RuntimeError("release unavailable")

    monkeypatch.setattr(generations, "release_credits", fail)
    monkeypatch.setattr(generations, "release_generation_slot", lambda **_: calls.append("quota"))
    assert request(client, brand=brand).status_code == 503
    assert request(client, brand=brand).status_code == 503
    assert calls == ["quota", "credit", "quota", "credit"]
    monkeypatch.setattr(generations, "release_credits", lambda _: None)
    assert request(client, brand=brand).status_code == 502
    assert store.rows("generations")[0]["status"] == "failed"
    assert store.rows("generation_locks") == []
    assert provider.await_count == 1


@pytest.mark.parametrize("code", ["TIMEOUT", "NETWORK", "PROVIDER_SERVER_ERROR"])
def test_unknown_outcome_replays_without_dispatch_or_expired_lock_takeover(endpoint, code):
    client, provider, store = endpoint
    brand = uuid4()
    provider.side_effect = ProviderError(code, "unknown")
    assert request(client, brand=brand).status_code == 503
    assert request(client, brand=brand).status_code == 503
    store.expire_locks()
    other = request(client, key="another-generation-intent", brand=brand)
    assert other.status_code == 409
    assert len(store.rows("generations")) == 1
    assert provider.await_count == 1


def test_checkpoint_lost_response_retains_output_for_replay(endpoint, monkeypatch):
    client, provider, store = endpoint
    brand = uuid4()
    upload = store.upload

    def upload_then_lose_checkpoint_response(*args, **kwargs):
        upload(*args, **kwargs)
        store.fail.add(("save_checkpoint", "after"))

    monkeypatch.setattr(generations.storage, "upload", upload_then_lose_checkpoint_response)
    assert request(client, brand=brand).status_code == 503
    assert store.rows("generations")[0]["status"] == "processing"
    assert request(client, brand=brand).status_code == 200
    assert provider.await_count == 1


def test_lock_cleanup_failure_cannot_downgrade_success(endpoint, monkeypatch):
    client, _, store = endpoint

    def fail(**_):
        raise RuntimeError("lock delete unavailable")

    monkeypatch.setattr(generations, "release_generation_lock", fail)
    assert request(client).status_code == 200
    assert store.rows("generations")[0]["status"] == "succeeded"


def test_ambiguous_credit_reserve_response_is_not_refunded(endpoint, monkeypatch):
    client, provider, store = endpoint
    releases = []

    def fail(**_):
        raise CreditsError("CREDITS_RPC_EMPTY_RESPONSE", "lost response")

    monkeypatch.setattr(generations, "reserve_credits", fail)
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    assert request(client).status_code == 503
    assert phase(store) == "outcome_unknown"
    assert releases == []
    assert provider.await_count == 0


def test_checkpoint_failure_before_write_blocks_without_refunding(endpoint, monkeypatch):
    client, provider, store = endpoint
    brand = uuid4()
    upload = store.upload

    def uploaded(*args, **kwargs):
        upload(*args, **kwargs)
        store.fail.add(("save_checkpoint", "before"))

    monkeypatch.setattr(generations.storage, "upload", uploaded)
    releases = []
    monkeypatch.setattr(generations, "release_credits", lambda _: releases.append("credit"))
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    assert request(client, brand=brand).status_code == 503
    assert request(client, brand=brand).status_code == 409
    assert store.objects
    assert releases == []
    assert provider.await_count == 1
    assert store.rows("generation_locks")


def test_simultaneous_settlement_replays_use_identical_receipts(endpoint, monkeypatch):
    client, provider, store = endpoint
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
        # Separate clients (and event loops) model separate deployed workers.
        return request(TestClient(app), brand=brand)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(replay, range(2)))
    assert [response.status_code for response in results] == [200, 200]
    assert receipts[0] == receipts[1]
    assert provider.await_count == 1
    assert store.rows("generation_locks") == []


@pytest.mark.asyncio
async def test_provider_cancellation_preserves_reservations_and_lock(endpoint, monkeypatch):
    _, provider, store = endpoint
    provider.side_effect = asyncio.CancelledError()
    releases = []
    monkeypatch.setattr(generations, "release_credits", lambda _: releases.append("credit"))
    monkeypatch.setattr(
        generations, "release_generation_slot", lambda **_: releases.append("quota")
    )
    with pytest.raises(asyncio.CancelledError):
        await generations.generate_image(
            brand_id=uuid4(),
            body=GenerateRequest.model_validate(payload()),
            current_user=User(id=USER_ID, email="test@example.invalid", access_token="fake"),
            idempotency_key="cancelled-generation-intent",
        )
    assert phase(store) == "outcome_unknown"
    assert store.rows("generation_locks")
    assert releases == []


# --------------------------------------------------------------- lock rules


def test_live_lock_blocks_a_second_generation(store):
    admit()
    with pytest.raises(generation_lock.GenerationLockError):
        generation_lock.acquire_generation_lock(user_id=USER_ID, generation_id=uuid4())


def test_expired_lock_of_a_finished_generation_is_replaced(store):
    admit()
    generation = store.rows("generations")[0]
    generations._mark_failed(generation["id"], "TEST_REJECTION", "rejected")
    store.expire_locks()
    new_id = uuid4()
    generation_lock.acquire_generation_lock(user_id=USER_ID, generation_id=new_id)
    assert [lock["generation_id"] for lock in store.rows("generation_locks")] == [str(new_id)]


def test_expired_lock_does_not_authorize_takeover_of_unfinished_generation(store):
    admit()
    store.expire_locks()
    old = store.rows("generation_locks")
    with pytest.raises(generation_lock.GenerationLockError, match="recovery"):
        generation_lock.acquire_generation_lock(user_id=USER_ID, generation_id=uuid4())
    assert store.rows("generation_locks") == old


def test_old_owner_cannot_release_new_owner_lock(store):
    admit()
    old = store.rows("generation_locks")
    generation_lock.release_generation_lock(user_id=USER_ID, generation_id=uuid4())
    assert store.rows("generation_locks") == old


def test_non_conflict_database_error_is_not_reported_as_lock_held(store):
    store.fail.add(("insert_lock", "before"))
    with pytest.raises(RuntimeError, match="injected"):
        generation_lock.acquire_generation_lock(user_id=USER_ID, generation_id=uuid4())


def test_stale_expiry_read_cannot_delete_a_replacement_lock(store, monkeypatch):
    admit()
    old = store.rows("generations")[0]
    generations._mark_failed(old["id"], "TEST_REJECTION", "rejected")
    store.expire_locks()
    replacement = str(uuid4())
    store.generations[replacement] = {"id": replacement, "user_id": USER_ID, "status": "pending"}
    original = store._delete_lock

    def raced(params, conditional):
        # Another request replaced the expired lock between our read and delete.
        store.locks[USER_ID] = {
            "generation_id": replacement,
            "expires_at": datetime(2099, 1, 1, tzinfo=timezone.utc),
        }
        return original(params, conditional)

    monkeypatch.setattr(store, "_delete_lock", raced)
    with pytest.raises(generation_lock.GenerationLockError):
        generation_lock.acquire_generation_lock(user_id=USER_ID, generation_id=uuid4())
    assert store.rows("generation_locks")[0]["generation_id"] == replacement
