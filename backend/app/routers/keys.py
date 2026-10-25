import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app import db
from app.core.auth import User, get_current_user
from app.core.vault import VaultError, decrypt_secret, encrypt_secret
from app.models.provider_key import (
    AddKeyRequest,
    ProviderKeyResponse,
    ValidateKeyResponse,
)
from app.repositories import brands as brand_repo
from app.repositories import provider_keys as key_repo
from app.services.provider_validation import validate_provider_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brands/{brand_id}/keys", tags=["provider-keys"])


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "request_id": str(uuid4())}},
    )


def _get_brand_or_404(brand_id: UUID, user_id: str) -> dict:
    brand = brand_repo.get_owned_brand(brand_id, user_id)
    if brand is None:
        raise _error_response(404, "BRAND_NOT_FOUND", "Brand not found")
    return brand


def _get_key_or_404(brand_id: UUID, key_id: UUID) -> dict:
    key = key_repo.get_key(brand_id, key_id)
    if key is None:
        raise _error_response(404, "KEY_NOT_FOUND", "Key not found")
    return key


def _key_response(row: dict) -> ProviderKeyResponse:
    return ProviderKeyResponse(
        id=row["id"],
        provider=row["provider"],
        label=row.get("label"),
        key_hint=row.get("key_hint"),
        is_active=row["is_active"],
        is_valid=row.get("is_valid"),
        last_validated_at=row.get("last_validated_at"),
        last_validation_error=row.get("last_validation_error"),
        created_at=row["created_at"],
    )


@router.get("", response_model=list[ProviderKeyResponse])
async def list_keys(
    brand_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _get_brand_or_404(brand_id, current_user.id)
    return [_key_response(row) for row in key_repo.list_keys(brand_id)]


@router.post("", response_model=ProviderKeyResponse, status_code=status.HTTP_201_CREATED)
async def add_key(
    brand_id: UUID,
    body: AddKeyRequest,
    current_user: User = Depends(get_current_user),
):
    _get_brand_or_404(brand_id, current_user.id)

    key_hint = body.key[-4:] if len(body.key) >= 4 else ("*" * len(body.key))

    try:
        encrypted_key = encrypt_secret(body.key)
    except VaultError as e:
        logger.error("Key encryption failed: %s", e)
        raise _error_response(502, "VAULT_ERROR", "Failed to store key securely") from e

    # Validate BEFORE touching active status so failures don't orphan the old key
    try:
        is_valid, validation_error = await validate_provider_key(body.provider, body.key)
    except Exception as e:
        logger.exception("Provider key validation crashed for provider=%s", body.provider)
        raise _error_response(
            502,
            "PROVIDER_VALIDATION_ERROR",
            "The provider could not validate this key. Check the key, model access, and provider availability.",
        ) from e
    now = datetime.now(timezone.utc).isoformat()

    try:
        # The previous active key is deactivated in the same transaction as the
        # insert, so a failure leaves it active (no manual rollback needed).
        row = key_repo.insert_key(
            {
                "brand_id": str(brand_id),
                "provider": body.provider,
                "encrypted_key": encrypted_key,
                "label": body.label,
                "key_hint": key_hint,
                "is_active": body.make_active,
                "is_valid": is_valid,
                "last_validated_at": now,
                "last_validation_error": None if is_valid is True else validation_error,
            },
            deactivate_existing=bool(body.make_active),
        )
    except Exception as e:
        if db.is_unique_violation(e, "uq_provider_keys_one_active"):
            raise _error_response(409, "ACTIVE_KEY_CONFLICT", "Another key is already active for this provider") from e
        logger.exception("Failed to persist provider key for brand=%s provider=%s", brand_id, body.provider)
        raise _error_response(
            502,
            "KEY_SAVE_ERROR",
            "The key was validated but could not be saved. Check the database migrations.",
        ) from e
    return _key_response(row)


@router.post("/{key_id}/validate", response_model=ValidateKeyResponse)
async def validate_key(
    brand_id: UUID,
    key_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _get_brand_or_404(brand_id, current_user.id)
    key = _get_key_or_404(brand_id, key_id)

    try:
        api_key = decrypt_secret(key["encrypted_key"])
    except VaultError as e:
        logger.error("Key decryption failed: %s", e)
        raise _error_response(502, "VAULT_ERROR", "Failed to retrieve key") from e

    if not api_key:
        raise _error_response(502, "VAULT_ERROR", "Key not found") from None

    is_valid, error_message = await validate_provider_key(key["provider"], api_key)

    now = datetime.now(timezone.utc)

    key_repo.update_validation(
        key_id,
        validated_at=now.isoformat(),
        error=None if is_valid is True else error_message,
        is_valid=is_valid,
    )

    return ValidateKeyResponse(
        valid=is_valid,
        validated_at=now,
        error=error_message,
        key_id=str(key_id),
    )


@router.patch("/{key_id}/activate", response_model=ProviderKeyResponse)
async def activate_key(
    brand_id: UUID,
    key_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _get_brand_or_404(brand_id, current_user.id)
    key = _get_key_or_404(brand_id, key_id)

    if key["is_active"]:
        return _key_response(key)

    try:
        row = key_repo.activate_key(brand_id, key_id, key["provider"])
    except Exception as e:
        if db.is_unique_violation(e, "uq_provider_keys_one_active"):
            raise _error_response(409, "ACTIVE_KEY_CONFLICT", "Another key is already active for this provider") from e
        raise
    return _key_response(row)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    brand_id: UUID,
    key_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _get_brand_or_404(brand_id, current_user.id)
    _get_key_or_404(brand_id, key_id)

    key_repo.delete_key(key_id)
