"""SQL for generations and their idempotency records."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app import db

# ------------------------------------------------------------ idempotency


def get_idempotency(user_id: str, scope: str, idempotency_key: str) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT * FROM idempotency_records
        WHERE user_id = CAST(:user_id AS uuid) AND scope = :scope
          AND idempotency_key = :idempotency_key
        """,
        {"user_id": user_id, "scope": scope, "idempotency_key": idempotency_key},
    )


def create_idempotency(
    user_id: str, scope: str, idempotency_key: str, request_hash: str
) -> dict[str, Any] | None:
    """Raises ``db.IntegrityError`` when the (user, scope, key) triple exists."""
    return db.fetch_one(
        """
        INSERT INTO idempotency_records
            (user_id, scope, idempotency_key, request_hash, status)
        VALUES
            (CAST(:user_id AS uuid), :scope, :idempotency_key, :request_hash, 'processing')
        RETURNING *
        """,
        {
            "user_id": user_id,
            "scope": scope,
            "idempotency_key": idempotency_key,
            "request_hash": request_hash,
        },
    )


def link_idempotency(record_id: str, generation_id: UUID | str) -> None:
    db.execute(
        """
        UPDATE idempotency_records SET generation_id = CAST(:generation_id AS uuid)
        WHERE id = CAST(:record_id AS uuid)
        """,
        {"record_id": str(record_id), "generation_id": str(generation_id)},
    )


def finish_idempotency(
    record_id: str,
    status: str,
    response_status: int,
    completed_at: str | None = None,
) -> None:
    db.execute(
        """
        UPDATE idempotency_records
        SET status = :status,
            response_status = :response_status,
            completed_at = COALESCE(CAST(:completed_at AS timestamptz), completed_at)
        WHERE id = CAST(:record_id AS uuid)
        """,
        {
            "record_id": str(record_id),
            "status": status,
            "response_status": response_status,
            "completed_at": completed_at,
        },
    )


# ------------------------------------------------------------ generations


def get_generation(generation_id: UUID | str) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT * FROM generations WHERE id = CAST(:generation_id AS uuid)",
        {"generation_id": str(generation_id)},
    )


def get_brand_generation(brand_id: UUID | str, generation_id: UUID | str) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT * FROM generations
        WHERE id = CAST(:generation_id AS uuid) AND brand_id = CAST(:brand_id AS uuid)
        """,
        {"generation_id": str(generation_id), "brand_id": str(brand_id)},
    )


def insert_generation(values: dict[str, Any]) -> dict[str, Any] | None:
    """Insert a pending generation. ``values`` uses the column names."""
    return db.fetch_one(
        """
        INSERT INTO generations (
            id, user_id, brand_id, prompt, brief, language, provider, model,
            idempotency_key, platform_preset, width, height, logo_mode,
            product_asset_id, status, trend_id, trend_snapshot, trend_applied
        ) VALUES (
            CAST(:id AS uuid), CAST(:user_id AS uuid), CAST(:brand_id AS uuid),
            :prompt, CAST(:brief AS jsonb), :language, CAST(:provider AS provider_t),
            :model, :idempotency_key, CAST(:platform_preset AS platform_preset_t),
            :width, :height, CAST(:logo_mode AS logo_mode_t),
            CAST(:product_asset_id AS uuid), 'pending', CAST(:trend_id AS uuid),
            CAST(:trend_snapshot AS jsonb), :trend_applied
        )
        RETURNING *
        """,
        {
            **values,
            "brief": db.json_param(values.get("brief")),
            "trend_snapshot": db.json_param(values.get("trend_snapshot")),
        },
    )


def mark_processing(generation_id: UUID | str) -> None:
    db.execute(
        """
        UPDATE generations SET status = 'processing'
        WHERE id = CAST(:generation_id AS uuid)
        """,
        {"generation_id": str(generation_id)},
    )


def mark_succeeded(
    generation_id: UUID | str,
    image_path: str,
    provider_request_id: str | None,
    completed_at: str,
) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        UPDATE generations
        SET status = 'succeeded',
            image_path = :image_path,
            provider_request_id = :provider_request_id,
            completed_at = CAST(:completed_at AS timestamptz)
        WHERE id = CAST(:generation_id AS uuid)
        RETURNING *
        """,
        {
            "generation_id": str(generation_id),
            "image_path": image_path,
            "provider_request_id": provider_request_id,
            "completed_at": completed_at,
        },
    )


def mark_failed(generation_id: UUID | str, code: str, message: str, completed_at: str) -> None:
    db.execute(
        """
        UPDATE generations
        SET status = 'failed',
            error_code = :code,
            error_message = :message,
            completed_at = CAST(:completed_at AS timestamptz)
        WHERE id = CAST(:generation_id AS uuid)
        """,
        {
            "generation_id": str(generation_id),
            "code": code,
            "message": message,
            "completed_at": completed_at,
        },
    )


def list_history(
    brand_id: UUID | str,
    *,
    provider: str | None,
    status: str | None,
    cursor: tuple[str, str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Terminal generations, newest first, keyset-paginated on (created_at, id)."""
    conditions = [
        "brand_id = CAST(:brand_id AS uuid)",
        "status IN ('succeeded', 'failed')",
    ]
    params: dict[str, Any] = {"brand_id": str(brand_id), "limit": limit}

    if provider:
        conditions.append("provider = CAST(:provider AS provider_t)")
        params["provider"] = provider
    if status:
        conditions.append("status = CAST(:status AS generation_status_t)")
        params["status"] = status
    if cursor:
        cursor_created_at, cursor_id = cursor
        conditions.append(
            "(created_at < CAST(:cursor_created_at AS timestamptz) OR "
            "(created_at = CAST(:cursor_created_at AS timestamptz) "
            "AND id < CAST(:cursor_id AS uuid)))"
        )
        params["cursor_created_at"] = cursor_created_at
        params["cursor_id"] = cursor_id

    return db.fetch_all(
        f"""
        SELECT * FROM generations
        WHERE {" AND ".join(conditions)}
        ORDER BY created_at DESC, id DESC
        LIMIT :limit
        """,
        params,
    )


def count_succeeded(brand_id: UUID | str) -> int:
    row = db.fetch_one(
        """
        SELECT count(*) AS total FROM generations
        WHERE brand_id = CAST(:brand_id AS uuid) AND status = 'succeeded'
        """,
        {"brand_id": str(brand_id)},
    )
    return int(row["total"]) if row else 0


def delete_generation(brand_id: UUID | str, generation_id: UUID | str) -> None:
    db.execute(
        """
        DELETE FROM generations
        WHERE id = CAST(:generation_id AS uuid) AND brand_id = CAST(:brand_id AS uuid)
        """,
        {"generation_id": str(generation_id), "brand_id": str(brand_id)},
    )


def latest_for_brand(brand_id: UUID | str) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT id, image_path, status, created_at, prompt
        FROM generations
        WHERE brand_id = CAST(:brand_id AS uuid)
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"brand_id": str(brand_id)},
    )


__all__ = [
    "count_succeeded",
    "create_idempotency",
    "delete_generation",
    "finish_idempotency",
    "get_brand_generation",
    "get_generation",
    "get_idempotency",
    "insert_generation",
    "latest_for_brand",
    "link_idempotency",
    "list_history",
    "mark_failed",
    "mark_processing",
    "mark_succeeded",
]
