"""Real SQLite FK/unique enforcement behind a small PostgREST-shaped adapter.

No remote database or provider access. SQLite validates admission ordering and
compensation, not PostgreSQL RPC/locking behavior (covered separately).
"""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier, Lock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers import generations
from app.services import generation_lock


class DatabaseError(Exception):
    def __init__(self, error):
        super().__init__(str(error))
        self.code = "23505" if "UNIQUE" in str(error) else "23503"


class Database:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.mutex = Lock()
        self.fail = None
        self.barrier = None
        self.connection.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE users(id TEXT PRIMARY KEY);
            INSERT INTO users VALUES ('user-123');
            CREATE TABLE generations(
                id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id),
                idempotency_key TEXT, status TEXT DEFAULT 'pending', payload TEXT,
                UNIQUE(user_id,idempotency_key));
            CREATE TABLE generation_locks(
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL);
            CREATE TABLE idempotency_records(
                id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                generation_id TEXT REFERENCES generations(id) ON DELETE SET NULL,
                scope TEXT, idempotency_key TEXT, request_hash TEXT,
                response_status INTEGER, response_body TEXT,
                status TEXT CHECK(status IN ('processing','succeeded','failed')),
                UNIQUE(user_id,scope,idempotency_key));
        """)

    def table(self, name):
        return Query(self, name)

    def rows(self, table):
        return self.table(table).select("*").execute().data


class Query:
    def __init__(self, db, table):
        self.db, self.name = db, table
        self.filters, self.action, self.data, self.single = [], "select", None, False

    def select(self, *_):
        return self

    def maybe_single(self):
        self.single = True
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def insert(self, data):
        self.action, self.data = "insert", data.copy()
        return self

    def delete(self):
        self.action = "delete"
        return self

    def update(self, data):
        self.action, self.data = "update", data.copy()
        return self

    def execute(self):
        where = " AND ".join(f"{key}=?" for key, _ in self.filters) or "1=1"
        args = [value for _, value in self.filters]
        point = (self.name, self.action)
        if self.db.fail == (*point, "before"):
            self.db.fail = None
            raise RuntimeError("injected before write")
        with self.db.mutex:
            try:
                if self.action == "insert":
                    data = self.data
                    if self.name == "generations":
                        self.data.setdefault(
                            "created_at", datetime.now(timezone.utc).isoformat()
                        )
                        data = {
                            k: data[k]
                            for k in ("id", "user_id", "idempotency_key", "status")
                            if k in data
                        }
                        data["payload"] = json.dumps(self.data)
                    if self.name == "idempotency_records":
                        data.setdefault("id", str(uuid4()))
                    self.db.connection.execute(
                        f"INSERT INTO {self.name} ({','.join(data)}) VALUES ({','.join('?' for _ in data)})",
                        list(data.values()),
                    )
                    rows = [self.data | data]
                elif self.action == "update":
                    rows = []
                    for previous in self.db.connection.execute(
                        f"SELECT * FROM {self.name} WHERE {where}", args
                    ).fetchall():
                        previous = dict(previous)
                        if self.name == "generations":
                            payload = json.loads(previous["payload"]) | self.data
                            self.db.connection.execute(
                                "UPDATE generations SET payload=?,status=? WHERE id=?",
                                [
                                    json.dumps(payload),
                                    payload["status"],
                                    previous["id"],
                                ],
                            )
                            rows.append(payload)
                        else:
                            # Response metadata is not part of admission constraints.
                            data = {k: v for k, v in self.data.items() if k in previous}
                            if isinstance(data.get("response_body"), dict):
                                data["response_body"] = json.dumps(data["response_body"])
                            self.db.connection.execute(
                                f"UPDATE {self.name} SET {','.join(k + '=?' for k in data)} WHERE {where}",
                                [*data.values(), *args],
                            )
                            rows.append(previous | data)
                elif self.action == "delete":
                    self.db.connection.execute(
                        f"DELETE FROM {self.name} WHERE {where}", args
                    )
                    rows = []
                else:
                    rows = [
                        dict(row)
                        for row in self.db.connection.execute(
                            f"SELECT * FROM {self.name} WHERE {where}", args
                        )
                    ]
                    if self.name == "generations":
                        rows = [json.loads(row["payload"]) | row for row in rows]
                self.db.connection.commit()
                if self.name == "idempotency_records":
                    rows = [row | {"response_body": json.loads(row["response_body"])}
                            if isinstance(row.get("response_body"), str) else row for row in rows]
            except sqlite3.IntegrityError as error:
                self.db.connection.rollback()
                raise DatabaseError(error) from error
        if self.db.fail == (*point, "after"):
            self.db.fail = None
            raise RuntimeError("injected lost response after committed write")
        if self.db.barrier and point == ("generation_locks", "select"):
            self.db.barrier.wait(timeout=5)
        return SimpleNamespace(
            data=(rows[0] if rows else None) if self.single else rows
        )


@pytest.fixture
def db(monkeypatch):
    database = Database()
    monkeypatch.setattr(generations, "get_service_client", lambda: database)
    monkeypatch.setattr(generation_lock, "get_service_client", lambda: database)
    yield database
    assert database.connection.execute("PRAGMA foreign_key_check").fetchall() == []
    database.connection.close()


def admit(key="admission-test-key", generation_id=None):
    generation_id = generation_id or uuid4()
    return generations._admit_generation(
        user_id="user-123",
        generation_id=generation_id,
        idempotency_key=key,
        request_hash="hash",
        generation_row={
            "id": str(generation_id),
            "user_id": "user-123",
            "idempotency_key": key,
            "status": "pending",
        },
    )


def assert_empty(db):
    for table in ("generations", "generation_locks", "idempotency_records"):
        assert db.rows(table) == []


def test_old_order_reproduces_real_foreign_key_failure(db):
    with pytest.raises(DatabaseError) as caught:
        generation_lock.acquire_generation_lock(
            user_id="user-123", generation_id=uuid4()
        )
    assert caught.value.code == "23503"
    assert_empty(db)


def test_idempotency_also_requires_generation(db):
    with pytest.raises(DatabaseError, match="FOREIGN KEY"):
        db.table("idempotency_records").insert(
            {
                "user_id": "user-123",
                "generation_id": str(uuid4()),
                "scope": "image_generation",
                "idempotency_key": "key",
                "request_hash": "hash",
                "status": "processing",
            }
        ).execute()
    assert_empty(db)


def test_success_uses_actual_lock_and_linked_idempotency(db):
    result = admit()
    assert result["generation_id"] == db.rows("generations")[0]["id"]
    assert db.rows("generation_locks")[0]["generation_id"] == result["generation_id"]


@pytest.mark.parametrize("same_key", [True, False])
def test_rejected_admission_preserves_winner(db, same_key):
    admit()
    before = {
        t: db.rows(t)
        for t in ("generations", "generation_locks", "idempotency_records")
    }
    with pytest.raises(HTTPException) as caught:
        admit("admission-test-key" if same_key else "different-key")
    assert caught.value.status_code == 409
    assert {t: db.rows(t) for t in before} == before


def test_idempotency_collision_after_lock_cleans_only_loser(db):
    winner = admit()
    db.table("generation_locks").delete().eq(
        "generation_id", winner["generation_id"]
    ).execute()
    # Existing historical rows can have a null generation idempotency key.
    db.connection.execute("UPDATE generations SET idempotency_key=NULL")
    db.connection.commit()
    with pytest.raises(HTTPException):
        admit()
    assert len(db.rows("generations")) == len(db.rows("idempotency_records")) == 1
    assert db.rows("idempotency_records")[0]["generation_id"] == winner["generation_id"]
    assert db.rows("generation_locks") == []


@pytest.mark.parametrize(
    "table", ["generations", "generation_locks", "idempotency_records"]
)
@pytest.mark.parametrize("timing", ["before", "after"])
def test_partial_failure_and_lost_response_cleanup(db, table, timing):
    db.fail = (table, "insert", timing)
    with pytest.raises(HTTPException):
        admit()
    assert_empty(db)


def test_concurrent_admission_has_one_winner(db):
    db.barrier = Barrier(2)

    def attempt(key):
        try:
            return admit(key)
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["first-key", "second-key"]))
    db.barrier = None
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 409 in results
    assert all(
        len(db.rows(t)) == 1
        for t in ("generations", "generation_locks", "idempotency_records")
    )


def test_same_key_concurrent_admission_preserves_single_parent(db):
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
    assert all(
        len(db.rows(t)) == 1
        for t in ("generations", "generation_locks", "idempotency_records")
    )


@pytest.mark.parametrize("failed_delete", ["generation_locks", "idempotency_records"])
def test_cleanup_failure_is_reported_and_other_cleanup_attempted(db, monkeypatch, failed_delete):
    original = generations._create_idempotency_record

    def fail(**kwargs):
        original(**kwargs)
        db.fail = (failed_delete, "delete", "before")
        raise RuntimeError("admission response lost")

    monkeypatch.setattr(generations, "_create_idempotency_record", fail)
    with pytest.raises(HTTPException) as caught:
        admit()
    assert caught.value.status_code == 503
    assert caught.value.detail["error"]["code"] == "GENERATION_ADMISSION_CLEANUP_FAILED"
    if failed_delete == "generation_locks":
        assert_empty(db)  # parent cascade removes the lock
    else:
        assert db.rows("generation_locks") == []
        assert db.rows("generations")[0]["status"] == "failed"
        record = db.rows("idempotency_records")[0]
        assert record["status"] == "failed"
        assert record["generation_id"] == db.rows("generations")[0]["id"]


@pytest.mark.parametrize(
    "mode", ["success", "credits_rejected", "invalid_logo", "unsupported_provider"]
)
def test_endpoint_with_real_admission_constraints(db, monkeypatch, mode):
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient

    from app.core.auth import User, get_current_user
    from app.main import app
    from app.services.credits import CreditsError
    from app.services.providers.base import ProviderResult
    from tests.test_generation_endpoint import VALID_BRIEF, FakeStorage

    db.storage = FakeStorage()
    provider = AsyncMock(
        return_value=ProviderResult(image_bytes=b"fake", request_id="test-request")
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
        lambda: SimpleNamespace(
            provider="gemini" if mode == "unsupported_provider" else "openai",
            model="test-model",
            api_key="fake",
        ),
    )
    monkeypatch.setattr(generations, "enforce_generation_rate_limit", lambda **_: None)
    monkeypatch.setattr(generations, "resize_to_preset", lambda content, *_: content)
    for name in (
        "reserve_generation_slot",
        "commit_generation_slot",
        "release_generation_slot",
    ):
        monkeypatch.setattr(generations, name, lambda **_: None)

    def reserve(**_):
        if mode == "credits_rejected":
            raise CreditsError("INSUFFICIENT_CREDITS", "No test credits")
        return SimpleNamespace(amount=1, reservation_id="test-receipt")

    monkeypatch.setattr(generations, "reserve_credits", reserve)
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
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/brands/{uuid4()}/generate",
                headers={"Idempotency-Key": "endpoint-admission-key"},
                json={
                    "brief": VALID_BRIEF,
                    "platform_preset": "instagram_post",
                    "logo_mode": "watermark" if mode == "invalid_logo" else "none",
                },
            )
        assert (
            response.status_code
            == {
                "success": 200,
                "credits_rejected": 402,
                "invalid_logo": 400,
                "unsupported_provider": 503,
            }[mode]
        )
        assert db.rows("generation_locks") == []
        if mode in ("invalid_logo", "unsupported_provider"):
            assert_empty(db)
        else:
            expected = "succeeded" if mode == "success" else "failed"
            assert db.rows("generations")[0]["status"] == expected
            assert db.rows("idempotency_records")[0]["status"] == expected
        assert provider.await_count == (1 if mode == "success" else 0)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
