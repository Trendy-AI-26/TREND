"""Unit-level tests for the migration runner (ordering, idempotency, locking)."""

import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.db import migrate


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeConnection:
    """Records every statement; keeps schema_migrations in memory."""

    def __init__(self, applied=None, fail_on=None):
        self.applied = dict(applied or {})
        self.log = []
        self.fail_on = fail_on
        self.in_tx = False
        self.tx_log = []
        self.lock_held = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @contextmanager
    def transaction(self):
        self.in_tx = True
        self.tx_log.append("BEGIN")
        snapshot = dict(self.applied)
        try:
            yield
        except Exception:
            self.applied = snapshot
            self.tx_log.append("ROLLBACK")
            raise
        else:
            self.tx_log.append("COMMIT")
        finally:
            self.in_tx = False

    def execute(self, sql, params=None):
        self.log.append((sql.strip(), params))
        text = sql.strip()
        if "pg_advisory_lock" in text:
            self.lock_held = True
        elif "pg_advisory_unlock" in text:
            self.lock_held = False
        elif text.startswith("SELECT filename, checksum"):
            return FakeCursor(list(self.applied.items()))
        elif text.startswith("INSERT INTO schema_migrations"):
            assert self.in_tx, "bookkeeping row must commit with the migration"
            self.applied[params[0]] = params[1]
        elif self.fail_on and self.fail_on in text:
            raise RuntimeError("boom")
        elif not text.startswith("CREATE TABLE IF NOT EXISTS schema_migrations"):
            assert self.in_tx, "migration SQL must run inside a transaction"
        return FakeCursor([])


def _write(directory: Path, name: str, sql: str) -> None:
    (directory / name).write_text(sql, encoding="utf-8")


@pytest.fixture
def tmp_path():
    with tempfile.TemporaryDirectory() as directory:
        yield Path(directory)


@pytest.fixture
def migrations_dir(tmp_path):
    _write(tmp_path, "0002_second.sql", "-- second\nSELECT 2;")
    _write(tmp_path, "0001_baseline.sql", "-- first\nSELECT 1;")
    _write(tmp_path, "0010_tenth.sql", "-- tenth\nSELECT 10;")
    _write(tmp_path, "notes.txt", "ignored")
    return tmp_path


def _run(conn, directory):
    return migrate.run_migrations("dsn", directory, connect=lambda *a, **k: conn)


def test_files_are_listed_in_filename_order_and_only_sql(migrations_dir):
    names = [p.name for p in migrate.list_migration_files(migrations_dir)]

    assert names == ["0001_baseline.sql", "0002_second.sql", "0010_tenth.sql"]


def test_shipped_baseline_is_discovered_first():
    files = migrate.list_migration_files()

    assert files and files[0].name == "0001_baseline.sql"


def test_pending_migrations_run_in_order_each_in_a_transaction(migrations_dir):
    conn = FakeConnection()

    applied = _run(conn, migrations_dir)

    assert applied == ["0001_baseline.sql", "0002_second.sql", "0010_tenth.sql"]
    executed = [sql for sql, _ in conn.log if sql.startswith("-- ")]
    assert executed == ["-- first\nSELECT 1;", "-- second\nSELECT 2;", "-- tenth\nSELECT 10;"]
    assert conn.tx_log == ["BEGIN", "COMMIT"] * 3
    assert set(conn.applied) == {"0001_baseline.sql", "0002_second.sql", "0010_tenth.sql"}


def test_rerun_is_idempotent(migrations_dir):
    conn = FakeConnection()
    _run(conn, migrations_dir)
    log_after_first = len(conn.log)

    second = _run(conn, migrations_dir)

    assert second == []
    new_statements = [sql for sql, _ in conn.log[log_after_first:] if sql.startswith("-- ")]
    assert new_statements == []


