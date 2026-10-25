import io
import logging
from urllib.parse import urlencode
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app import db
from app.config import settings
from app.core import storage
from app.core.auth import User, get_current_user
from app.models.brand import (
    BrandListItem,
    BrandResponse,
    CreateBrandRequest,
    DeleteBrandRequest,
    LogoUploadResponse,
    UpdateBrandRequest,
)
from app.models.generation import PreviewBriefRequest
from app.repositories import brands as brand_repo
from app.services.quota import QuotaError, create_brand_if_allowed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brands", tags=["brands"])


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {"code": code, "message": message, "request_id": str(uuid4())}
        },
    )


def _get_brand_or_404(brand_id: UUID, user_id: str) -> dict:
    brand = brand_repo.get_owned_brand(brand_id, user_id)
    if brand is None:
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")
    return brand


def _build_logo_url(logo_path: str | None, updated_at: str | None = None) -> str | None:
    if logo_path is None:
        return None
    logo_url = storage.public_url(settings.STORAGE_BUCKET, logo_path)
    if updated_at:
        return f"{logo_url}?{urlencode({'v': updated_at})}"
    return logo_url


def _get_kit_status(brand_id: str) -> str:
    return brand_repo.get_kit_status(brand_id) or "not_started"


def _brand_response(row: dict, kit_status: str) -> BrandResponse:
    return BrandResponse(
        id=row["id"],
        name=row["name"],
        logo_url=_build_logo_url(row.get("logo_path"), row.get("updated_at")),
        kit_status=kit_status,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _platform_preview_note(platform_preset: str) -> str:
    labels = {
        "instagram_post": "Bold, scroll-stopping product storytelling for the feed.",
        "instagram_story": "Quick visual moments designed for vertical story consumption.",
        "instagram_reel_cover": "Clear, high-impact cover art for short-form video content.",
        "facebook_post": "Broad, polished social content optimized for engagement.",
        "facebook_cover": "Strong profile cover art with a clean brand-first look.",
        "facebook_story": "Fast social storytelling with clear focal messaging.",
        "twitter_post": "Punchy, concise creative built for social conversation.",
        "twitter_header": "Wide-format brand hero designed for a professional profile header.",
        "linkedin_post": "Professional and informative visual designed for business audiences.",
        "linkedin_banner": "Premium branding layout for professional company positioning.",
        "tiktok_video_cover": "Animated marketing energy with a vibrant, attention-grabbing focal point.",
        "youtube_thumbnail": "High-contrast thumbnail art designed to spark curiosity instantly.",
        "youtube_banner": "Wide-format visual identity for a trusted channel presence.",
    }
    return labels.get(
        platform_preset, "Creative direction tuned for the selected platform format."
    )


@router.post("/{brand_id}/preview-brief")
async def preview_brand_brief(
    brand_id: UUID,
    body: PreviewBriefRequest,
    current_user: User = Depends(get_current_user),
):
    brand = _get_brand_or_404(brand_id, current_user.id)
    brief = body.brief
    audience = brief.target_audience
    target_audience = ", ".join(
        str(item.value if hasattr(item, "value") else item)
        for item in audience.segments
        if item
    )
    if not target_audience:
        target_audience = "General audience"

    creative_direction = {
        "campaign_goal": brief.campaign_goal.value,
        "content_type": brief.content_type.value,
        "target_audience": target_audience,
        "core_idea": brief.core_idea,
        "voice_tone": brief.voice_tone.value,
        "platform": {
            "name": body.platform_preset.value,
            "note": _platform_preview_note(body.platform_preset.value),
        },
        "text_to_include": brief.text_to_include,
        "optional_notes": brief.optional_notes,
        "brand_identity": {
            "tagline": None,
            "tone": brief.voice_tone.value,
            "colors": [],
            "avoid_words": None,
        },
    }

    return {
        "creative_direction": creative_direction,
        "brand_name": brand["name"],
        "language": brief.language.value,
    }


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    body: CreateBrandRequest, current_user: User = Depends(get_current_user)
):
    name = body.name.strip()
    try:
        row = create_brand_if_allowed(user_id=current_user.id, name=name)
    except QuotaError as exc:
        status_code = 403 if exc.code == "BRAND_LIMIT_REACHED" else 409
        raise _error_response(status_code, exc.code, exc.message) from exc
    kit_status = _get_kit_status(row["id"])
    return _brand_response(row, kit_status)


@router.get("", response_model=list[BrandListItem])
def list_brands(current_user: User = Depends(get_current_user)):
    rows = brand_repo.list_brands(current_user.id)
    brand_ids = [row["id"] for row in rows]
    kits: dict[str, dict] = {}
    if brand_ids:
        kits = {k["brand_id"]: k for k in brand_repo.kit_summaries(brand_ids)}

    items = []
    for row in rows:
        kit = kits.get(row["id"], {})
        kit_status = kit.get("status", "not_started")
        items.append(
            BrandListItem(
                id=row["id"],
                name=row["name"],
                logo_url=_build_logo_url(row.get("logo_path"), row.get("updated_at")),
                kit_status=kit_status,
                colors=kit.get("colors") or [],
                industry=kit.get("industry"),
                tagline=kit.get("tagline"),
                created_at=row["created_at"],
            )
        )
    return items


