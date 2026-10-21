import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status


from app.config import settings
from app.core import storage
from app.core.auth import User, get_current_user
from app.models.generation import PreviewBriefRequest
from app.repositories import brands as brand_repo
from app.repositories import generations as gen_repo
from app.services.brief_preview import build_creative_direction

logger = logging.getLogger(__name__)

# Keep the existing public paths explicit because this module exposes
# both /brands/{brand_id}/preview-brief and /preview/* endpoints.
router = APIRouter(tags=["preview"])


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}},
    )


def _build_logo_url(logo_path: str | None) -> str | None:
    if not logo_path:
        return None

    return storage.public_url(settings.STORAGE_BUCKET, logo_path)


def _get_brand_or_404(brand_id: UUID, user_id: str) -> dict:
    brand = brand_repo.get_owned_brand(brand_id, user_id)

    if brand is None:
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")

    return brand


def _get_brand_kit_context(brand_id: UUID, brand_name: str) -> dict | None:
    row = brand_repo.get_kit(brand_id)

    if row is None:
        return None

    if row.get("status") != "complete":
        return None

    return {
        "name": brand_name,
        "tagline": row.get("tagline"),
        "tone": row.get("tone"),
        "audience": row.get("audience"),
        "colors": row.get("colors") or [],
        "avoid_words": row.get("avoid_words"),
    }


def _get_kit_status(brand_id: str) -> str:
    return brand_repo.get_kit_status(brand_id) or "not_started"


@router.post("/brands/{brand_id}/preview-brief")
async def preview_brief(
    brand_id: UUID,
    body: PreviewBriefRequest,
    current_user: User = Depends(get_current_user),
):
    """Return the creative direction for a structured generation brief."""
    brief = body.brief
    platform_preset = body.platform_preset.value

    brand = _get_brand_or_404(brand_id, current_user.id)
    brand_context = _get_brand_kit_context(brand_id, brand["name"])

    creative_direction = build_creative_direction(
        brief=brief,
        brand_name=brand["name"],
        platform_preset=platform_preset,
        brand_context=brand_context,
    )

    return {
        "creative_direction": creative_direction,
        "brand_name": brand["name"],
        "language": brief.language.value,
    }



@router.get("/preview/health")
async def preview_health():
    return {"status": "ok", "service": "preview"}


@router.get("/preview/brands/{brand_id}")
async def get_brand_preview(
    brand_id: UUID,
    current_user: User = Depends(get_current_user),
):
    brand = _get_brand_or_404(brand_id, current_user.id)

    generation = gen_repo.latest_for_brand(brand_id) or {}
    latest_image_url = None
    if generation.get("image_path"):
        latest_image_url = storage.public_url(
            settings.STORAGE_BUCKET, generation["image_path"]
        )

    return {
        "brand_id": str(brand["id"]),
        "name": brand["name"],
        "logo_url": _build_logo_url(brand.get("logo_path")),
        "kit_status": _get_kit_status(str(brand_id)),
        "latest_generation": {
            "id": generation.get("id"),
            "status": generation.get("status"),
            "image_url": latest_image_url,
            "created_at": generation.get("created_at"),
        },
    }


@router.get("/preview/brands/{brand_id}/latest-generation")
async def get_latest_generation_preview(
    brand_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _get_brand_or_404(brand_id, current_user.id)

    row = gen_repo.latest_for_brand(brand_id)

    if not row:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "GENERATION_NOT_FOUND",
            "No generation found for this brand",
        )

    image_url = None
    if row.get("image_path"):
        image_url = storage.public_url(settings.STORAGE_BUCKET, row["image_path"])

    return {
        "id": row["id"],
        "status": row.get("status"),
        "prompt": row.get("prompt"),
        "image_url": image_url,
        "created_at": row.get("created_at"),
    }
