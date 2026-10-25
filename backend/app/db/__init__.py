"""Database access layer (SQLAlchemy Core on psycopg v3)."""

from app.db.session import (
    DBAPIError,
    IntegrityError,
    Tx,
    execute,
    fetch_all,
    fetch_one,
    get_engine,
    is_unique_violation,
    json_param,
    reset_engine,
    transaction,
)

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
