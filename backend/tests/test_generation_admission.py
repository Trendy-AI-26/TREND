"""Admission ordering and compensation for POST /brands/{id}/generate.

Runs against ``FakeStore`` (tests/generation_fakes.py): an in-memory model of the
generation tables with the baseline's unique/foreign-key rules. It validates the
order of writes and the cleanup of a failed admission, not PostgreSQL locking.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app import db
from app.routers import generations
from app.services import generation_lock
from tests.generation_fakes import USER_ID
from tests.test_generation_endpoint import VALID_BRIEF

TABLES = ("generations", "generation_locks", "idempotency_records")


def admit(key="admission-test-key", generation_id=None):
    generation_id = generation_id or uuid4()
    return generations._admit_generation(
        user_id=USER_ID,
        generation_id=generation_id,
        idempotency_key=key,
        request_hash="hash",
        generation_row={
            "id": str(generation_id),
            "user_id": USER_ID,
            "idempotency_key": key,
            "status": "pending",
        },
    )


def assert_empty(store):
    for table in TABLES:
        assert store.rows(table) == []


def test_generation_row_is_written_before_lock_and_idempotency_record(store):
    admit()
    assert store.calls == ["insert_generation", "insert_lock", "create_idempotency"]


def test_idempotency_record_requires_an_existing_generation(store):
    with pytest.raises(db.IntegrityError) as caught:
        store.create_idempotency(
            USER_ID, "image_generation", "key", "hash", generation_id=uuid4()
        )
    assert not db.is_unique_violation(caught.value)
    assert_empty(store)


def test_lock_has_no_generation_foreign_key(store):
    # generation_locks.generation_id is informational on this schema.
    generation_lock.acquire_generation_lock(user_id=USER_ID, generation_id=uuid4())
    assert len(store.rows("generation_locks")) == 1


def test_success_links_record_and_lock_to_the_generation(store):
    record = admit()
    generation = store.rows("generations")[0]
    assert record["generation_id"] == generation["id"]
    assert store.rows("generation_locks")[0]["generation_id"] == generation["id"]
    assert record["status"] == "processing"


@pytest.mark.parametrize("same_key", [True, False])
def test_rejected_admission_preserves_the_winner(store, same_key):
    admit()
    before = {table: store.rows(table) for table in TABLES}
    with pytest.raises(HTTPException) as caught:
        admit("admission-test-key" if same_key else "different-key")
    assert caught.value.status_code == 409
    assert caught.value.detail["error"]["code"] == "GENERATION_IN_PROGRESS"
    assert {table: store.rows(table) for table in TABLES} == before


def test_idempotency_collision_after_lock_cleans_only_the_loser(store):
    winner = admit()
    store.locks.clear()  # winner's lock was released
    # Historical rows can carry a null generation idempotency key, so only the
    # idempotency record collides here.
    store.generations[winner["generation_id"]]["idempotency_key"] = None
    with pytest.raises(HTTPException) as caught:
        admit()
    assert caught.value.status_code == 409
    assert len(store.rows("generations")) == len(store.rows("idempotency_records")) == 1
    assert store.rows("idempotency_records")[0]["generation_id"] == winner["generation_id"]
    assert store.rows("generation_locks") == []


@pytest.mark.parametrize("operation", ["insert_generation", "insert_lock", "create_idempotency"])
@pytest.mark.parametrize("timing", ["before", "after"])
def test_partial_failure_and_lost_response_cleanup(store, operation, timing):
    store.fail.add((operation, timing))
    with pytest.raises(HTTPException) as caught:
        admit()
    assert caught.value.status_code == 503
    assert caught.value.detail["error"]["code"] == "GENERATION_ADMISSION_FAILED"
    assert_empty(store)


def test_concurrent_admission_has_one_winner(store):
    start = Barrier(2)

    def attempt(key):
        start.wait(timeout=5)
        try:
            return admit(key)
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["first-key", "second-key"]))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 409 in results
    assert all(len(store.rows(table)) == 1 for table in TABLES)


def test_same_key_concurrent_admission_preserves_a_single_parent(store):
    start = Barrier(2)

    def attempt(_):
        start.wait(timeout=5)
        try:
            return admit()
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 409 in results
    assert all(len(store.rows(table)) == 1 for table in TABLES)


@pytest.mark.parametrize("failed_delete", ["delete_lock", "delete_idempotency"])
def test_cleanup_failure_is_reported_and_other_cleanup_attempted(
    store, monkeypatch, failed_delete
):
    original = generations._create_idempotency_record

    def create_then_lose_response(**kwargs):
        original(**kwargs)
        store.fail.add((failed_delete, "before"))
        raise RuntimeError("admission response lost")

    monkeypatch.setattr(generations, "_create_idempotency_record", create_then_lose_response)
    with pytest.raises(HTTPException) as caught:
        admit()
    assert caught.value.status_code == 503
    assert caught.value.detail["error"]["code"] == "GENERATION_ADMISSION_CLEANUP_FAILED"
    if failed_delete == "delete_lock":
        # Record and generation were still removed; only the lock is left.
        assert store.rows("generations") == []
        assert store.rows("idempotency_records") == []
        assert len(store.rows("generation_locks")) == 1
        # The orphan (its generation no longer exists) is not a recovery case:
        # once expired it must not block the user.
        store.expire_locks()
        generation_lock.acquire_generation_lock(user_id=USER_ID, generation_id=uuid4())
    else:
        assert store.rows("generation_locks") == []
        generation = store.rows("generations")[0]
        record = store.rows("idempotency_records")[0]
        assert generation["status"] == "failed"
        assert record["status"] == "failed"
        # The link is kept for diagnosis and replay.
        assert record["generation_id"] == generation["id"]


@pytest.mark.parametrize(
    "mode", ["success", "credits_rejected", "invalid_logo", "unsupported_provider"]
)
def test_endpoint_with_real_admission_constraints(endpoint, monkeypatch, mode):
    from app.services.credits import CreditsError

    client, provider, store = endpoint
    if mode == "unsupported_provider":
        monkeypatch.setattr(
            generations,
            "resolve_generation_config",
            lambda: SimpleNamespace(provider="gemini", model="test-model", api_key="fake"),
        )
    if mode == "credits_rejected":

        def reject(**_):
            raise CreditsError("INSUFFICIENT_CREDITS", "No test credits")

        monkeypatch.setattr(generations, "reserve_credits", reject)

    response = client.post(
        f"/brands/{uuid4()}/generate",
        headers={"Idempotency-Key": "endpoint-admission-key"},
        json={
            "brief": VALID_BRIEF,
            "platform_preset": "instagram_post",
            "logo_mode": "watermark" if mode == "invalid_logo" else "none",
        },
    )
    expected_status = {
        "success": 200,
        "credits_rejected": 402,
        "invalid_logo": 400,
        "unsupported_provider": 503,
    }[mode]
    assert response.status_code == expected_status
    assert store.rows("generation_locks") == []
    if mode in ("invalid_logo", "unsupported_provider"):
        # Rejected before admission: nothing was written.
        assert_empty(store)
    else:
        expected = "succeeded" if mode == "success" else "failed"
        assert store.rows("generations")[0]["status"] == expected
        assert store.rows("idempotency_records")[0]["status"] == expected
    assert provider.await_count == (1 if mode == "success" else 0)
