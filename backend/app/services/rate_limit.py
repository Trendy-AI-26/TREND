from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app import db

class RateLimitExceeded(RuntimeError):
    pass

def check_generation_rate_limit(*, user_id: str, limit: int = 5, window_seconds: int = 60) -> None:
    if limit <= 0 or window_seconds <= 0:
        raise ValueError("Rate-limit limit and window must be positive.")
    now = datetime.now(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    elapsed_seconds = int((now - epoch).total_seconds())
    window_start = epoch + timedelta(seconds=elapsed_seconds - elapsed_seconds % window_seconds)
    try:
        db.fetch_one(
            "SELECT check_generation_rate_limit("
            "CAST(:p_user_id AS uuid), CAST(:p_bucket AS text), "
            "CAST(:p_limit AS integer), CAST(:p_window_started_at AS timestamptz)) AS result",
            {
                "p_user_id": user_id,
                "p_bucket": "image_generation",
                "p_limit": limit,
                "p_window_started_at": window_start,
            },
        )
    except Exception as exc:
        if "RATE_LIMIT_EXCEEDED" in str(exc).upper():
            raise RateLimitExceeded("Generation rate limit exceeded.") from exc
        raise
