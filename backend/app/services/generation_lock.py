from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app import db


class GenerationLockError(RuntimeError):
    pass


def acquire_generation_lock(
    *,
    user_id: str,
    generation_id: UUID,
    ttl_seconds: int = 180,
) -> None:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    try:
        with db.transaction() as tx:
            # An expired lock is stale: clear it. A live lock stays and makes
            # the insert below fail on the primary key (one lock per user).
            tx.execute(
                "DELETE FROM generation_locks "
                "WHERE user_id = CAST(:user_id AS uuid) AND expires_at <= :now",
                {"user_id": user_id, "now": now},
            )
            tx.execute(
                "INSERT INTO generation_locks (user_id, generation_id, expires_at) "
                "VALUES (CAST(:user_id AS uuid), CAST(:generation_id AS uuid), :expires_at)",
                {
                    "user_id": user_id,
                    "generation_id": str(generation_id),
                    "expires_at": expires_at,
                },
            )
    except Exception as exc:
        raise GenerationLockError("A generation is already in progress.") from exc


def release_generation_lock(
    *,
    user_id: str,
    generation_id: UUID,
) -> None:
    db.execute(
        "DELETE FROM generation_locks "
        "WHERE user_id = CAST(:user_id AS uuid) "
        "AND generation_id = CAST(:generation_id AS uuid)",
        {"user_id": user_id, "generation_id": str(generation_id)},
    )
