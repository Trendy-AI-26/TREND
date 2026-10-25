import io
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app.config import settings
from app.core import storage
from app.core.auth import User, get_current_user
from app.models.product_asset import ProductAssetResponse, ProductAssetUploadResponse
from app.repositories import product_assets as asset_repo

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
    brand = asset_repo.get_owned_brand(brand_id, user_id)

    if brand is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "BRAND_NOT_FOUND",
            "Brand not found",
        )

    return brand


def _signed_url(storage_path: str) -> str:
    """Time-limited URL for the private product-assets bucket."""
    try:
        return storage.signed_url(settings.PRODUCT_ASSETS_BUCKET, storage_path, 3600)
    except storage.StorageError as exc:
        raise _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "PRODUCT_ASSET_URL_FAILED",
            "Could not create product image URL",
        ) from exc


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
            "Product image must not exceed 10 MB",
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

    try:
        storage.upload(
            settings.PRODUCT_ASSETS_BUCKET,
            storage_path,
            file_bytes,
            content_type,
            upsert=False,
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

        saved = asset_repo.insert_asset(row)

        if not saved:
            raise RuntimeError("Product asset insert returned no data")

        return ProductAssetUploadResponse(
            id=saved["id"],
            brand_id=saved["brand_id"],
            image_url=_signed_url(saved["storage_path"]),
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
            storage.remove(settings.PRODUCT_ASSETS_BUCKET, [storage_path])
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

@router.get(
    "/{asset_id}",
    response_model=ProductAssetResponse,
)
async def get_product_asset(
    brand_id: UUID,
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _get_owned_brand(brand_id, current_user.id)
    asset = asset_repo.get_owned_asset(asset_id, brand_id, current_user.id)
    if asset is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "PRODUCT_ASSET_NOT_FOUND",
            "Product image not found",
        )
    return ProductAssetResponse(
        id=asset["id"],
        brand_id=asset["brand_id"],
        image_url=_signed_url(asset["storage_path"]),
        content_type=asset["content_type"],
        file_size_bytes=asset["file_size_bytes"],
        width=asset["width"],
        height=asset["height"],
        created_at=asset["created_at"],
    )


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

    asset = asset_repo.get_owned_asset(asset_id, brand_id, current_user.id)

    if asset is None:
        raise _error_response(
            status.HTTP_404_NOT_FOUND,
            "PRODUCT_ASSET_NOT_FOUND",
            "Product image not found",
        )

    storage_path = asset["storage_path"]

    try:
        storage.remove(settings.PRODUCT_ASSETS_BUCKET, [storage_path])
    except storage.ObjectNotFoundError:
        pass  # already gone
    except Exception:
        logger.warning(
            "Failed to delete product asset from storage path=%s",
            storage_path,
        )

    asset_repo.delete_asset(asset_id, brand_id, current_user.id)
