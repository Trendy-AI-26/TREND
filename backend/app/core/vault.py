"""Application-level secret encryption for provider API keys.

Provider API keys are never stored in plain text. Secrets are encrypted with Fernet
(``cryptography``) using the key in ``APP_ENCRYPTION_KEY`` and stored directly
in ``provider_keys.encrypted_key``.

Generate a key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class VaultError(RuntimeError):
    """Encryption is misconfigured or a stored secret cannot be decrypted."""


def _fernet() -> Fernet:
    key = settings.APP_ENCRYPTION_KEY
    if not key:
        raise VaultError("APP_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise VaultError(
            "APP_ENCRYPTION_KEY is not a valid Fernet key (32 url-safe base64 bytes)"
        ) from exc


def encrypt_secret(value: str) -> str:
    """Encrypt ``value``; the result is a url-safe text token."""
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt_secret`."""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise VaultError("Stored secret could not be decrypted") from exc
