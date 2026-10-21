"""SQL for brands and brand kits. Ownership is always part of the query."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app import db


def get_owned_brand(brand_id: UUID | str, user_id: str) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT * FROM brands
        WHERE id = CAST(:brand_id AS uuid) AND owner_user_id = CAST(:user_id AS uuid)
        """,
        {"brand_id": str(brand_id), "user_id": user_id},
    )


def get_kit_status(brand_id: UUID | str) -> str | None:
    row = db.fetch_one(
        "SELECT status FROM brand_kits WHERE brand_id = CAST(:brand_id AS uuid)",
        {"brand_id": str(brand_id)},
    )
    return None if row is None else str(row["status"])


def list_brands(user_id: str) -> list[dict[str, Any]]:
    return db.fetch_all(
        """
        SELECT * FROM brands
        WHERE owner_user_id = CAST(:user_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"user_id": user_id},
    )


def kit_summaries(brand_ids: list[str]) -> list[dict[str, Any]]:
    return db.fetch_all(
        """
        SELECT brand_id, status, colors, industry, tagline
        FROM brand_kits
        WHERE brand_id = ANY(CAST(:brand_ids AS uuid[]))
        """,
        {"brand_ids": brand_ids},
    )


def rename_brand(brand_id: UUID | str, name: str) -> dict[str, Any] | None:
    """Raises ``db.IntegrityError`` (uq_brands_owner_name_ci) on duplicates."""
    return db.fetch_one(
        """
        UPDATE brands SET name = :name
        WHERE id = CAST(:brand_id AS uuid)
        RETURNING *
        """,
        {"brand_id": str(brand_id), "name": name},
    )


def generation_image_paths(brand_id: UUID | str) -> list[str]:
    rows = db.fetch_all(
        """
        SELECT image_path FROM generations
        WHERE brand_id = CAST(:brand_id AS uuid) AND image_path IS NOT NULL
        """,
        {"brand_id": str(brand_id)},
    )
    return [row["image_path"] for row in rows]


def product_asset_paths(brand_id: UUID | str) -> list[str]:
    rows = db.fetch_all(
        "SELECT storage_path FROM product_assets WHERE brand_id = CAST(:brand_id AS uuid)",
        {"brand_id": str(brand_id)},
    )
    return [row["storage_path"] for row in rows]


def delete_brand(brand_id: UUID | str) -> None:
    """Related rows are removed by ON DELETE CASCADE."""
    db.execute(
        "DELETE FROM brands WHERE id = CAST(:brand_id AS uuid)",
        {"brand_id": str(brand_id)},
    )


def set_logo_path(brand_id: UUID | str, logo_path: str | None) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        UPDATE brands SET logo_path = :logo_path
        WHERE id = CAST(:brand_id AS uuid)
        RETURNING *
        """,
        {"brand_id": str(brand_id), "logo_path": logo_path},
    )


# ------------------------------------------------------------------ kits


def get_kit(brand_id: UUID | str) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT * FROM brand_kits WHERE brand_id = CAST(:brand_id AS uuid)",
        {"brand_id": str(brand_id)},
    )


def get_kit_state(brand_id: UUID | str) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT status, completed_at FROM brand_kits WHERE brand_id = CAST(:brand_id AS uuid)",
        {"brand_id": str(brand_id)},
    )


def product_asset_exists(asset_id: UUID | str, brand_id: UUID | str, owner_user_id: str) -> bool:
    row = db.fetch_one(
        """
        SELECT id FROM product_assets
        WHERE id = CAST(:asset_id AS uuid)
          AND brand_id = CAST(:brand_id AS uuid)
          AND owner_user_id = CAST(:owner AS uuid)
        """,
        {"asset_id": str(asset_id), "brand_id": str(brand_id), "owner": owner_user_id},
    )
    return row is not None


def upsert_kit(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Insert or update the kit for ``payload['brand_id']`` and return the row."""
    return db.fetch_one(
        """
        INSERT INTO brand_kits (
            brand_id, product_asset_id, tagline, tone, industry, audience,
            colors, avoid_words, summary, status, completed_at
        ) VALUES (
            CAST(:brand_id AS uuid), CAST(:product_asset_id AS uuid), :tagline,
            CAST(:tone AS tone_t), :industry, :audience,
            CAST(:colors AS text[]), :avoid_words, :summary,
            CAST(:status AS kit_status_t), CAST(:completed_at AS timestamptz)
        )
        ON CONFLICT (brand_id) DO UPDATE SET
            product_asset_id = EXCLUDED.product_asset_id,
            tagline = EXCLUDED.tagline,
            tone = EXCLUDED.tone,
            industry = EXCLUDED.industry,
            audience = EXCLUDED.audience,
            colors = EXCLUDED.colors,
            avoid_words = EXCLUDED.avoid_words,
            summary = EXCLUDED.summary,
            status = EXCLUDED.status,
            completed_at = EXCLUDED.completed_at
        RETURNING *
        """,
        {**payload, "colors": list(payload.get("colors") or [])},
    )
