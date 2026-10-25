"""SQL for product reference images. Ownership is part of every query."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app import db


def get_owned_brand(brand_id: UUID | str, user_id: str) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT id, owner_user_id, name FROM brands
        WHERE id = CAST(:brand_id AS uuid) AND owner_user_id = CAST(:user_id AS uuid)
        """,
        {"brand_id": str(brand_id), "user_id": user_id},
    )


def get_owned_asset(
    asset_id: UUID | str, brand_id: UUID | str, user_id: str
) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT id, brand_id, owner_user_id, storage_path, content_type,
               file_size_bytes, width, height, created_at
        FROM product_assets
        WHERE id = CAST(:asset_id AS uuid)
          AND brand_id = CAST(:brand_id AS uuid)
          AND owner_user_id = CAST(:user_id AS uuid)
        """,
        {"asset_id": str(asset_id), "brand_id": str(brand_id), "user_id": user_id},
    )


def insert_asset(values: dict[str, Any]) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        INSERT INTO product_assets (
            id, brand_id, owner_user_id, storage_path, content_type,
            file_size_bytes, width, height
        ) VALUES (
            CAST(:id AS uuid), CAST(:brand_id AS uuid), CAST(:owner_user_id AS uuid),
            :storage_path, :content_type, :file_size_bytes, :width, :height
        )
        RETURNING *
        """,
        values,
    )


def delete_asset(asset_id: UUID | str, brand_id: UUID | str, user_id: str) -> None:
    db.execute(
        """
        DELETE FROM product_assets
        WHERE id = CAST(:asset_id AS uuid)
          AND brand_id = CAST(:brand_id AS uuid)
          AND owner_user_id = CAST(:user_id AS uuid)
        """,
        {"asset_id": str(asset_id), "brand_id": str(brand_id), "user_id": user_id},
    )
