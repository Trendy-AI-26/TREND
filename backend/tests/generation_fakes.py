"""In-memory stand-ins for the generation tables and the seams around them.

``FakeStore`` models the three tables the admission/settlement logic depends on
(``generations``, ``generation_locks``, ``idempotency_records``) with the same
constraints as ``0001_baseline.sql`` that matter here:

* ``generations`` is unique on ``(user_id, idempotency_key)``;
* ``idempotency_records`` is unique on ``(user_id, scope, key)`` and its
  ``generation_id`` is a foreign key (``ON DELETE SET NULL``);
* ``generation_locks`` is keyed by ``user_id`` and has NO foreign key.

Its methods mirror ``app.repositories.generations``; ``install`` patches them
(plus object storage and the ``app.db`` transaction used by
``generation_lock``) the way the other tests in this suite fake repositories.
It validates admission ordering and compensation, not PostgreSQL locking.
"""

from __future__ import annotations

import copy
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app import db

USER_ID = "user-123"


class PgError(Exception):
    """Stands in for the psycopg error carried by ``IntegrityError.orig``."""

    def __init__(self, sqlstate: str, message: str) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


def integrity_error(sqlstate: str, message: str) -> db.IntegrityError:
    return db.IntegrityError("fake statement", {}, PgError(sqlstate, message))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeStore:
    def __init__(self) -> None:
        self.generations: dict[str, dict] = {}
        self.locks: dict[str, dict] = {}
        self.records: list[dict] = []
        self.objects: dict[tuple[str, str], bytes] = {}
        self.calls: list[str] = []
        # {(operation, "before" | "after")}: raise once at that point.
        self.fail: set[tuple[str, str]] = set()
        self.mutex = threading.RLock()

    # ------------------------------------------------------------ plumbing
    def _inject(self, name: str, phase: str) -> None:
        if (name, phase) in self.fail:
            self.fail.discard((name, phase))
            raise RuntimeError(f"injected {phase} {name}")

    @contextmanager
    def _op(self, name: str):
        with self.mutex:
            self._inject(name, "before")
            self.calls.append(name)
            yield
        # "after" models a committed write whose response was lost.
        self._inject(name, "after")

    def rows(self, table: str) -> list[dict]:
        with self.mutex:
            if table == "generations":
                return copy.deepcopy(list(self.generations.values()))
            if table == "idempotency_records":
                return copy.deepcopy(self.records)
            if table == "generation_locks":
                return [
                    {"user_id": user, **copy.deepcopy(lock)}
                    for user, lock in self.locks.items()
                ]
        raise KeyError(table)

    def expire_locks(self) -> None:
        with self.mutex:
            for lock in self.locks.values():
                lock["expires_at"] = datetime(2000, 1, 1, tzinfo=timezone.utc)

    def _record(self, record_id: str) -> dict | None:
        return next((r for r in self.records if r["id"] == str(record_id)), None)

    # ------------------------------------------------ repository: idempotency
    def get_idempotency(self, user_id, scope, idempotency_key):
        with self._op("get_idempotency"):
            found = next(
                (
                    r
                    for r in self.records
                    if (r["user_id"], r["scope"], r["idempotency_key"])
                    == (user_id, scope, idempotency_key)
                ),
                None,
            )
            return copy.deepcopy(found)

    def create_idempotency(
        self, user_id, scope, idempotency_key, request_hash, generation_id=None
    ):
        with self._op("create_idempotency"):
            if generation_id is not None and str(generation_id) not in self.generations:
                raise integrity_error("23503", "idempotency_records_generation_id_fkey")
            if any(
                (r["user_id"], r["scope"], r["idempotency_key"])
                == (user_id, scope, idempotency_key)
                for r in self.records
            ):
                raise integrity_error("23505", "idempotency_records_user_id_scope_key")
            record = {
                "id": str(uuid4()),
                "user_id": user_id,
                "scope": scope,
                "idempotency_key": idempotency_key,
                "request_hash": request_hash,
                "generation_id": None if generation_id is None else str(generation_id),
                "status": "processing",
                "response_status": None,
                "response_body": None,
                "created_at": _now(),
                "completed_at": None,
            }
            self.records.append(record)
            return copy.deepcopy(record)

    def link_idempotency(self, record_id, generation_id):
        with self._op("link_idempotency"):
            self._record(record_id)["generation_id"] = str(generation_id)

    def save_checkpoint(self, record_id, checkpoint):
        with self._op("save_checkpoint"):
            record = self._record(record_id)
            if record is None or record["status"] != "processing":
                return False
            record["response_body"] = copy.deepcopy(checkpoint)
            return True

    def finish_idempotency(self, record_id, status, response_status, completed_at=None):
        with self._op("finish_idempotency"):
            record = self._record(record_id)
            if record is None:
                return False
            record.update(
                status=status,
                response_status=response_status,
                completed_at=completed_at or record["completed_at"],
            )
            return True

    def delete_idempotency_for_generation(self, generation_id):
        with self._op("delete_idempotency"):
            self.records = [
                r for r in self.records if r["generation_id"] != str(generation_id)
            ]

    def fail_idempotency_for_generation(self, generation_id, response_status):
        with self._op("fail_idempotency"):
            for record in self.records:
                if record["generation_id"] == str(generation_id):
                    record.update(status="failed", response_status=response_status)

    # ------------------------------------------------ repository: generations
    def insert_generation(self, values):
        with self._op("insert_generation"):
            key = values.get("idempotency_key")
            if key is not None and any(
                g.get("user_id") == values.get("user_id") and g.get("idempotency_key") == key
                for g in self.generations.values()
            ):
                raise integrity_error("23505", "uq_generations_user_idempotency")
            row = {
                "error_code": None,
                "error_message": None,
                "image_path": None,
                "provider_request_id": None,
                "completed_at": None,
                **copy.deepcopy(values),
                "status": "pending",
                "created_at": _now(),
            }
            self.generations[row["id"]] = row
            return copy.deepcopy(row)

    def mark_processing(self, generation_id):
        with self._op("mark_processing"):
            self.generations[str(generation_id)]["status"] = "processing"

    def mark_succeeded(self, generation_id, image_path, provider_request_id, completed_at):
        with self._op("mark_succeeded"):
            row = self.generations[str(generation_id)]
            row.update(
                status="succeeded",
                image_path=image_path,
                provider_request_id=provider_request_id,
                completed_at=completed_at,
            )
            return copy.deepcopy(row)

    def mark_failed(self, generation_id, code, message, completed_at):
        with self._op("mark_failed"):
            row = self.generations.get(str(generation_id))
            if row is not None:
                row.update(
                    status="failed",
                    error_code=code,
                    error_message=message,
                    completed_at=completed_at,
                )

    def get_generation(self, generation_id):
        with self._op("get_generation"):
            return copy.deepcopy(self.generations.get(str(generation_id)))

    def delete_owned_generation(self, user_id, generation_id):
        with self._op("delete_generation"):
            row = self.generations.get(str(generation_id))
            if row is None or row.get("user_id") != user_id:
                return
            del self.generations[str(generation_id)]
            for record in self.records:  # ON DELETE SET NULL
                if record["generation_id"] == str(generation_id):
                    record["generation_id"] = None

    # ------------------------------------------------------------- storage
    def upload(self, bucket, path, data, content_type="application/octet-stream", *, upsert=True):
        with self._op("upload"):
            self.objects[(bucket, path)] = data

    def download(self, bucket, path):
        return b"fake-logo-bytes"

    # ---------------------------------------- app.db seam used by generation_lock
    def _insert_lock(self, params):
        with self._op("insert_lock"):
            if params["user_id"] in self.locks:
                raise integrity_error("23505", "generation_locks_pkey")
            self.locks[params["user_id"]] = {
                "generation_id": params["generation_id"],
                "expires_at": params["expires_at"],
            }
            return 1

    def _delete_lock(self, params, conditional):
        with self._op("delete_lock"):
            lock = self.locks.get(params["user_id"])
            if lock is None or lock["generation_id"] != params["generation_id"]:
                return 0
            if conditional and lock["expires_at"] != params["expires_at"]:
                return 0
            del self.locks[params["user_id"]]
            return 1


