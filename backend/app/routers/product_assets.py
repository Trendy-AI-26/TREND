import io
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app.config import settings
from app.core.auth import User, get_current_user
from app.core.supabase import get_service_client
from app.models.product_asset import ProductAssetUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/brands/{brand_id}/product-assets",
    tags=["product-assets"],
)


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


def _get_owned_brand(brand_id: UUID, user_id: str) -> dict:
    client = get_service_client()

    result = (
        client.table("brands")
        .select("id, owner_user_id, name")
        .eq("id", str(brand_id))
        .eq("owner_user_id", user_id)
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "BRAND_NOT_FOUND",
            "Brand not found",
        )

    return result.data


def _signed_url(client, storage_path: str) -> str:
    result = (
        client.storage
        .from_(settings.PRODUCT_ASSETS_BUCKET)
        .create_signed_url(storage_path, 3600)
    )

    if isinstance(result, dict):
        url = result.get("signedURL") or result.get("signed_url")

        if url:
            return url

    raise _error_response(
        status.HTTP_502_BAD_GATEWAY,
        "PRODUCT_ASSET_URL_FAILED",
        "Could not create product image URL",
    )


@router.post(
    "",
    response_model=ProductAssetUploadResponse,
)
async def upload_product_asset(
    brand_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    _get_owned_brand(brand_id, current_user.id)

    if not file.filename:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_FILE",
            "A product image file is required",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "EMPTY_FILE",
            "The product image file is empty",
        )

    if len(file_bytes) > settings.PRODUCT_ASSET_MAX_BYTES:
        raise _error_response(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "FILE_TOO_LARGE",
            "Product image must not exceed 5 MB",
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

    image_format = image.format

    if image_format not in ALLOWED_FORMATS:
        raise _error_response(
            status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_IMAGE_TYPE",
            "Only PNG, JPEG, and WebP images are supported",
        )

    extension, content_type = ALLOWED_FORMATS[image_format]

    asset_id = uuid4()

    storage_path = (
        f"brands/{brand_id}/product-assets/"
        f"{asset_id}.{extension}"
    )

    client = get_service_client()

    try:
        client.storage.from_(
            settings.PRODUCT_ASSETS_BUCKET
        ).upload(
            storage_path,
            file_bytes,
            {
                "content-type": content_type,
                "upsert": "false",
            },
        )

        row = {
            "id": str(asset_id),
            "brand_id": str(brand_id),
            "owner_user_id": current_user.id,
            "storage_path": storage_path,
            "content_type": content_type,
            "file_size_bytes": len(file_bytes),
            "width": image.width,
            "height": image.height,
        }

        result = (
            client.table("product_assets")
            .insert(row)
            .execute()
        )

        if not result.data:
            raise RuntimeError("Product asset insert returned no data")

        saved = result.data[0]

        return ProductAssetUploadResponse(
            id=saved["id"],
            brand_id=saved["brand_id"],
            image_url=_signed_url(
                client,
                saved["storage_path"],
            ),
            content_type=saved["content_type"],
            file_size_bytes=saved["file_size_bytes"],
            width=saved["width"],
            height=saved["height"],
            created_at=saved["created_at"],
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Product asset upload failed brand_id=%s user_id=%s",
            brand_id,
            current_user.id,
        )

        try:
            client.storage.from_(
                settings.PRODUCT_ASSETS_BUCKET
            ).remove([storage_path])
        except Exception:
            logger.warning(
                "Product asset cleanup failed path=%s",
                storage_path,
            )

        raise _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "PRODUCT_ASSET_UPLOAD_FAILED",
            "Could not upload product image",
        ) from exc

@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product_asset(
    brand_id: UUID,
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _get_owned_brand(brand_id, current_user.id)

    client = get_service_client()

    result = (
        client.table("product_assets")
        .select("id, storage_path")
        .eq("id", str(asset_id))
        .eq("brand_id", str(brand_id))
        .eq("owner_user_id", current_user.id)
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "PRODUCT_ASSET_NOT_FOUND",
            "Product image not found",
        )

    storage_path = result.data["storage_path"]

    try:
        client.storage.from_(
            settings.PRODUCT_ASSETS_BUCKET
        ).remove([storage_path])
    except Exception:
        logger.warning(
            "Failed to delete product asset from storage path=%s",
            storage_path,
        )

    client.table("product_assets").delete().eq(
        "id",
        str(asset_id),
    ).eq(
        "brand_id",
        str(brand_id),
    ).eq(
        "owner_user_id",
        current_user.id,
    ).execute()
