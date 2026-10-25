from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app import db

_TERMINAL_STATUSES = ("succeeded", "failed")


class GenerationLockError(RuntimeError):
    pass


def acquire_generation_lock(
    *,
    user_id: str,
    generation_id: UUID,
    ttl_seconds: int = 180,
) -> None:
    """Take the single per-user generation lock.

    An expired lock only counts as stale when the generation that owned it is
    terminal (or no longer exists). An expired lock whose generation is still
    pending/processing belongs to a request that may have reached the provider
    and needs recovery, so it is never taken over automatically.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    try:
        with db.transaction() as tx:
            current = tx.fetch_one(
                "SELECT generation_id, expires_at FROM generation_locks "
                "WHERE user_id = CAST(:user_id AS uuid) FOR UPDATE",
                {"user_id": user_id},
                raw=True,
            )
            if current is not None:
                if current["expires_at"] > now:
                    raise GenerationLockError("A generation is already in progress.")

                previous = tx.fetch_one(
                    "SELECT status FROM generations WHERE id = CAST(:id AS uuid)",
                    {"id": str(current["generation_id"])},
                )
                # generation_locks.generation_id has no foreign key, so a lock
                # can outlive a generation that was deleted or never inserted:
                # that is an orphan, safe to replace. Only a live, unfinished
                # generation blocks the takeover.
                if previous is not None and previous["status"] not in _TERMINAL_STATUSES:
                    raise GenerationLockError("The previous generation needs recovery.")

                # Delete exactly the lock row we read, never a replacement.
                tx.execute(
                    "DELETE FROM generation_locks "
                    "WHERE user_id = CAST(:user_id AS uuid) "
                    "AND generation_id = CAST(:generation_id AS uuid) "
                    "AND expires_at = :expires_at",
                    {
                        "user_id": user_id,
                        "generation_id": str(current["generation_id"]),
                        "expires_at": current["expires_at"],
                    },
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
    except GenerationLockError:
        raise
    except Exception as exc:
        # Only a primary-key conflict means another request holds the lock;
        # any other database fault must not be disguised as "in progress".
        if db.is_unique_violation(exc):
            raise GenerationLockError("A generation is already in progress.") from exc
        raise


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
