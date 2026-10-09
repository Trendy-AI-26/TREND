from app.services.trend_service import (
    is_trend_usable,
    rank_candidates,
)


def test_expired_trend_is_not_usable():
    trend = {
        "status": "active",
        "expires_at": "2020-01-01T00:00:00Z",
    }

    assert is_trend_usable(trend) is False


def test_inactive_trend_is_not_usable():
    trend = {
        "status": "inactive",
        "expires_at": None,
    }

    assert is_trend_usable(trend) is False


def test_active_without_expiration_is_usable():
    trend = {
        "status": "active",
        "expires_at": None,
    }

    assert is_trend_usable(trend) is True


def test_rank_candidates_returns_maximum_five():
    trends = [
        {
            "id": str(index),
            "status": "active",
            "expires_at": None,
            "industry": [],
            "region": [],
            "platform": ["instagram"],
            "audience": ["general_consumers"],
            "popularity_score": index,
            "growth_score": index,
            "relevance_score": index,
        }
        for index in range(10)
    ]

    class Audience:
        segments = ["general_consumers"]

    class Brief:
        target_audience = Audience()

    result = rank_candidates(
        trends,
        brief=Brief(),
        platform_preset="instagram_post",
    )

    assert len(result) == 5
    assert result[0]["id"] == "9"