def test_only_new_files_are_applied(migrations_dir):
    conn = FakeConnection()
    _run(conn, migrations_dir)
    _write(migrations_dir, "0011_eleventh.sql", "-- eleventh\nSELECT 11;")

    assert _run(conn, migrations_dir) == ["0011_eleventh.sql"]


def test_advisory_lock_is_taken_before_and_released_after(migrations_dir):
    conn = FakeConnection()

    _run(conn, migrations_dir)

    statements = [sql for sql, _ in conn.log]
    assert "pg_advisory_lock" in statements[0]
    assert "pg_advisory_unlock" in statements[-1]
    assert conn.log[0][1] == (migrate.ADVISORY_LOCK_KEY,)
    assert conn.lock_held is False
    # The bookkeeping table exists before anything is read from it.
    create_at = next(i for i, s in enumerate(statements) if "CREATE TABLE IF NOT EXISTS schema_migrations" in s)
    select_at = next(i for i, s in enumerate(statements) if s.startswith("SELECT filename"))
    assert 0 < create_at < select_at


def test_failure_rolls_back_stops_and_releases_the_lock(migrations_dir):
    _write(migrations_dir, "0002_second.sql", "-- second\nBROKEN;")
    conn = FakeConnection(fail_on="BROKEN")

    with pytest.raises(RuntimeError):
        _run(conn, migrations_dir)

    assert set(conn.applied) == {"0001_baseline.sql"}
    assert conn.tx_log == ["BEGIN", "COMMIT", "BEGIN", "ROLLBACK"]
    assert conn.lock_held is False
    assert not any("tenth" in sql for sql, _ in conn.log)


def test_editing_an_applied_migration_is_refused(migrations_dir):
    conn = FakeConnection()
    _run(conn, migrations_dir)
    _write(migrations_dir, "0001_baseline.sql", "-- first, edited\nSELECT 1;")

    with pytest.raises(migrate.MigrationError):
        _run(conn, migrations_dir)


def test_plan_migrations_skips_applied_and_keeps_order(migrations_dir):
    files = migrate.list_migration_files(migrations_dir)
    first_sql = migrate.read_sql(files[0])

    plan = migrate.plan_migrations(files, {files[0].name: migrate.checksum(first_sql)})

    assert [path.name for path, _ in plan] == ["0002_second.sql", "0010_tenth.sql"]


def test_bom_is_stripped_and_checksum_is_stable(tmp_path):
    (tmp_path / "0001_a.sql").write_bytes(b"\xef\xbb\xbfSELECT 1;")

    sql = migrate.read_sql(tmp_path / "0001_a.sql")

    assert sql == "SELECT 1;"
    assert migrate.checksum(sql) == migrate.checksum("SELECT 1;")


def test_database_dsn_drops_the_sqlalchemy_driver_suffix():
    dsn = migrate.database_dsn("postgresql+psycopg://user:p%40ss@db:5432/trendy")

    assert dsn.startswith("postgresql://user:p%40ss@db:5432/trendy")


def test_baseline_has_no_hosted_platform_specific_objects():
    sql = migrate.read_sql(migrate.list_migration_files()[0])
    # Comments may explain what was removed; only executable SQL matters.
    code = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    lowered = code.lower()

    for forbidden in (
        "auth.users",
        "auth.uid",
        "storage.",
        "vault.",
        "notify pgrst",
        "service_role",
        "anon",
        "enable row level security",
        "create policy",
    ):
        assert forbidden not in lowered, forbidden
    assert "begin;" not in lowered and "commit;" not in lowered


def test_baseline_defines_the_required_auth_tables():
    sql = migrate.read_sql(migrate.list_migration_files()[0])

    for fragment in (
        "CREATE TABLE users (",
        "CREATE TABLE auth_codes (",
        "CREATE UNIQUE INDEX uq_users_email_ci ON users (lower(email))",
        "'verify_email', 'reset_password'",
        "encrypted_key TEXT NOT NULL",
    ):
        assert fragment in sql, fragment
