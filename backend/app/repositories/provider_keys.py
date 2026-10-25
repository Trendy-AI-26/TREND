"""SQL for provider API keys (BYOK). Secrets stay encrypted in ``encrypted_key``."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app import db

# Never select encrypted_key unless a caller needs the secret.
_PUBLIC_COLUMNS = (
    "id, brand_id, provider, label, key_hint, is_active, is_valid, "
    "last_validated_at, last_validation_error, last_used_at, created_at, updated_at"
)


def list_keys(brand_id: UUID | str) -> list[dict[str, Any]]:
    return db.fetch_all(
        f"""
        SELECT {_PUBLIC_COLUMNS} FROM provider_keys
        WHERE brand_id = CAST(:brand_id AS uuid)
        ORDER BY provider, created_at DESC
        """,
        {"brand_id": str(brand_id)},
    )


def get_key(brand_id: UUID | str, key_id: UUID | str) -> dict[str, Any] | None:
    """The key row including ``encrypted_key``, scoped to its brand."""
    return db.fetch_one(
        """
        SELECT * FROM provider_keys
        WHERE id = CAST(:key_id AS uuid) AND brand_id = CAST(:brand_id AS uuid)
        """,
        {"key_id": str(key_id), "brand_id": str(brand_id)},
    )


def insert_key(values: dict[str, Any], *, deactivate_existing: bool) -> dict[str, Any] | None:
    """Insert a key; optionally deactivate the provider's active key first.

    Both steps run in one transaction, so a failed insert (for example
    ``uq_provider_keys_one_active``) leaves the previous active key untouched.
    """
    with db.transaction() as tx:
        if deactivate_existing:
            tx.execute(
                """
                UPDATE provider_keys SET is_active = FALSE
                WHERE brand_id = CAST(:brand_id AS uuid)
                  AND provider = CAST(:provider AS provider_t) AND is_active
                """,
                {"brand_id": values["brand_id"], "provider": values["provider"]},
            )
        return tx.fetch_one(
            f"""
            INSERT INTO provider_keys (
                brand_id, provider, encrypted_key, label, key_hint, is_active,
                is_valid, last_validated_at, last_validation_error
            ) VALUES (
                CAST(:brand_id AS uuid), CAST(:provider AS provider_t), :encrypted_key,
                :label, :key_hint, :is_active, :is_valid,
                CAST(:last_validated_at AS timestamptz), :last_validation_error
            )
            RETURNING {_PUBLIC_COLUMNS}
            """,
            values,
        )


def update_validation(
    key_id: UUID | str,
    *,
    validated_at: str,
    error: str | None,
    is_valid: bool | None,
) -> None:
    """Record a validation result; ``is_valid=None`` keeps the previous verdict."""
    db.execute(
        """
        UPDATE provider_keys
        SET last_validated_at = CAST(:validated_at AS timestamptz),
            last_validation_error = :error,
            is_valid = COALESCE(:is_valid, is_valid)
        WHERE id = CAST(:key_id AS uuid)
        """,
        {
            "key_id": str(key_id),
            "validated_at": validated_at,
            "error": error,
            "is_valid": is_valid,
        },
    )


def activate_key(brand_id: UUID | str, key_id: UUID | str, provider: str) -> dict[str, Any] | None:
    """Make ``key_id`` the provider's only active key (atomic swap)."""
    with db.transaction() as tx:
        tx.execute(
            """
            UPDATE provider_keys SET is_active = FALSE
            WHERE brand_id = CAST(:brand_id AS uuid)
              AND provider = CAST(:provider AS provider_t) AND is_active
            """,
            {"brand_id": str(brand_id), "provider": provider},
        )
        return tx.fetch_one(
            f"""
            UPDATE provider_keys SET is_active = TRUE
            WHERE id = CAST(:key_id AS uuid)
            RETURNING {_PUBLIC_COLUMNS}
            """,
            {"key_id": str(key_id)},
        )


def delete_key(key_id: UUID | str) -> None:
    db.execute(
        "DELETE FROM provider_keys WHERE id = CAST(:key_id AS uuid)",
        {"key_id": str(key_id)},
    )
