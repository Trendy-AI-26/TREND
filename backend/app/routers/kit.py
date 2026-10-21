from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import User, get_current_user
from app.models.kit import KitAnswers, UpsertKitRequest, KitResponse, KitStatusEnum
from app.repositories import brands as brand_repo
from app.services.kit_summary import derive_status, derive_summary

router = APIRouter(prefix="/brands/{brand_id}/kit", tags=["brand-kit"])


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "request_id": str(uuid4())}},
    )


def _get_brand_or_404(brand_id: UUID, user_id: str) -> dict:
    brand = brand_repo.get_owned_brand(brand_id, user_id)
    if brand is None:
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")
    return brand


def _empty_answers() -> KitAnswers:
    return KitAnswers(product_asset_id=None, tagline=None, tone=None, industry=None, audience=None, colors=[], avoid_words=None)


def _row_to_response(brand: dict, row: dict | None) -> KitResponse:
    if row is None:
        return KitResponse(
            brand_id=brand["id"],
            brand_name=brand["name"],
            answers=_empty_answers(),
            summary=None,
            status=KitStatusEnum.not_started,
            completed_at=None,
            updated_at=None,
        )
    answers = KitAnswers(
        product_asset_id=row.get("product_asset_id"),
        tagline=row.get("tagline"),
        tone=row.get("tone"),
        industry=row.get("industry"),
        audience=row.get("audience"),
        colors=row.get("colors") or [],
        avoid_words=row.get("avoid_words"),
    )
    return KitResponse(
        brand_id=brand["id"],
        brand_name=brand["name"],
        answers=answers,
        summary=row.get("summary"),
        status=row.get("status", KitStatusEnum.not_started),
        completed_at=row.get("completed_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("", response_model=KitResponse)
def get_kit(brand_id: UUID, current_user: User = Depends(get_current_user)):
    brand = _get_brand_or_404(brand_id, current_user.id)
    row = brand_repo.get_kit(brand_id)
    return _row_to_response(brand, row)


@router.put("", response_model=KitResponse)
async def upsert_kit(
    brand_id: UUID,
    body: UpsertKitRequest,
    current_user: User = Depends(get_current_user),
):
    brand = _get_brand_or_404(brand_id, current_user.id)
    existing = brand_repo.get_kit_state(brand_id)

    a = body.answers
    if a.product_asset_id is not None:
        if not brand_repo.product_asset_exists(
            a.product_asset_id, brand_id, brand["owner_user_id"]
        ):
            raise _error_response(404, "PRODUCT_ASSET_NOT_FOUND", "Product image not found")

    new_status = derive_status(
        tagline=a.tagline,
        industry=a.industry,
        audience=a.audience,
        colors=a.colors,
        avoid_words=a.avoid_words,
    )
    summary = derive_summary(
        brand_name=brand["name"],
        tagline=a.tagline,
        industry=a.industry,
        audience=a.audience,
        colors=a.colors,
        avoid_words=a.avoid_words,
    )
    now = datetime.now(timezone.utc)
    if new_status == KitStatusEnum.complete:
        if (
            existing
            and existing.get("status") == KitStatusEnum.complete.value
            and existing.get("completed_at") is not None
        ):
            completed_at = existing["completed_at"]
        else:
            completed_at = now.isoformat()
    else:
        completed_at = None

    payload = {
        "brand_id": str(brand_id),
        "product_asset_id": str(a.product_asset_id) if a.product_asset_id else None,
        "tagline": a.tagline,
        "tone": a.tone.value if a.tone else None,
        "industry": a.industry,
        "audience": a.audience,
        "colors": a.colors,
        "avoid_words": a.avoid_words,
        "summary": summary,
        "status": new_status.value,
        "completed_at": completed_at,
    }
    row = brand_repo.upsert_kit(payload)
    return _row_to_response(brand, row)
