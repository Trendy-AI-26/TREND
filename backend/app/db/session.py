"""SQLAlchemy engine and small synchronous query helpers.

Rows are returned as plain dicts. By default values are converted to the same
JSON-friendly shapes the API used to receive from PostgREST: UUID -> str,
datetime/date -> ISO-8601 str, Decimal -> float. Pass ``raw=True`` to keep the
native Python types (used by the auth code, which needs real datetimes).
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
import uuid
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator, Mapping

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.config import settings

Params = Mapping[str, Any] | None

__all__ = [
    "DBAPIError",
    "IntegrityError",
    "Tx",
    "execute",
    "fetch_all",
    "fetch_one",
    "get_engine",
    "is_unique_violation",
    "json_param",
    "reset_engine",
    "transaction",
]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        # Keep timestamps in UTC so ISO strings match the old API output.
        connect_args={"options": "-c timezone=UTC", "connect_timeout": 10},
    )


def reset_engine() -> None:
    """Dispose the cached engine (used by tests and after config changes)."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()


def json_param(value: Any) -> str | None:
    """Serialize a value for a ``CAST(:param AS jsonb)`` bind parameter."""
    if value is None:
        return None
    return json.dumps(value, default=_json_default)


def _json_default(value: Any) -> Any:
    converted = _jsonable(value)
    if converted is value:
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
    return converted


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _row(row: Any, raw: bool) -> dict[str, Any]:
    data = dict(row._mapping)
    if raw:
        return data
    return {key: _jsonable(value) for key, value in data.items()}


def is_unique_violation(exc: BaseException, constraint: str | None = None) -> bool:
    """True when ``exc`` is a unique violation (optionally for one constraint)."""
    if not isinstance(exc, IntegrityError):
        return False
    orig = getattr(exc, "orig", None)
    if getattr(orig, "sqlstate", None) != "23505":
        return False
    if constraint is None:
        return True
    diag = getattr(orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name == constraint or constraint in str(exc)


class Tx:
    """Statements bound to one open transaction."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def fetch_all(self, sql: str, params: Params = None, *, raw: bool = False) -> list[dict]:
        result = self._conn.execute(text(sql), dict(params or {}))
        return [_row(row, raw) for row in result.fetchall()]

    def fetch_one(self, sql: str, params: Params = None, *, raw: bool = False) -> dict | None:
        result = self._conn.execute(text(sql), dict(params or {}))
        row = result.fetchone()
        return None if row is None else _row(row, raw)

    def execute(self, sql: str, params: Params = None) -> int:
        result = self._conn.execute(text(sql), dict(params or {}))
        return result.rowcount


@contextmanager
def transaction() -> Iterator[Tx]:
    """Run several statements atomically; commits on success, rolls back on error."""
    with get_engine().begin() as conn:
        yield Tx(conn)


def fetch_all(sql: str, params: Params = None, *, raw: bool = False) -> list[dict]:
    with transaction() as tx:
        return tx.fetch_all(sql, params, raw=raw)


def fetch_one(sql: str, params: Params = None, *, raw: bool = False) -> dict | None:
    with transaction() as tx:
        return tx.fetch_one(sql, params, raw=raw)


def execute(sql: str, params: Params = None) -> int:
    with transaction() as tx:
        return tx.execute(sql, params)
