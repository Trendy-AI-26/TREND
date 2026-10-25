"""Password hashing, session/reset JWTs and one-time email codes."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import get_jwt_secret, settings

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "trendy-api"
JWT_AUDIENCE = "trendy"

SESSION_COOKIE_NAME = "trendy_session"
RESET_TOKEN_TTL_SECONDS = 15 * 60

PASSWORD_MIN_LENGTH = 8
# bcrypt only looks at the first 72 bytes; refuse anything longer instead of
# silently truncating it.
PASSWORD_MAX_BYTES = 72

CODE_LENGTH = 6
CODE_TTL_SECONDS = 15 * 60
CODE_MAX_ATTEMPTS = 5
CODE_RESEND_COOLDOWN_SECONDS = 60

PURPOSE_VERIFY_EMAIL = "verify_email"
PURPOSE_RESET_PASSWORD = "reset_password"
CODE_PURPOSES = (PURPOSE_VERIFY_EMAIL, PURPOSE_RESET_PASSWORD)


class TokenError(Exception):
    """A JWT is missing, malformed, expired or has the wrong type."""


# ---------------------------------------------------------------- passwords


def validate_password(password: str) -> str | None:
    """Return an error message when the password is unacceptable, else None."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"Password must be at most {PASSWORD_MAX_BYTES} bytes"
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:PASSWORD_MAX_BYTES], password_hash.encode("ascii"))
    except ValueError:
        return False


_DUMMY_HASH: str | None = None


def dummy_password_check(password: str) -> None:
    """Spend the same time as a real check so unknown emails are not detectable."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("not-a-real-password")
    verify_password(password, _DUMMY_HASH)


def password_fingerprint(password_hash: str) -> str:
    """Short digest binding a reset token to the password it was issued for."""
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------- JWTs


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _encode(claims: dict[str, Any], ttl_seconds: int) -> str:
    now = _now()
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def _decode(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc


def create_session_token(user_id: str, email: str) -> str:
    return _encode({"sub": str(user_id), "email": email}, settings.AUTH_SESSION_TTL_SECONDS)


def decode_session_token(token: str) -> dict[str, Any]:
    payload = _decode(token)
    if payload.get("purpose"):
        # Reset (or any other special-purpose) tokens must never act as sessions.
        raise TokenError("Token is not a session token")
    return payload


def create_reset_token(user_id: str, email: str, password_hash: str) -> str:
    return _encode(
        {
            "sub": str(user_id),
            "email": email,
            "purpose": "reset",
            "pwf": password_fingerprint(password_hash),
        },
        RESET_TOKEN_TTL_SECONDS,
    )


def decode_reset_token(token: str) -> dict[str, Any]:
    payload = _decode(token)
    if payload.get("purpose") != "reset":
        raise TokenError("Token is not a reset token")
    return payload


# -------------------------------------------------------------------- codes


def generate_code() -> str:
    return f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"


def hash_code(user_id: str, purpose: str, code: str) -> str:
    """HMAC the code with the server secret; bound to user and purpose."""
    message = f"{user_id}:{purpose}:{code}".encode("utf-8")
    return hmac.new(get_jwt_secret().encode("utf-8"), message, hashlib.sha256).hexdigest()


def code_matches(user_id: str, purpose: str, code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_code(user_id, purpose, code), code_hash)
