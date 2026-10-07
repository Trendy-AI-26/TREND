import io
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app.config import settings
from app.core.auth import User, get_current_user, is_admin_email
from app.core.supabase import get_service_client
from app.models.profile import (
    AvatarUploadResponse,
    ProfileResponse,
    UpdateProfileRequest,
)
from app.models.quota import QuotaSummaryResponse
from app.services.quota import QuotaError, get_quota_summary

logger = logging.getLogger(__name__)
router = APIRouter()

AVATAR_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}
AVATAR_SIGNED_URL_TTL = 3600


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {"code": code, "message": message, "request_id": str(uuid4())}
        },
    )


@router.get("/me/quota", response_model=QuotaSummaryResponse)
def get_my_quota(current_user: User = Depends(get_current_user)):
    try:
        summary = get_quota_summary(user_id=current_user.id)
    except QuotaError as exc:
        logger.exception("Failed to load generation quota")
        raise _error_response(503, exc.code, exc.message) from exc
    return QuotaSummaryResponse(**summary.__dict__)


def _create_avatar_signed_url(client, storage_path: str) -> str:
    result = client.storage.from_(settings.AVATARS_BUCKET).create_signed_url(
        storage_path, AVATAR_SIGNED_URL_TTL
    )

    if isinstance(result, dict):
        signed_url = result.get("signedURL") or result.get("signed_url")
        if signed_url:
            return signed_url

    raise _error_response(
        status.HTTP_502_BAD_GATEWAY,
        "AVATAR_URL_FAILED",
        "Could not create avatar URL",
    )


@router.get("/me", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    client = get_service_client()
    result = (
        client.table("profiles")
        .select("*")
        .eq("user_id", current_user.id)
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "PROFILE_NOT_FOUND",
            "Profile not found",
        )

    row = result.data
    avatar_path = row.get("avatar_path")
    avatar_url = _create_avatar_signed_url(client, avatar_path) if avatar_path else None

    return ProfileResponse(
        user_id=row["user_id"],
        email=current_user.email,
        full_name=row.get("full_name"),
        avatar_url=avatar_url,
        avatar_path=avatar_path,
        is_admin=is_admin_email(current_user.email),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
):
    update_data = body.model_dump(exclude_unset=True)

    if not update_data:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "VALIDATION_ERROR",
            "No fields provided for update",
        )

    client = get_service_client()
    result = (
        client.table("profiles")
        .update(update_data)
        .eq("user_id", current_user.id)
        .execute()
    )

    if not result.data:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "PROFILE_NOT_FOUND",
            "Profile not found",
        )

    row = result.data[0]
    avatar_path = row.get("avatar_path")
    avatar_url = (
        _create_avatar_signed_url(client, avatar_path)
        if avatar_path
        else row.get("avatar_url")
    )

    return ProfileResponse(
        user_id=row["user_id"],
        email=current_user.email,
        full_name=row.get("full_name"),
        avatar_url=avatar_url,
        avatar_path=avatar_path,
        is_admin=is_admin_email(current_user.email),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_FILE",
            "Avatar image is required",
        )

    if file.content_type not in {mime for _, mime in AVATAR_FORMATS.values()}:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_AVATAR_TYPE",
            "Avatar must be a JPEG, PNG, or WebP image",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "EMPTY_AVATAR",
            "Avatar file is empty",
        )

    if len(image_bytes) > settings.AVATAR_MAX_BYTES:
        raise _error_response(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "AVATAR_TOO_LARGE",
            "Avatar must be smaller than 2 MB",
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception as exc:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_IMAGE",
            "The uploaded file is not a valid image",
        ) from exc

    if image.format not in AVATAR_FORMATS:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_IMAGE_TYPE",
            "Only JPEG, PNG, and WebP images are supported",
        )

    extension, content_type = AVATAR_FORMATS[image.format]
    storage_path = f"avatars/{current_user.id}/avatar.{extension}"
    client = get_service_client()

    profile_result = (
        client.table("profiles")
        .select("avatar_path")
        .eq("user_id", current_user.id)
        .maybe_single()
        .execute()
    )
    if profile_result is None or profile_result.data is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "PROFILE_NOT_FOUND",
            "Profile not found",
        )

    old_avatar_path = profile_result.data.get("avatar_path")
    uploaded = False

    try:
        client.storage.from_(settings.AVATARS_BUCKET).upload(
            storage_path,
            image_bytes,
            {"content-type": content_type, "upsert": "true"},
        )
        uploaded = True
        signed_url = _create_avatar_signed_url(client, storage_path)

        update_result = (
            client.table("profiles")
            .update({"avatar_path": storage_path, "avatar_url": None})
            .eq("user_id", current_user.id)
            .execute()
        )
        if not update_result.data:
            raise _error_response(
                status.HTTP_404_NOT_FOUND,
                "PROFILE_NOT_FOUND",
                "Profile not found",
            )

        if old_avatar_path and old_avatar_path != storage_path:
            try:
                client.storage.from_(settings.AVATARS_BUCKET).remove([old_avatar_path])
            except Exception:
                logger.warning(
                    "Failed to remove old avatar path=%s",
                    old_avatar_path,
                    exc_info=True,
                )

        return AvatarUploadResponse(avatar_url=signed_url)

    except HTTPException:
        if uploaded:
            try:
                client.storage.from_(settings.AVATARS_BUCKET).remove([storage_path])
            except Exception:
                logger.warning(
                    "Failed to clean up avatar path=%s", storage_path, exc_info=True
                )
        raise
    except Exception as exc:
        if uploaded:
            try:
                client.storage.from_(settings.AVATARS_BUCKET).remove([storage_path])
            except Exception:
                logger.warning(
                    "Failed to clean up avatar path=%s", storage_path, exc_info=True
                )
        logger.exception("Avatar upload failed user_id=%s", current_user.id)
        raise _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "AVATAR_UPLOAD_FAILED",
            "Could not upload avatar",
        ) from exc


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avatar(current_user: User = Depends(get_current_user)):
    client = get_service_client()
    result = (
        client.table("profiles")
        .select("avatar_path")
        .eq("user_id", current_user.id)
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "PROFILE_NOT_FOUND",
            "Profile not found",
        )

    avatar_path = result.data.get("avatar_path")
    if not avatar_path:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "AVATAR_NOT_FOUND",
            "User has no avatar",
        )

    try:
        client.storage.from_(settings.AVATARS_BUCKET).remove([avatar_path])
    except Exception as exc:
        logger.exception("Failed to delete avatar path=%s", avatar_path)
        raise _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "AVATAR_DELETE_FAILED",
            "Could not delete avatar",
        ) from exc

    client.table("profiles").update({"avatar_path": None, "avatar_url": None}).eq(
        "user_id", current_user.id
    ).execute()
