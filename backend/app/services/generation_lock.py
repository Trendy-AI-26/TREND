from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.supabase import get_service_client


class GenerationLockError(RuntimeError):
    pass


def acquire_generation_lock(
    *,
    user_id: str,
    generation_id: UUID,
    ttl_seconds: int = 180,
) -> None:
    client = get_service_client()

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    existing = (
        client.table("generation_locks")
        .select("*")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    if existing is not None and existing.data is not None:
        current = existing.data

        current_expiry = datetime.fromisoformat(
            current["expires_at"].replace(
                "Z",
                "+00:00",
            )
        )

        if current_expiry > now:
            raise GenerationLockError(
                "A generation is already in progress."
            )

        client.table("generation_locks").delete().eq(
            "user_id",
            user_id,
        ).execute()

    try:
        client.table("generation_locks").insert(
            {
                "user_id": user_id,
                "generation_id": str(generation_id),
                "expires_at": expires_at.isoformat(),
            }
        ).execute()
    except Exception as exc:
        raise GenerationLockError(
            "A generation is already in progress."
        ) from exc


def release_generation_lock(
    *,
    user_id: str,
    generation_id: UUID,
) -> None:
    client = get_service_client()

    client.table("generation_locks").delete().eq(
        "user_id",
        user_id,
    ).eq(
        "generation_id",
        str(generation_id),
    ).execute()
