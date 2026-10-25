"""SQL over the admin monitoring views."""

from __future__ import annotations

from typing import Any

from app import db


def get_stats() -> dict[str, Any]:
    row = db.fetch_one("SELECT * FROM admin_stats")
    if row is None:
        raise RuntimeError("admin_stats returned no row")
    return row


def list_brands(offset: int, limit: int) -> tuple[list[dict[str, Any]], int]:
    """One page of ``admin_brand_overview`` (newest first) and the total count."""
    rows = db.fetch_all(
        """
        SELECT * FROM admin_brand_overview
        ORDER BY created_at DESC, id DESC
        OFFSET :offset LIMIT :limit
        """,
        {"offset": offset, "limit": limit},
    )
    total_row = db.fetch_one("SELECT count(*) AS total FROM admin_brand_overview")
    return rows, int(total_row["total"]) if total_row else 0
