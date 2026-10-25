"""Fail-closed safety checks for destructive PostgreSQL integration tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.engine import URL, make_url

EXPECTED_HOSTS = frozenset({"127.0.0.1", "localhost"})
SUPPORTED_POSTGRESQL_DRIVERS = frozenset({"postgresql", "postgresql+psycopg"})
EXPECTED_PORT = 55432
EXPECTED_DATABASE = "trendy_integration_test"
EXPECTED_USER = "trendy_test"


class UnsafeTestDatabaseError(RuntimeError):
    """The destructive integration-test target is missing or unsafe."""


def _parse_url(value: str | None, *, setting_name: str) -> URL:
    if not value or not value.strip():
        raise UnsafeTestDatabaseError(f"{setting_name} is required.")
    try:
        parsed = make_url(value)
    except Exception as exc:
        raise UnsafeTestDatabaseError(f"{setting_name} is malformed.") from exc

    if parsed.drivername not in SUPPORTED_POSTGRESQL_DRIVERS:
        raise UnsafeTestDatabaseError(
            f"{setting_name} must use a supported PostgreSQL driver."
        )
    return parsed


def _target_identity(url: URL) -> tuple[str | None, int, str | None, str | None]:
    host = url.host.lower() if url.host else None
    if host in EXPECTED_HOSTS:
        host = "loopback"
    return (
        host,
        url.port or 5432,
        url.database,
        url.username,
    )


def validate_destructive_test_target(
    test_url: str | None,
    *,
    confirmation: str | None,
    normal_database_url: str | None,
) -> str:
    """Return a validated URL or raise without including credentials in errors."""
    if confirmation != "1":
        raise UnsafeTestDatabaseError("ALLOW_DESTRUCTIVE_TEST_DB must equal 1.")

    parsed = _parse_url(test_url, setting_name="TEST_DATABASE_URL")
    identity = _target_identity(parsed)
    expected = (None, EXPECTED_PORT, EXPECTED_DATABASE, EXPECTED_USER)

    if identity[0] != "loopback" or identity[1:] != expected[1:]:
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL must target the designated local integration database."
        )
    if not parsed.password:
        raise UnsafeTestDatabaseError("The local integration database password is required.")
    if parsed.query:
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL query parameters are not allowed.")

    if normal_database_url:
        normal = _parse_url(normal_database_url, setting_name="DATABASE_URL")
        if _target_identity(normal) == identity:
            raise UnsafeTestDatabaseError(
                "TEST_DATABASE_URL must not equal the application's normal database target."
            )

    return test_url.strip()


def prepare_disposable_test_schema(
    test_url: str | None,
    *,
    confirmation: str | None,
    normal_database_url: str | None,
    database_dsn: Callable[[str], str],
    connect: Callable[..., Any],
) -> str:
    """Validate first, then recreate ``public`` on the isolated test database."""
    safe_url = validate_destructive_test_target(
        test_url,
        confirmation=confirmation,
        normal_database_url=normal_database_url,
    )
    dsn = database_dsn(safe_url)
    with connect(dsn, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    return dsn
