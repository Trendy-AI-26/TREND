"""Idempotency-key binding and replay of saved outcomes (no provider re-dispatch)."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.generation import GenerateRequest
from app.routers import generations
from app.services.providers.base import ProviderError, ProviderResult
from tests.generation_fakes import USER_ID
from tests.test_generation_admission import admit
from tests.test_generation_endpoint import VALID_BRIEF


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

    def hashed(body, user="u", brand_id=brand):
        return generations._hash_generation_request(body, user_id=user, brand_id=brand_id)

    assert hashed(a) == hashed(b)
    assert hashed(a) != hashed(a, user="other")
    assert hashed(a) != hashed(a, brand_id=uuid4())
    changed = GenerateRequest.model_validate(payload() | {"platform_preset": "instagram_story"})
    assert hashed(a) != hashed(changed)


def test_replay_success_and_collisions_never_call_provider_again(endpoint):
    client, provider, store = endpoint
    url = f"/brands/{uuid4()}/generate"
    headers = {"Idempotency-Key": "stable-generation-key"}
    first = client.post(url, json=payload(), headers=headers)
    assert first.status_code == 200
    replay = client.post(url, json=payload(), headers=headers)
    assert replay.status_code == 200
    assert replay.json() == first.json()

    # Same key on another brand is a different request.
    other_brand = client.post(f"/brands/{uuid4()}/generate", json=payload(), headers=headers)
    assert other_brand.status_code == 409
    assert other_brand.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    changed = payload() | {"platform_preset": "instagram_story"}
    mismatch = client.post(url, json=changed, headers=headers)
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert provider.await_count == 1
    assert len(store.rows("generations")) == 1


def test_concurrent_endpoint_retry_does_not_dispatch_twice(endpoint):
    client, provider, store = endpoint
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
    assert len(store.rows("generations")) == 1


@pytest.mark.parametrize(
    "state,record_status,status",
    [("pending", "processing", 409), ("processing", "processing", 409), ("failed", "failed", 402)],
)
def test_replay_state_status_without_provider(store, state, record_status, status):
    brand = uuid4()
    body = GenerateRequest.model_validate(payload())
    hashed = generations._hash_generation_request(body, user_id=USER_ID, brand_id=brand)
    record = admit("state-request-key-1")
    # Admission stores a fixed hash; rewrite it to the one this request computes.
    store.records[0]["request_hash"] = hashed
    generation = store.generations[record["generation_id"]]
    generation.update(
        status=state,
        error_code="INSUFFICIENT_CREDITS",
        error_message="No credits",
    )
    store.records[0].update(status=record_status, response_status=402)
    with pytest.raises(HTTPException) as error:
        generations._get_idempotent_generation(
            user_id=USER_ID, idempotency_key="state-request-key-1", request_hash=hashed
        )
    assert error.value.status_code == status
    if state == "failed":
        assert error.value.detail["error"]["code"] == "INSUFFICIENT_CREDITS"


def test_missing_header_rejected_before_writes(endpoint):
    client, provider, store = endpoint
    response = client.post(f"/brands/{uuid4()}/generate", json=payload())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert store.rows("generations") == []
    assert store.calls == []
    provider.assert_not_awaited()


def test_short_header_is_a_validation_error(endpoint):
    client, provider, store = endpoint
    response = client.post(
        f"/brands/{uuid4()}/generate", json=payload(), headers={"Idempotency-Key": "short"}
    )
    assert response.status_code == 400
    assert store.calls == []
    provider.assert_not_awaited()


def test_missing_generation_never_restarts(store):
    store.records.append(
        {
            "id": str(uuid4()),
            "user_id": USER_ID,
            "scope": "image_generation",
            "idempotency_key": "deleted-result-key",
            "request_hash": "hash",
            "generation_id": None,  # ON DELETE SET NULL after the row was removed
            "status": "failed",
            "response_status": None,
            "response_body": None,
            "completed_at": None,
        }
    )
    with pytest.raises(HTTPException) as error:
        generations._get_idempotent_generation(
            user_id=USER_ID, idempotency_key="deleted-result-key", request_hash="hash"
        )
    assert error.value.status_code == 409
    assert error.value.detail["error"]["code"] == "GENERATION_OUTCOME_UNKNOWN"


def test_provider_failure_replays_original_status_without_redispatch(endpoint):
    client, provider, store = endpoint
    provider.side_effect = ProviderError("INVALID_KEY", "Rejected")
    url = f"/brands/{uuid4()}/generate"
    headers = {"Idempotency-Key": "failed-provider-intent"}
    first = client.post(url, json=payload(), headers=headers)
    again = client.post(url, json=payload(), headers=headers)
    assert first.status_code == again.status_code == 502
    assert again.json()["error"]["code"] == "INVALID_KEY"
    assert provider.await_count == 1
    assert len(store.rows("generations")) == 1


def test_another_users_key_is_never_replayed(store):
    admit("other-user-intent-1")
    assert (
        generations._get_idempotent_generation(
            user_id="other-user", idempotency_key="other-user-intent-1", request_hash="hash"
        )
        is None
    )


def test_lookup_failure_does_not_become_a_new_generation(endpoint):
    client, provider, store = endpoint
    store.fail.add(("get_idempotency", "before"))
    with pytest.raises(RuntimeError, match="injected"):
        client.post(
            f"/brands/{uuid4()}/generate",
            json=payload(),
            headers={"Idempotency-Key": "lookup-failure-key"},
        )
    provider.assert_not_awaited()
    assert store.rows("generations") == []
