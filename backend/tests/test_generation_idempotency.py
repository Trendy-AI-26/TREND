import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth import User, get_current_user
from app.main import app
from app.models.generation import GenerateRequest
from app.routers import generations
from app.services.providers.base import ProviderResult
from tests import test_generation_admission as admission
from tests.test_generation_endpoint import VALID_BRIEF, FakeStorage

db = admission.db


@pytest.fixture
def endpoint(db, monkeypatch):
    db.storage = FakeStorage()
    provider = AsyncMock(
        return_value=ProviderResult(image_bytes=b"fake", request_id="test")
    )
    monkeypatch.setattr(generations, "openai_generate", provider)
    monkeypatch.setattr(
        generations,
        "_get_brand_or_404",
        lambda **_: {"name": "Test", "logo_path": None},
    )
    monkeypatch.setattr(generations, "_get_brand_kit_context", lambda **_: None)
    monkeypatch.setattr(
        generations,
        "resolve_generation_config",
        lambda: SimpleNamespace(provider="openai", model="test-model", api_key="fake"),
    )
    monkeypatch.setattr(generations, "enforce_generation_rate_limit", lambda **_: None)
    monkeypatch.setattr(generations, "resize_to_preset", lambda content, *_: content)
    for name in (
        "reserve_generation_slot",
        "commit_generation_slot",
        "release_generation_slot",
    ):
        monkeypatch.setattr(generations, name, lambda **_: None)
    monkeypatch.setattr(
        generations, "reserve_credits", lambda **_: SimpleNamespace(amount=1, reservation_id="test-receipt")
    )
    monkeypatch.setattr(generations, "commit_credits", lambda _: None)
    monkeypatch.setattr(generations, "release_credits", lambda _: None)
    monkeypatch.setattr(
        generations,
        "UsageTimer",
        lambda **_: SimpleNamespace(
            usage_id="test", start=lambda: None, finish=lambda **_: None
        ),
    )
    app.dependency_overrides[get_current_user] = lambda: User(
        id="user-123", email="test@example.invalid", access_token="fake"
    )
    with TestClient(app) as client:
        yield client, provider, db
    app.dependency_overrides.pop(get_current_user, None)


def payload():
    return {
        "brief": VALID_BRIEF,
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }


def test_canonical_identity_includes_user_brand_and_validated_defaults():
    brand = uuid4()
    a = GenerateRequest.model_validate(payload())
    b = GenerateRequest.model_validate(dict(reversed(list(payload().items()))))
    hashed = lambda body, user="u", brand_id=brand: (
        generations._hash_generation_request(body, user_id=user, brand_id=brand_id)
    )
    assert hashed(a) == hashed(b)
    assert hashed(a) != hashed(a, user="other")
    assert hashed(a) != hashed(a, brand_id=uuid4())


def test_replay_success_and_collisions_never_call_provider_again(endpoint):
    client, provider, database = endpoint
    url = f"/brands/{uuid4()}/generate"
    headers = {"Idempotency-Key": "stable-generation-key"}
    first = client.post(url, json=payload(), headers=headers)
    assert first.status_code == 200
    replay = client.post(url, json=payload(), headers=headers)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert (
        client.post(
            f"/brands/{uuid4()}/generate", json=payload(), headers=headers
        ).status_code
        == 409
    )
    changed = payload() | {"platform_preset": "instagram_story"}
    mismatch = client.post(url, json=changed, headers=headers)
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert provider.await_count == 1
    assert len(database.rows("generations")) == 1


def test_concurrent_endpoint_retry_does_not_dispatch_twice(endpoint):
    client, provider, database = endpoint
    entered, release = Event(), Event()

    async def blocked(**_):
        entered.set()
        assert await asyncio.to_thread(release.wait, 5)
        return ProviderResult(image_bytes=b"fake", request_id="test")

    provider.side_effect = blocked
    url = f"/brands/{uuid4()}/generate"
    headers = {"Idempotency-Key": "concurrent-request-key"}
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(client.post, url, json=payload(), headers=headers)
        try:
            assert entered.wait(5)
            second = client.post(url, json=payload(), headers=headers)
            assert second.status_code == 409
            assert second.json()["error"]["code"] == "GENERATION_IN_PROGRESS"
        finally:
            release.set()
        assert first.result(timeout=5).status_code == 200
    assert provider.await_count == 1
    assert len(database.rows("generations")) == 1


