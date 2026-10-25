"""SQL for user profiles (one row per user, keyed by user_id)."""

from __future__ import annotations

from typing import Any

from app import db

# Columns a client may change through PATCH /me.
UPDATABLE_COLUMNS = ("full_name", "avatar_url")


def get_profile(user_id: str) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT * FROM profiles WHERE user_id = CAST(:user_id AS uuid)",
        {"user_id": user_id},
    )


def get_avatar_path(user_id: str) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT avatar_path FROM profiles WHERE user_id = CAST(:user_id AS uuid)",
        {"user_id": user_id},
    )


def update_profile(user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    """Update the given columns (whitelisted) and return the new row."""
    columns = [name for name in fields if name in UPDATABLE_COLUMNS]
    if not columns:
        return get_profile(user_id)
    assignments = ", ".join(f"{name} = :{name}" for name in columns)
    params: dict[str, Any] = {name: fields[name] for name in columns}
    params["user_id"] = user_id
    return db.fetch_one(
        f"""
        UPDATE profiles SET {assignments}
        WHERE user_id = CAST(:user_id AS uuid)
        RETURNING *
        """,
        params,
    )


def set_avatar_path(user_id: str, avatar_path: str | None) -> dict[str, Any] | None:
    """Set (or clear) the private avatar path; the legacy avatar_url is cleared."""
    return db.fetch_one(
        """
        UPDATE profiles SET avatar_path = :avatar_path, avatar_url = NULL
        WHERE user_id = CAST(:user_id AS uuid)
        RETURNING *
        """,
        {"user_id": user_id, "avatar_path": avatar_path},
    )
