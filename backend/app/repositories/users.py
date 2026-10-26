"""SQL for users and one-time auth codes.

All rows are returned with native Python types (UUID, datetime) because the
auth service compares timestamps.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from app import db

_USER_COLUMNS = """
    u.id, u.email, u.password_hash, u.email_verified_at, u.created_at,
    u.disabled_at, p.full_name
"""


AccountStatus = Literal["active", "disabled", "missing"]


def account_status(user_id: str | UUID) -> AccountStatus:
    """``active``, ``disabled`` (by an admin) or ``missing`` (no such user).

    One primary-key lookup; used by every authenticated request. An id that is
    not a UUID cannot exist, so it is ``missing`` without a query.
    """
    try:
        canonical = str(UUID(str(user_id)))
    except ValueError:
        return "missing"
    row = db.fetch_one(
        "SELECT disabled_at IS NOT NULL AS disabled FROM users WHERE id = CAST(:user_id AS uuid)",
        {"user_id": canonical},
        raw=True,
    )
    if row is None:
        return "missing"
    return "disabled" if row["disabled"] else "active"


def get_user_by_email(email: str) -> dict[str, Any] | None:
    return db.fetch_one(
        f"""
        SELECT {_USER_COLUMNS}
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        WHERE lower(u.email) = lower(:email)
        """,
        {"email": email},
        raw=True,
    )


def get_user_by_id(user_id: str | UUID) -> dict[str, Any] | None:
    return db.fetch_one(
        f"""
        SELECT {_USER_COLUMNS}
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        WHERE u.id = CAST(:user_id AS uuid)
        """,
        {"user_id": str(user_id)},
        raw=True,
    )


def create_user(email: str, password_hash: str, full_name: str | None) -> dict[str, Any]:
    """Insert the user; the database trigger creates the profile row."""
    with db.transaction() as tx:
        created = tx.fetch_one(
            "INSERT INTO users (email, password_hash) VALUES (:email, :hash) RETURNING id",
            {"email": email, "hash": password_hash},
            raw=True,
        )
        assert created is not None
        if full_name is not None:
            tx.execute(
                "UPDATE profiles SET full_name = :full_name WHERE user_id = :user_id",
                {"full_name": full_name, "user_id": created["id"]},
            )
        row = tx.fetch_one(
            f"""
            SELECT {_USER_COLUMNS}
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id = :user_id
            """,
            {"user_id": created["id"]},
            raw=True,
        )
    assert row is not None
    return row


def set_password(user_id: str | UUID, password_hash: str, verified_at: datetime) -> None:
    """Set a new password; completing a reset also proves control of the mailbox."""
    db.execute(
        """
        UPDATE users
        SET password_hash = :hash,
            email_verified_at = COALESCE(email_verified_at, :verified_at)
        WHERE id = CAST(:user_id AS uuid)
        """,
        {"hash": password_hash, "verified_at": verified_at, "user_id": str(user_id)},
    )


# ------------------------------------------------------------------ codes


def latest_code(user_id: str | UUID, purpose: str) -> dict[str, Any] | None:
    """Most recently created code for the user and purpose (any state)."""
    return db.fetch_one(
        """
        SELECT id, user_id, purpose, code_hash, expires_at, attempts, consumed_at, created_at
        FROM auth_codes
        WHERE user_id = CAST(:user_id AS uuid) AND purpose = :purpose
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        {"user_id": str(user_id), "purpose": purpose},
        raw=True,
    )


def issue_code_if_allowed(
    user_id: str | UUID,
    purpose: str,
    code_hash: str,
    expires_at: datetime,
    now: datetime,
    cooldown_seconds: int,
) -> str:
    """Atomically issue a code after eligibility and cooldown checks.

    Locking the user row serializes sign-up, resend, and email verification for
    one account. The transaction is committed before the caller sends email.
    """
    with db.transaction() as tx:
        user = tx.fetch_one(
            """
            SELECT email_verified_at
            FROM users
            WHERE id = CAST(:user_id AS uuid)
            FOR UPDATE
            """,
            {"user_id": str(user_id)},
            raw=True,
        )
        if user is None:
            return "missing"

        is_verified = user["email_verified_at"] is not None
        if purpose == "verify_email" and is_verified:
            return "ineligible"
        if purpose == "reset_password" and not is_verified:
            return "ineligible"

        latest = tx.fetch_one(
            """
            SELECT created_at
            FROM auth_codes
            WHERE user_id = CAST(:user_id AS uuid) AND purpose = :purpose
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            {"user_id": str(user_id), "purpose": purpose},
            raw=True,
        )
        if latest is not None:
            age = (now - latest["created_at"]).total_seconds()
            if age < cooldown_seconds:
                return "cooldown"

        tx.execute(
            """
            UPDATE auth_codes
            SET consumed_at = :now
            WHERE user_id = CAST(:user_id AS uuid) AND purpose = :purpose
              AND consumed_at IS NULL
            """,
            {"user_id": str(user_id), "purpose": purpose, "now": now},
        )
        tx.execute(
            """
            INSERT INTO auth_codes (user_id, purpose, code_hash, expires_at, created_at)
            VALUES (CAST(:user_id AS uuid), :purpose, :code_hash, :expires_at, :now)
            """,
            {
                "user_id": str(user_id),
                "purpose": purpose,
                "code_hash": code_hash,
                "expires_at": expires_at,
                "now": now,
            },
        )
        return "issued"


def consume_verification_code_and_mark_verified(
    user_id: str | UUID,
    code_id: str | UUID,
    now: datetime,
) -> bool:
    """Consume a verification code and verify its user in one locked transaction."""
    with db.transaction() as tx:
        user = tx.fetch_one(
            """
            SELECT email_verified_at
            FROM users
            WHERE id = CAST(:user_id AS uuid)
            FOR UPDATE
            """,
            {"user_id": str(user_id)},
            raw=True,
        )
        if user is None or user["email_verified_at"] is not None:
            return False

        consumed = tx.execute(
            """
            UPDATE auth_codes
            SET consumed_at = :now
            WHERE id = CAST(:code_id AS uuid)
              AND user_id = CAST(:user_id AS uuid)
              AND purpose = 'verify_email'
              AND consumed_at IS NULL
            """,
            {"code_id": str(code_id), "user_id": str(user_id), "now": now},
        )
        if consumed != 1:
            return False

        tx.execute(
            """
            UPDATE users
            SET email_verified_at = :now
            WHERE id = CAST(:user_id AS uuid) AND email_verified_at IS NULL
            """,
            {"user_id": str(user_id), "now": now},
        )
        return True


def increment_attempts(code_id: str | UUID) -> int | None:
    """Atomically count one verification attempt; None when already consumed."""
    row = db.fetch_one(
        """
        UPDATE auth_codes SET attempts = attempts + 1
        WHERE id = CAST(:code_id AS uuid) AND consumed_at IS NULL
        RETURNING attempts
        """,
        {"code_id": str(code_id)},
        raw=True,
    )
    return None if row is None else int(row["attempts"])


def consume_code(code_id: str | UUID, now: datetime) -> bool:
    """Mark the code used; False when someone else consumed it first."""
    return (
        db.execute(
            """
            UPDATE auth_codes SET consumed_at = :now
            WHERE id = CAST(:code_id AS uuid) AND consumed_at IS NULL
            """,
            {"code_id": str(code_id), "now": now},
        )
        > 0
    )