@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(brand_id: UUID, current_user: User = Depends(get_current_user)):
    brand = _get_brand_or_404(brand_id, current_user.id)
    kit_status = _get_kit_status(brand["id"])
    return _brand_response(brand, kit_status)


@router.patch("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    body: UpdateBrandRequest,
    current_user: User = Depends(get_current_user),
):
    brand = _get_brand_or_404(brand_id, current_user.id)
    name = body.name.strip()
    if name == brand["name"]:
        kit_status = _get_kit_status(brand["id"])
        return _brand_response(brand, kit_status)
    try:
        row = brand_repo.rename_brand(brand_id, name)
    except db.IntegrityError as e:
        if db.is_unique_violation(e):
            raise _error_response(
                409, "DUPLICATE_BRAND_NAME", "A brand with this name already exists"
            ) from e
        raise
    if row is None:
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")
    kit_status = _get_kit_status(row["id"])
    return _brand_response(row, kit_status)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: UUID,
    body: DeleteBrandRequest,
    current_user: User = Depends(get_current_user),
):
    brand = _get_brand_or_404(brand_id, current_user.id)
    if body.confirm_name != brand["name"]:
        raise _error_response(
            400, "NAME_MISMATCH", "Confirmation name does not match brand name"
        )
    # Step 1: Delete generation images from storage
    for image_path in brand_repo.generation_image_paths(brand_id):
        try:
            storage.remove(settings.STORAGE_BUCKET, [image_path])
        except storage.ObjectNotFoundError:
            pass  # already gone
        except Exception as e:
            logger.warning(f"Failed to delete generation image {image_path}: {e}")

    # Step 2: Delete brand logo from storage
    if brand.get("logo_path"):
        try:
            storage.remove(settings.STORAGE_BUCKET, [brand["logo_path"]])
        except storage.ObjectNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Failed to delete logo {brand['logo_path']}: {e}")

    # Step 3: Delete the brand row. The DB cascade removes related tables,
    # including provider_keys (their encrypted secrets live in the row itself).
    brand_repo.delete_brand(brand_id)


@router.post("/{brand_id}/logo", response_model=LogoUploadResponse)
async def upload_logo(
    brand_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    brand = _get_brand_or_404(brand_id, current_user.id)

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise _error_response(400, "VALIDATION_ERROR", "File size exceeds 5 MB limit")

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.thumbnail((512, 512))
    except Exception as e:
        logger.warning(f"Image processing failed: {e}")
        raise _error_response(
            400, "VALIDATION_ERROR", "Invalid or corrupted image file"
        ) from e

    # Validate actual image format (don't trust client content_type)
    allowed_formats = {
        "PNG": ("png", "image/png"),
        "JPEG": ("jpg", "image/jpeg"),
        "WEBP": ("webp", "image/webp"),
    }
    if img.format not in allowed_formats:
        raise _error_response(
            400, "INVALID_FILE_TYPE", "Only PNG, JPG, and WebP images are accepted"
        )
    ext, mime_type = allowed_formats[img.format]

    output = io.BytesIO()
    img.save(output, format=img.format)
    resized_bytes = output.getvalue()

    storage_path = f"brands/{brand_id}/logo.{ext}"

    old_logo_path = brand.get("logo_path")

    storage.upload(
        settings.STORAGE_BUCKET, storage_path, resized_bytes, mime_type, upsert=True
    )

    try:
        updated_row = brand_repo.set_logo_path(brand_id, storage_path)
    except Exception:
        if old_logo_path != storage_path:
            try:
                storage.remove(settings.STORAGE_BUCKET, [storage_path])
            except Exception as cleanup_err:
                logger.warning(
                    f"Failed to clean up uploaded logo after DB error: {cleanup_err}"
                )
        raise

    if old_logo_path and old_logo_path != storage_path:
        try:
            storage.remove(settings.STORAGE_BUCKET, [old_logo_path])
        except Exception as e:
            logger.warning(f"Failed to delete old logo {old_logo_path}: {e}")

    if not updated_row:
        try:
            storage.remove(settings.STORAGE_BUCKET, [storage_path])
        except Exception as cleanup_err:
            logger.warning(
                f"Failed to clean up uploaded logo after missing brand update: {cleanup_err}"
            )
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")

    return LogoUploadResponse(
        logo_url=_build_logo_url(storage_path, updated_row.get("updated_at"))
    )


@router.delete("/{brand_id}/logo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_logo(brand_id: UUID, current_user: User = Depends(get_current_user)):
    brand = _get_brand_or_404(brand_id, current_user.id)
    if not brand.get("logo_path"):
        raise _error_response(404, "LOGO_NOT_FOUND", "Brand has no logo to delete")

    try:
        storage.remove(settings.STORAGE_BUCKET, [brand["logo_path"]])
    except storage.ObjectNotFoundError:
        pass  # already gone
    except Exception as e:
        logger.warning(f"Failed to delete logo from storage: {e}")
    brand_repo.set_logo_path(brand_id, None)
