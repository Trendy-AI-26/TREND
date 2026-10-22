from unittest.mock import Mock

import pytest

from postgres_test_safety import (
    UnsafeTestDatabaseError,
    prepare_disposable_test_schema,
    validate_destructive_test_target,
)

SAFE_URL = (
    "postgresql+psycopg://trendy_test:temporary-password"
    "@127.0.0.1:55432/trendy_integration_test"
)
NORMAL_URL = "postgresql+psycopg://app:secret@127.0.0.1:5432/trendy"


@pytest.mark.parametrize(
    "unsafe_url",
    [
        None,
        "",
        "not-a-database-url",
        "mysql://trendy_test:password@127.0.0.1:55432/trendy_integration_test",
        "postgresql+asyncpg://trendy_test:password@127.0.0.1:55432/trendy_integration_test",
        "postgresqlmalicious://trendy_test:password@127.0.0.1:55432/trendy_integration_test",
        "postgresql+psycopg://trendy_test:password@db.example.com:55432/trendy_integration_test",
        "postgresql+psycopg://trendy_test:password@127.0.0.1:5432/trendy_integration_test",
        "postgresql+psycopg://trendy_test:password@127.0.0.1:55432/trendy",
        "postgresql+psycopg://app:password@127.0.0.1:55432/trendy_integration_test",
        "postgresql+psycopg://trendy_test@127.0.0.1:55432/trendy_integration_test",
        "postgresql+psycopg://trendy_test:password@localhost:55432/trendy_integration_test?sslmode=require",
    ],
)
def test_unsafe_target_is_rejected_before_dsn_parsing_or_connection(unsafe_url):
    database_dsn = Mock(side_effect=AssertionError("DSN parser must not run"))
    connect = Mock(side_effect=AssertionError("connection must not run"))

    with pytest.raises(UnsafeTestDatabaseError):
        prepare_disposable_test_schema(
            unsafe_url,
            confirmation="1",
            normal_database_url=NORMAL_URL,
            database_dsn=database_dsn,
            connect=connect,
        )

    database_dsn.assert_not_called()
    connect.assert_not_called()


def test_confirmation_is_required_before_dsn_parsing_or_connection():
    database_dsn = Mock(side_effect=AssertionError("DSN parser must not run"))
    connect = Mock(side_effect=AssertionError("connection must not run"))

    with pytest.raises(UnsafeTestDatabaseError):
        prepare_disposable_test_schema(
            SAFE_URL,
            confirmation=None,
            normal_database_url=NORMAL_URL,
            database_dsn=database_dsn,
            connect=connect,
        )

    database_dsn.assert_not_called()
    connect.assert_not_called()


def test_normal_application_database_target_is_rejected():
    with pytest.raises(UnsafeTestDatabaseError):
        validate_destructive_test_target(
            SAFE_URL,
            confirmation="1",
            normal_database_url=SAFE_URL,
        )


def test_loopback_alias_of_normal_application_database_target_is_rejected():
    normal_url = (
        "postgresql+psycopg://trendy_test:different-password"
        "@localhost:55432/trendy_integration_test"
    )

    with pytest.raises(UnsafeTestDatabaseError):
        validate_destructive_test_target(
            SAFE_URL,
            confirmation="1",
            normal_database_url=normal_url,
        )


def test_malformed_normal_database_url_is_rejected_before_connection():
    database_dsn = Mock(side_effect=AssertionError("DSN parser must not run"))
    connect = Mock(side_effect=AssertionError("connection must not run"))

    with pytest.raises(UnsafeTestDatabaseError):
        prepare_disposable_test_schema(
            SAFE_URL,
            confirmation="1",
            normal_database_url="://malformed",
            database_dsn=database_dsn,
            connect=connect,
        )

    database_dsn.assert_not_called()
    connect.assert_not_called()


def test_exact_designated_local_target_is_accepted():
    assert validate_destructive_test_target(
        SAFE_URL,
        confirmation="1",
        normal_database_url=NORMAL_URL,
    ) == SAFE_URL