class FakeTx:
    """Answers exactly the statements ``generation_lock`` issues."""

    def __init__(self, store: FakeStore) -> None:
        self.store = store

    def fetch_one(self, sql, params=None, *, raw=False):
        if "FROM generation_locks" in sql:
            lock = self.store.locks.get(params["user_id"])
            return None if lock is None else dict(lock)
        if "FROM generations" in sql:
            row = self.store.generations.get(params["id"])
            return None if row is None else {"status": row["status"]}
        raise AssertionError(f"unexpected SQL: {sql}")

    def execute(self, sql, params=None):
        if sql.startswith("DELETE FROM generation_locks"):
            return self.store._delete_lock(params, conditional="expires_at" in sql)
        if sql.startswith("INSERT INTO generation_locks"):
            return self.store._insert_lock(params)
        raise AssertionError(f"unexpected SQL: {sql}")


REPOSITORY_FUNCTIONS = (
    "get_idempotency",
    "create_idempotency",
    "link_idempotency",
    "save_checkpoint",
    "finish_idempotency",
    "delete_idempotency_for_generation",
    "fail_idempotency_for_generation",
    "insert_generation",
    "mark_processing",
    "mark_succeeded",
    "mark_failed",
    "get_generation",
    "delete_owned_generation",
)


def install(monkeypatch, store: FakeStore) -> None:
    """Route the repository, object storage and lock transaction to ``store``."""
    from app.routers import generations

    for name in REPOSITORY_FUNCTIONS:
        monkeypatch.setattr(generations.gen_repo, name, getattr(store, name))
    monkeypatch.setattr(generations.storage, "upload", store.upload)
    monkeypatch.setattr(generations.storage, "download", store.download)

    @contextmanager
    def transaction():
        with store.mutex:
            yield FakeTx(store)

    def execute(sql, params=None):
        with store.mutex:
            return FakeTx(store).execute(sql, params)

    monkeypatch.setattr(db, "transaction", transaction)
    monkeypatch.setattr(db, "execute", execute)
