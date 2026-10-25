from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth import User, get_current_user
from app.models.trend import (
    TrendRecommendation,
    TrendRecommendationRequest,
    TrendRecommendationResponse,
)
from app.services.trend_ranker import rank_trends_with_openai
from app.services.trend_service import find_candidate_trends
from app.routers.brands import _get_brand_or_404
from app.routers.preview import _get_brand_kit_context


router = APIRouter(
    prefix="/brands/{brand_id}",
    tags=["trends"],
)


@router.post(
    "/trend-recommendations",
    response_model=TrendRecommendationResponse,
)
async def recommend_trends(
    brand_id: UUID,
    body: TrendRecommendationRequest,
    current_user: User = Depends(get_current_user),
) -> TrendRecommendationResponse:
    brand = _get_brand_or_404(
        brand_id,
        current_user.id,
    )

    brand_context = _get_brand_kit_context(
        brand_id,
        brand["name"],
    )

    candidates = find_candidate_trends(
        brief=body.brief,
        platform_preset=body.platform_preset,
    )

    if not candidates:
        return TrendRecommendationResponse(
            recommendations=[],
            best_trend_id=None,
        )

    ranked = await rank_trends_with_openai(
        brief=body.brief.model_dump(mode="json"),
        brand_context=brand_context,
        platform_preset=body.platform_preset,
        candidates=candidates,
    )

    candidate_by_id = {
        str(candidate["id"]): candidate
        for candidate in candidates
    }

    recommendations = []

    for item in ranked["recommendations"]:
        trend = candidate_by_id[item["trend_id"]]

        recommendations.append(
            TrendRecommendation(
                trend_id=item["trend_id"],
                trend_name=trend["name"],
                match_score=item["match_score"],
                reason=item["reason"],
                how_to_apply=item["how_to_apply"],
                risks=item["risks"],
            )
        )

    return TrendRecommendationResponse(
        recommendations=recommendations,
        best_trend_id=ranked.get("best_trend_id"),
    )
