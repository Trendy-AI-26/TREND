"""Account logic: sign-up, email verification, login and password reset.

Everything here is synchronous (database + bcrypt); the router runs it in a
worker thread. Emails are not sent from here: functions that need one hand back
a :class:`PendingEmail` (or attach it to :class:`AuthError`) for the async
router layer to deliver.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app import db
from app.config import settings
from app.core import security
from app.core.auth import is_admin_email
from app.repositories import users as users_repo

logger = logging.getLogger(__name__)

FULL_NAME_MIN = 2
FULL_NAME_MAX = 120


@dataclass(frozen=True)
class PendingEmail:
    to: str
    code: str
    purpose: str


class AuthError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        pending_email: PendingEmail | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.pending_email = pending_email


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "full_name": row.get("full_name"),
        "is_admin": is_admin_email(row["email"]),
        "email_verified": row.get("email_verified_at") is not None,
    }


def _normalize_full_name(full_name: str | None) -> str | None:
    if full_name is None:
        return None
    cleaned = full_name.strip()
    if not cleaned:
        return None
    if not FULL_NAME_MIN <= len(cleaned) <= FULL_NAME_MAX:
        raise AuthError(
            400,
            "VALIDATION_ERROR",
            f"full_name must be {FULL_NAME_MIN}-{FULL_NAME_MAX} characters",
        )
    return cleaned


def _check_password(password: str) -> None:
    problem = security.validate_password(password)
    if problem:
        raise AuthError(400, "VALIDATION_ERROR", problem)


# ------------------------------------------------------------------ codes


def issue_code(user: dict[str, Any], purpose: str) -> PendingEmail | None:
    """Create a fresh code unless one was issued in the last 60 seconds.

    The cooldown is enforced silently (None), so callers answer identically
    whether or not a message goes out.
    """
    now = _now()
    user_id = str(user["id"])
    code = security.generate_code()
    result = users_repo.issue_code_if_allowed(
        user_id,
        purpose,
        security.hash_code(user_id, purpose, code),
        now + timedelta(seconds=security.CODE_TTL_SECONDS),
        now,
        security.CODE_RESEND_COOLDOWN_SECONDS,
    )
    if result != "issued":
        return None
    return PendingEmail(to=user["email"], code=code, purpose=purpose)


def check_code(
    user: dict[str, Any], purpose: str, code: str, *, consume: bool = True
) -> dict[str, Any]:
    """Validate and consume a code, or raise 400 INVALID_CODE / CODE_EXPIRED /
    TOO_MANY_ATTEMPTS. Wrong guesses are counted atomically (max 5)."""
    now = _now()
    user_id = str(user["id"])
    submitted = code.strip()

    row = users_repo.latest_code(user_id, purpose)
    if row is None or row["consumed_at"] is not None:
        raise AuthError(400, "INVALID_CODE", "The code is invalid.")
    if row["expires_at"] <= now:
        raise AuthError(400, "CODE_EXPIRED", "The code has expired. Request a new one.")
    if row["attempts"] >= security.CODE_MAX_ATTEMPTS:
        raise AuthError(
            400, "TOO_MANY_ATTEMPTS", "Too many attempts. Request a new code."
        )

    attempts = users_repo.increment_attempts(row["id"])
    if attempts is None:
        raise AuthError(400, "INVALID_CODE", "The code is invalid.")
    if attempts > security.CODE_MAX_ATTEMPTS:
        raise AuthError(
            400, "TOO_MANY_ATTEMPTS", "Too many attempts. Request a new code."
        )

    if not security.code_matches(user_id, purpose, submitted, row["code_hash"]):
        raise AuthError(400, "INVALID_CODE", "The code is invalid.")
    if consume and not users_repo.consume_code(row["id"], now):
        raise AuthError(400, "INVALID_CODE", "The code is invalid.")
    return row


# --------------------------------------------------------------- accounts


def signup(email: str, password: str, full_name: str | None) -> PendingEmail | None:
    email = normalize_email(email)
    _check_password(password)
    name = _normalize_full_name(full_name)

    existing = users_repo.get_user_by_email(email)
    if existing is not None and existing["email_verified_at"] is not None:
        raise AuthError(409, "EMAIL_ALREADY_REGISTERED", "This email is already registered.")

    if existing is None:
        password_hash = security.hash_password(password)
        try:
            user = users_repo.create_user(email, password_hash, name)
        except db.IntegrityError as exc:
            # Lost a race with a concurrent sign-up for the same address.
            if not db.is_unique_violation(exc, "uq_users_email_ci"):
                raise
            user = users_repo.get_user_by_email(email)
            if user is None:
                raise
            if user["email_verified_at"] is not None:
                raise AuthError(
                    409, "EMAIL_ALREADY_REGISTERED", "This email is already registered."
                )
    else:
        # A repeated sign-up proves no control over the mailbox. Keep the
        # original password and profile, and treat it only as a resend request.
        user = existing

    return issue_code(user, security.PURPOSE_VERIFY_EMAIL)


def signup_without_verification(
    email: str, password: str, full_name: str | None
) -> dict[str, Any]:
    """Sign-up for AUTH_REQUIRE_EMAIL_VERIFICATION=false.

    Creates the account (``email_verified_at`` stays NULL) and returns it so the
    router can start a session. No code is issued and no email is sent. An
    existing account, verified or not, is never touched or logged into.
    """
    email = normalize_email(email)
    _check_password(password)
    name = _normalize_full_name(full_name)

    if users_repo.get_user_by_email(email) is not None:
        raise AuthError(409, "EMAIL_ALREADY_REGISTERED", "This email is already registered.")

    try:
        return users_repo.create_user(email, security.hash_password(password), name)
    except db.IntegrityError as exc:
        # Lost a race with a concurrent sign-up for the same address.
        if not db.is_unique_violation(exc, "uq_users_email_ci"):
            raise
        raise AuthError(
            409, "EMAIL_ALREADY_REGISTERED", "This email is already registered."
        ) from None


def verify_email(email: str, code: str) -> dict[str, Any]:
    email = normalize_email(email)
    user = users_repo.get_user_by_email(email)
    if user is None:
        raise AuthError(400, "INVALID_CODE", "The code is invalid.")

    row = check_code(user, security.PURPOSE_VERIFY_EMAIL, code, consume=False)
    verified_at = _now()
    if not users_repo.consume_verification_code_and_mark_verified(
        user["id"], row["id"], verified_at
    ):
        raise AuthError(400, "INVALID_CODE", "The code is invalid.")
    if user["email_verified_at"] is None:
        user = {**user, "email_verified_at": verified_at}
    return user


def resend_code(email: str, purpose: str) -> PendingEmail | None:
    user = users_repo.get_user_by_email(normalize_email(email))
    if user is None:
        return None
    verified = user["email_verified_at"] is not None
    if purpose == security.PURPOSE_VERIFY_EMAIL and verified:
        return None
    if purpose == security.PURPOSE_RESET_PASSWORD and not verified:
        return None
    return issue_code(user, purpose)


def login(email: str, password: str) -> dict[str, Any]:
    user = users_repo.get_user_by_email(normalize_email(email))
    if user is None:
        security.dummy_password_check(password)
        raise AuthError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    if not security.verify_password(password, user["password_hash"]):
        raise AuthError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    # Checked only after the password, so it reveals nothing about unknown accounts.
    if user.get("disabled_at") is not None:
        raise AuthError(403, "ACCOUNT_DISABLED", "This account has been disabled.")
    if user["email_verified_at"] is None and settings.AUTH_REQUIRE_EMAIL_VERIFICATION:
        raise AuthError(
            403,
            "EMAIL_NOT_VERIFIED",
            "Verify your email before signing in.",
            pending_email=issue_code(user, security.PURPOSE_VERIFY_EMAIL),
        )
    return user


def forgot_password(email: str) -> PendingEmail | None:
    return resend_code(email, security.PURPOSE_RESET_PASSWORD)


def verify_reset_code(email: str, code: str) -> str:
    user = users_repo.get_user_by_email(normalize_email(email))
    if user is None or user["email_verified_at"] is None:
        raise AuthError(400, "INVALID_CODE", "The code is invalid.")
    check_code(user, security.PURPOSE_RESET_PASSWORD, code)
    return security.create_reset_token(str(user["id"]), user["email"], user["password_hash"])


def reset_password(reset_token: str, password: str) -> None:
    try:
        claims = security.decode_reset_token(reset_token)
    except security.TokenError:
        raise AuthError(400, "INVALID_RESET_TOKEN", "The reset link is invalid or has expired.")

    user = users_repo.get_user_by_id(claims["sub"])
    if (
        user is None
        or claims.get("pwf") != security.password_fingerprint(user["password_hash"])
    ):
        # Unknown user, or the password already changed since the token was issued.
        raise AuthError(400, "INVALID_RESET_TOKEN", "The reset link is invalid or has expired.")

    _check_password(password)
    users_repo.set_password(user["id"], security.hash_password(password), _now())


def get_user(user_id: str) -> dict[str, Any] | None:
    return users_repo.get_user_by_id(user_id)