@pytest.mark.parametrize(
    "state,status", [("pending", 409), ("processing", 409), ("failed", 402)]
)
def test_replay_state_status_without_provider(db, state, status):
    brand = uuid4()
    body = GenerateRequest.model_validate(payload())
    hashed = generations._hash_generation_request(
        body, user_id="user-123", brand_id=brand
    )
    gen = uuid4()
    generations._admit_generation(
        user_id="user-123",
        generation_id=gen,
        idempotency_key="state-request-key",
        request_hash=hashed,
        generation_row={
            "id": str(gen),
            "user_id": "user-123",
            "idempotency_key": "state-request-key",
            "status": state,
            "error_code": "INSUFFICIENT_CREDITS",
            "error_message": "No credits",
        },
    )
    db.table("idempotency_records").update(
        {
            "status": "failed" if state == "failed" else "processing",
            "response_status": 402,
        }
    ).eq("generation_id", str(gen)).execute()
    with pytest.raises(HTTPException) as error:
        generations._get_idempotent_generation(
            user_id="user-123", idempotency_key="state-request-key", request_hash=hashed
        )
    assert error.value.status_code == status


def test_missing_header_rejected_before_writes(endpoint):
    client, provider, database = endpoint
    assert client.post(f"/brands/{uuid4()}/generate", json=payload()).status_code == 400
    assert not database.rows("generations")
    provider.assert_not_awaited()


def test_missing_generation_never_restarts(db):
    db.table("idempotency_records").insert(
        {
            "user_id": "user-123",
            "scope": "image_generation",
            "idempotency_key": "deleted-result-key",
            "request_hash": "hash",
            "status": "failed",
        }
    ).execute()
    with pytest.raises(HTTPException) as error:
        generations._get_idempotent_generation(
            user_id="user-123",
            idempotency_key="deleted-result-key",
            request_hash="hash",
        )
    assert error.value.detail["error"]["code"] == "GENERATION_OUTCOME_UNKNOWN"


def test_provider_failure_replays_original_status_without_redispatch(endpoint):
    from app.services.providers.base import ProviderError

    client, provider, database = endpoint
    provider.side_effect = ProviderError("INVALID_KEY", "Rejected")
    url = f"/brands/{uuid4()}/generate"
    headers = {"Idempotency-Key": "failed-provider-intent"}
    first = client.post(url, json=payload(), headers=headers)
    again = client.post(url, json=payload(), headers=headers)
    assert first.status_code == again.status_code == 502
    assert again.json()["error"]["code"] == "INVALID_KEY"
    assert provider.await_count == 1
    assert len(database.rows("generations")) == 1


def test_authenticated_user_lookup_does_not_replay_another_users_key(db):
    db.table("idempotency_records").insert(
        {
            "user_id": "user-123",
            "scope": "image_generation",
            "idempotency_key": "other-user-intent",
            "request_hash": "hash",
            "status": "failed",
        }
    ).execute()
    assert (
        generations._get_idempotent_generation(
            user_id="other-user",
            idempotency_key="other-user-intent",
            request_hash="hash",
        )
        is None
    )


def test_lookup_failure_does_not_become_a_new_generation(endpoint):
    client, provider, database = endpoint
    database.fail = ("idempotency_records", "select", "before")
    with pytest.raises(RuntimeError, match="injected"):
        client.post(
            f"/brands/{uuid4()}/generate",
            json=payload(),
            headers={"Idempotency-Key": "lookup-failure-key"},
        )
    provider.assert_not_awaited()
    assert database.rows("generations") == []
