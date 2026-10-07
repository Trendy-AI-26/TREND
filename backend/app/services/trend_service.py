from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from app.core.supabase import get_service_client


def _error_response(
    status_code: int,
    code: str,
    message: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def is_trend_usable(trend: dict) -> bool:
    if trend.get("status") != "active":
        return False

    expires_at = _parse_datetime(trend.get("expires_at"))

    if expires_at is None:
        return True

    return expires_at >= datetime.now(timezone.utc)


def _list_values(trend: dict, field_name: str) -> list[str]:
    value = trend.get(field_name)

    if not isinstance(value, list):
        return []

    return [
        item
        for item in value
        if isinstance(item, str)
    ]


def _brief_values(brief, field_name: str) -> list[str]:
    value = getattr(brief, field_name, None)

    if value is None:
        return []

    if isinstance(value, list):
        return [
            item.value if hasattr(item, "value") else str(item)
            for item in value
        ]

    return [
        value.value if hasattr(value, "value") else str(value)
    ]


def _calculate_local_score(
    trend: dict,
    *,
    brief,
    platform_preset: str,
) -> int:
    score = 0

    trend_platforms = _list_values(trend, "platform")
    if platform_preset.split("_")[0] in trend_platforms:
        score += 20

    brief_segments = set(
        _brief_values(brief.target_audience, "segments")
    )
    trend_audiences = set(
        _list_values(trend, "audience")
    )

    if brief_segments & trend_audiences:
        score += 20

    score += int(trend.get("relevance_score") or 0)
    score += int(trend.get("growth_score") or 0)
    score += int(trend.get("popularity_score") or 0)

    return score


def rank_candidates(
    trends: list[dict],
    *,
    brief,
    platform_preset: str,
) -> list[dict]:
    usable = [
        trend
        for trend in trends
        if is_trend_usable(trend)
    ]

    return sorted(
        usable,
        key=lambda trend: _calculate_local_score(
            trend,
            brief=brief,
            platform_preset=platform_preset,
        ),
        reverse=True,
    )[:5]


def get_active_trend_or_404(
    trend_id: UUID,
) -> dict:
    client = get_service_client()

    result = (
        client.table("trends")
        .select("*")
        .eq("id", str(trend_id))
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        raise _error_response(
            404,
            "TREND_NOT_FOUND",
            "Selected trend was not found.",
        )

    trend = result.data

    if not is_trend_usable(trend):
        raise _error_response(
            409,
            "TREND_NOT_ACTIVE",
            "Selected trend is no longer active.",
        )

    return trend


def find_candidate_trends(
    *,
    brief,
    platform_preset: str,
) -> list[dict]:
    client = get_service_client()

    result = (
        client.table("trends")
        .select("*")
        .eq("status", "active")
        .limit(100)
        .execute()
    )

    trends = result.data or []

    return rank_candidates(
        trends,
        brief=brief,
        platform_preset=platform_preset,
    )
