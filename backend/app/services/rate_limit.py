from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.supabase import get_service_client


class RateLimitExceeded(RuntimeError):
    pass


def check_generation_rate_limit(
    *,
    user_id: str,
    limit: int = 5,
    window_seconds: int = 60,
) -> None:
    client = get_service_client()

    now = datetime.now(timezone.utc)

    if window_seconds <= 0:
        raise ValueError("Rate-limit window must be positive.")

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    elapsed_seconds = int((now - epoch).total_seconds())
    window_start = epoch + timedelta(
        seconds=elapsed_seconds - elapsed_seconds % window_seconds
    )

    result = (
        client.table("rate_limit_buckets")
        .select("*")
        .eq("user_id", user_id)
        .eq("bucket", "image_generation")
        .eq(
            "window_started_at",
            window_start.isoformat(),
        )
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        client.table("rate_limit_buckets").insert(
            {
                "user_id": user_id,
                "bucket": "image_generation",
                "window_started_at": (window_start.isoformat()),
                "request_count": 1,
            }
        ).execute()
        return

    row = result.data

    if int(row["request_count"]) >= limit:
        raise RateLimitExceeded("Generation rate limit exceeded.")

    client.table("rate_limit_buckets").update(
        {"request_count": (int(row["request_count"]) + 1)}
    ).eq(
        "user_id",
        user_id,
    ).eq(
        "bucket",
        "image_generation",
    ).eq(
        "window_started_at",
        window_start.isoformat(),
    ).execute()
