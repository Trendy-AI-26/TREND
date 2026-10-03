from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status

from app.config import settings
from app.core.supabase import get_service_client
from app.services.providers.base import ReferenceImage


@dataclass(frozen=True)
class ProductAssetRecord:
    id: UUID
    brand_id: UUID
    owner_user_id: str
    storage_path: str
    content_type: str
    file_size_bytes: int
    width: int
    height: int


def _product_asset_error(
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
            }
        },
    )


def get_owned_product_asset(
    *,
    asset_id: UUID,
    brand_id: UUID,
    user_id: str,
) -> ProductAssetRecord:
    """
    قراءة صورة منتج مع التأكد من:
    - أنها موجودة.
    - تخص الـ Brand المطلوب.
    - تخص المستخدم الحالي.
    """
    client = get_service_client()

    result = (
        client.table("product_assets")
        .select(
            "id, brand_id, owner_user_id, storage_path, "
            "content_type, file_size_bytes, width, height"
        )
        .eq("id", str(asset_id))
        .eq("brand_id", str(brand_id))
        .eq("owner_user_id", user_id)
        .maybe_single()
        .execute()
    )

    if result is None or result.data is None:
        raise _product_asset_error(
            status.HTTP_404_NOT_FOUND,
            "PRODUCT_ASSET_NOT_FOUND",
            "Product image not found.",
        )

    row = result.data

    return ProductAssetRecord(
        id=UUID(str(row["id"])),
        brand_id=UUID(str(row["brand_id"])),
        owner_user_id=str(row["owner_user_id"]),
        storage_path=str(row["storage_path"]),
        content_type=str(row["content_type"]),
        file_size_bytes=int(row["file_size_bytes"]),
        width=int(row["width"]),
        height=int(row["height"]),
    )


def load_product_asset_reference(
    *,
    asset_id: UUID,
    brand_id: UUID,
    user_id: str,
) -> ReferenceImage:
    """
    قراءة سجل صورة المنتج ثم تنزيل محتوى الصورة
    من Supabase Storage.
    """
    asset = get_owned_product_asset(
        asset_id=asset_id,
        brand_id=brand_id,
        user_id=user_id,
    )

    if asset.file_size_bytes > settings.PRODUCT_ASSET_MAX_BYTES:
        raise _product_asset_error(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "PRODUCT_ASSET_TOO_LARGE",
            "Product image exceeds the allowed size.",
        )

    client = get_service_client()

    try:
        image_bytes = (
            client.storage
            .from_(settings.PRODUCT_ASSETS_BUCKET)
            .download(asset.storage_path)
        )
    except Exception as exc:
        raise _product_asset_error(
            status.HTTP_502_BAD_GATEWAY,
            "PRODUCT_ASSET_READ_FAILED",
            "Could not read the product image.",
        ) from exc

    if not image_bytes:
        raise _product_asset_error(
            status.HTTP_502_BAD_GATEWAY,
            "PRODUCT_ASSET_EMPTY",
            "The product image is empty.",
        )

    return ReferenceImage(
        content=image_bytes,
        mime_type=asset.content_type,
    )
