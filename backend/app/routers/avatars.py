import io
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app.config import settings
from app.core.auth import User, get_current_user
from app.core.supabase import get_service_client
from app.models.avatars import AvatarUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["account"])


ALLOWED_FORMATS = {
    "PNG": ("png", "image/png"),
    "JPEG": ("jpg", "image/jpeg"),
    "WEBP": ("webp", "image/webp"),
}


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
                "request_id": str(uuid4()),
            }
        },
    )


def _create_signed_url(client, storage_path: str) -> str:
    result = (
        client.storage
        .from_(settings.AVATARS_BUCKET)
        .create_signed_url(storage_path, 3600)
    )

    if isinstance(result, dict):
        signed_url = (
            result.get("signedURL")
            or result.get("signed_url")
        )

        if signed_url:
            return signed_url

    raise _error_response(
        status.HTTP_502_BAD_GATEWAY,
        "AVATAR_URL_FAILED",
        "Could not create avatar URL",
    )


@router.post(
    "/me/avatar",
    response_model=AvatarUploadResponse,
)
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

    file_bytes = await file.read()

    if not file_bytes:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "EMPTY_FILE",
            "Avatar file is empty",
        )

    if len(file_bytes) > settings.AVATAR_MAX_BYTES:
        raise _error_response(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "FILE_TOO_LARGE",
            "Avatar must not exceed 2 MB",
        )

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except Exception as exc:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_IMAGE",
            "The uploaded file is not a valid image",
        ) from exc

    if image.format not in ALLOWED_FORMATS:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_IMAGE_TYPE",
            "Only PNG, JPEG, and WebP images are supported",
        )

    extension, content_type = ALLOWED_FORMATS[image.format]

    storage_path = (
        f"avatars/{current_user.id}/avatar.{extension}"
    )

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

    try:
        client.storage.from_(
            settings.AVATARS_BUCKET
        ).upload(
            storage_path,
            file_bytes,
            {
                "content-type": content_type,
                "upsert": "true",
            },
        )

        update_result = (
            client.table("profiles")
            .update(
                {
                    "avatar_path": storage_path,
                    "avatar_url": None,
                }
            )
            .eq("user_id", current_user.id)
            .execute()
        )

        if not update_result.data:
            raise RuntimeError(
                "Profile update returned no data"
            )

        # Delete old extension if the user changed format.
        if old_avatar_path and old_avatar_path != storage_path:
            try:
                client.storage.from_(
                    settings.AVATARS_BUCKET
                ).remove([old_avatar_path])
            except Exception:
                logger.warning(
                    "Failed to delete old avatar path=%s",
                    old_avatar_path,
                )

        return AvatarUploadResponse(
            user_id=current_user.id,
            avatar_url=_create_signed_url(
                client,
                storage_path,
            ),
            content_type=content_type,
            file_size_bytes=len(file_bytes),
            width=image.width,
            height=image.height,
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Avatar upload failed user_id=%s",
            current_user.id,
        )

        raise _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "AVATAR_UPLOAD_FAILED",
            "Could not upload avatar",
        ) from exc

@router.delete(
    "/me/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
):
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
        client.storage.from_(
            settings.AVATARS_BUCKET
        ).remove([avatar_path])
    except Exception:
        logger.warning(
            "Failed to delete avatar from Storage path=%s",
            avatar_path,
        )

    client.table("profiles").update(
        {
            "avatar_path": None,
            "avatar_url": None,
        }
    ).eq(
        "user_id",
        current_user.id,
    ).execute()
