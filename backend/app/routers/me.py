import logging
from pathlib import PurePosixPath
from unittest import result
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
 )

from app.config import settings
from app.core.auth import User, get_current_user, is_admin_email
from app.core.supabase import get_service_client
from app.models.profile import (
    AvatarUploadResponse,
    ProfileResponse,
    UpdateProfileRequest,
)


logger = logging.getLogger(__name__)

router = APIRouter()


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "request_id": str(uuid4())}},
    )

ALLOWED_AVATAR_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

@router.get("/me", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
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
    avatar_url = None

    if result.data.get("avatar_path"):
        avatar_url = _create_avatar_signed_url(
        client,
        result.data["avatar_path"],
    )

    return ProfileResponse(
        user_id=result.data["user_id"],
        email=current_user.email,
        full_name=result.data.get("full_name"),
        avatar_url=avatar_url,
        is_admin=is_admin_email(current_user.email),
        created_at=result.data["created_at"],
        updated_at=result.data["updated_at"],
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
    return ProfileResponse(
        user_id=row["user_id"],
        email=current_user.email,
        full_name=row.get("full_name"),
        avatar_url=row.get("avatar_url"),
        is_admin=is_admin_email(current_user.email),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _create_avatar_signed_url(client, avatar_path: str) -> str:
    result = (
        client.storage
        .from_(settings.AVATAR_BUCKET)
        .create_signed_url(avatar_path, 3600)
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
@router.post(
    "/me/avatar",
    response_model=AvatarUploadResponse,
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_AVATAR_TYPES:
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

    extension = ALLOWED_AVATAR_TYPES[file.content_type]

    avatar_path = (
        f"users/{current_user.id}/avatar/"
        f"{uuid4()}.{extension}"
    )

    client = get_service_client()

    profile_result = (
        client.table("profiles")
        .select("avatar_path")
        .eq("user_id", current_user.id)
        .maybe_single()
        .execute()
    )

    old_avatar_path = None

    if profile_result and profile_result.data:
        old_avatar_path = profile_result.data.get("avatar_path")

    try:
        client.storage.from_(settings.AVATAR_BUCKET).upload(
            avatar_path,
            image_bytes,
            {
                "content-type": file.content_type,
                "upsert": "false",
            },
        )

        update_result = (
            client.table("profiles")
            .update({"avatar_path": avatar_path})
            .eq("user_id", current_user.id)
            .execute()
        )

        if not update_result.data:
            client.storage.from_(settings.AVATAR_BUCKET).remove(
                [avatar_path]
            )

            raise _error_response(
                status.HTTP_404_NOT_FOUND,
                "PROFILE_NOT_FOUND",
                "Profile not found",
            )

        if old_avatar_path:
            try:
                client.storage.from_(settings.AVATAR_BUCKET).remove(
                    [old_avatar_path]
                )
            except Exception:
                logger.warning(
                    "Failed to remove old avatar user_id=%s",
                    current_user.id,
                )

        signed_url = _create_avatar_signed_url(
            client,
            avatar_path,
        )

        return AvatarUploadResponse(
            avatar_url=signed_url,
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Avatar upload failed user_id=%s",
            current_user.id,
        )

        try:
            client.storage.from_(settings.AVATAR_BUCKET).remove(
                [avatar_path]
            )
        except Exception:
            logger.warning(
                "Failed to clean up avatar after upload failure",
                exc_info=True,
            )

        raise _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "AVATAR_UPLOAD_FAILED",
            "Could not upload avatar",
        ) from exc


