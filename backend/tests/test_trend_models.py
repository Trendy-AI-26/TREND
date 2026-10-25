from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.trend import (
    TrendRecommendation,
)


def test_match_score_accepts_valid_range():
    result = TrendRecommendation(
        trend_id=uuid4(),
        trend_name="Founder-led authenticity",
        match_score=91,
        reason="Good fit",
        how_to_apply=["Use natural lighting"],
        risks=[],
    )

    assert result.match_score == 91


def test_match_score_rejects_values_above_100():
    with pytest.raises(ValidationError):
        TrendRecommendation(
            trend_id=uuid4(),
            trend_name="Invalid",
            match_score=101,
            reason="Invalid",
            how_to_apply=[],
            risks=[],
        )
