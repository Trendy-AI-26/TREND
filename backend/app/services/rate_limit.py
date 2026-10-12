from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.core.supabase import get_service_client

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
        get_service_client().rpc(
            "check_generation_rate_limit",
            {
                "p_user_id": user_id,
                "p_bucket": "image_generation",
                "p_limit": limit,
                "p_window_started_at": window_start.isoformat(),
            },
        ).execute()
    except Exception as exc:
        if "RATE_LIMIT_EXCEEDED" in str(exc).upper():
            raise RateLimitExceeded("Generation rate limit exceeded.") from exc
        raise
