"""Plain-SQL migration runner.

Usage (from ``backend/``):  ``python -m app.db.migrate``

* applies ``backend/db/migrations/*.sql`` in filename order;
* records every applied file in ``schema_migrations``;
* runs each file in its own transaction (file + bookkeeping row commit together);
* holds a Postgres advisory lock so concurrent starts cannot race;
* is idempotent: already-applied files are skipped.
"""

from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from app.config import settings

logger = logging.getLogger("app.db.migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"

# Arbitrary constant shared by every runner instance.
ADVISORY_LOCK_KEY = 7_281_934_001

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   text PRIMARY KEY,
    checksum   text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


class MigrationError(RuntimeError):
    pass


def list_migration_files(directory: Path | None = None) -> list[Path]:
    """Return ``*.sql`` files in lexical filename order."""
    directory = Path(directory or MIGRATIONS_DIR)
    return sorted(
        (path for path in directory.glob("*.sql") if path.is_file()),
        key=lambda path: path.name,
    )


def checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def read_sql(path: Path) -> str:
    # utf-8-sig drops a BOM if an editor added one.
    return Path(path).read_text(encoding="utf-8-sig")


def plan_migrations(
    files: Iterable[Path],
    applied: dict[str, str],
) -> list[tuple[Path, str]]:
    """Decide which files still have to run, in order.

    ``applied`` maps filename -> checksum recorded when it ran. A file that was
    applied but has since been edited is an error: change history by adding a
    new migration instead.
    """
    pending: list[tuple[Path, str]] = []
    for path in sorted(files, key=lambda p: p.name):
        sql = read_sql(path)
        digest = checksum(sql)
        recorded = applied.get(path.name)
        if recorded is None:
            pending.append((path, digest))
        elif recorded != digest:
            raise MigrationError(
                f"Migration {path.name} was modified after it was applied "
                "(checksum mismatch). Add a new migration instead of editing it."
            )
    return pending


def database_dsn(url: str | None = None) -> str:
    """Convert the SQLAlchemy URL into a libpq connection string for psycopg."""
    from sqlalchemy.engine import make_url

    parsed = make_url(url or settings.DATABASE_URL)
    return parsed.set(drivername="postgresql").render_as_string(hide_password=False)


def run_migrations(
    dsn: str | None = None,
    directory: Path | None = None,
    *,
    connect: Callable[..., Any] | None = None,
) -> list[str]:
    """Apply pending migrations; return the filenames applied by this call."""
    if connect is None:
        import psycopg

        connect = psycopg.connect

    files = list_migration_files(directory)
    applied_now: list[str] = []

    with connect(dsn or database_dsn(), autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
        try:
            conn.execute(CREATE_TABLE_SQL)
            rows = conn.execute("SELECT filename, checksum FROM schema_migrations").fetchall()
            applied = {row[0]: row[1] for row in rows}

            for path, digest in plan_migrations(files, applied):
                logger.info("Applying migration %s", path.name)
                sql = read_sql(path)
                with conn.transaction():
                    # No parameters here, so psycopg sends the whole file as one
                    # multi-statement simple query.
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s)",
                        (path.name, digest),
                    )
                applied_now.append(path.name)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))

    if not applied_now:
        logger.info("Database schema is up to date")
    return applied_now


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Apply SQL migrations.")
    parser.add_argument("--database-url", default=None, help="Defaults to DATABASE_URL.")
    parser.add_argument("--directory", default=None, help="Defaults to backend/db/migrations.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        applied = run_migrations(
            database_dsn(args.database_url),
            Path(args.directory) if args.directory else None,
        )
    except MigrationError as exc:
        logger.error("%s", exc)
        return 1
    print(f"applied {len(applied)} migration(s)" + (": " + ", ".join(applied) if applied else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
