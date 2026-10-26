"""SQL for the admin area: monitoring views, lists, user actions, trends, audit log.

Rows are returned as JSON-friendly dicts (UUID -> str, datetime -> ISO str,
Decimal -> float); the router maps them onto the response models. Every admin
action writes its ``admin_audit_log`` row in the same transaction as the
change itself, so an action is never applied without being audited.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

from app import db

NEEDS_REVIEW_AFTER = "10 minutes"
REVIEW_PHASES = ("outcome_unknown", "cleanup_pending")

# A generation needs review when its idempotency record is still open on an
# "outcome unknown" / "cleanup pending" checkpoint, or when it has been pending
# or processing for more than 10 minutes. Closed records keep their last
# checkpoint in response_body, so only still-processing records count.
NEEDS_REVIEW_SQL = f"""(
    EXISTS (
        SELECT 1 FROM idempotency_records ir
        WHERE ir.generation_id = g.id
          AND ir.status = 'processing'
          AND ir.response_body ->> 'phase' IN ('outcome_unknown', 'cleanup_pending')
    )
    OR (
        g.status IN ('pending', 'processing')
        AND g.created_at < now() - interval '{NEEDS_REVIEW_AFTER}'
    )
)"""

# The owner is the brand owner; generations.user_id is the same user (and
# NULL only for legacy rows).
_GENERATION_SELECT = f"""
    SELECT
        g.id, g.status::text AS status, g.provider::text AS provider, g.model,
        g.platform_preset::text AS platform_preset, g.error_code, g.error_message,
        g.created_at, g.completed_at, g.image_path,
        {NEEDS_REVIEW_SQL} AS needs_review,
        b.id AS brand_id, b.name AS brand_name,
        u.id AS user_id, u.email AS user_email
    FROM generations g
    JOIN brands b ON b.id = g.brand_id
    JOIN users u ON u.id = COALESCE(g.user_id, b.owner_user_id)
"""

_TODAY_SQL = "(now() AT TIME ZONE 'utc')::date"

_USER_SELECT = f"""
    SELECT
        u.id, u.email, p.full_name, u.email_verified_at, u.disabled_at, u.created_at,
        p.trial_ends_at,
        (SELECT count(*) FROM brands ob WHERE ob.owner_user_id = u.id) AS brands_count,
        gc.total AS generations_count,
        gc.succeeded AS generations_succeeded,
        q.generation_limit AS quota_limit, q.consumed AS quota_consumed,
        q.reserved AS quota_reserved,
        ca.balance AS credits_balance, ca.reserved AS credits_reserved,
        d.daily_limit AS today_limit, d.consumed AS today_consumed,
        d.reserved AS today_reserved
    FROM users u
    LEFT JOIN profiles p ON p.user_id = u.id
    LEFT JOIN user_generation_quotas q ON q.user_id = u.id
    LEFT JOIN credit_accounts ca ON ca.user_id = u.id
    LEFT JOIN generation_daily_usage d
        ON d.user_id = u.id AND d.usage_date = {_TODAY_SQL}
    LEFT JOIN LATERAL (
        SELECT
            count(*) AS total,
            count(*) FILTER (WHERE g.status = 'succeeded') AS succeeded
        FROM generations g
        JOIN brands gb ON gb.id = g.brand_id
        WHERE gb.owner_user_id = u.id
    ) gc ON true
"""

_BRAND_FROM = """
    FROM brands b
    JOIN users u ON u.id = b.owner_user_id
    LEFT JOIN profiles p ON p.user_id = b.owner_user_id
    LEFT JOIN brand_kits bk ON bk.brand_id = b.id
"""

_TREND_COLUMNS = """
    id, name, slug, description, category, industry, region, platform, audience,
    visual_style, content_patterns, keywords, avoid_patterns, popularity_score,
    growth_score, relevance_score, status, source, observed_at, expires_at,
    created_at, updated_at
"""

TREND_JSON_FIELDS = (
    "industry",
    "region",
    "platform",
    "audience",
    "visual_style",
    "content_patterns",
    "keywords",
    "avoid_patterns",
)
TREND_SCALAR_FIELDS = (
    "name",
    "slug",
    "description",
    "category",
    "popularity_score",
    "growth_score",
    "relevance_score",
    "status",
    "source",
    "observed_at",
    "expires_at",
)
_TREND_CASTS = {"observed_at": "timestamptz", "expires_at": "timestamptz"}


def like_pattern(term: str) -> str:
    """``%term%`` for ILIKE with LIKE wildcards in ``term`` escaped."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _where(conditions: Iterable[str]) -> str:
    conditions = list(conditions)
    return ("WHERE " + " AND ".join(conditions)) if conditions else ""


def _count(tx: db.Tx, sql: str, params: dict[str, Any]) -> int:
    """``SELECT count(*) AS total ...`` with the list's filters but not its paging."""
    filters = {k: v for k, v in params.items() if k not in ("offset", "limit")}
    row = tx.fetch_one(sql, filters)
    return int(row["total"]) if row else 0


def _insert_audit(tx: db.Tx, audit: dict[str, Any]) -> None:
    """Write one audit row. A missing admin row stores NULL instead of failing."""
    tx.execute(
        """
        INSERT INTO admin_audit_log
            (admin_user_id, admin_email, action, target_type, target_id, details)
        VALUES (
            (SELECT id FROM users WHERE id = CAST(:admin_user_id AS uuid)),
            :admin_email, :action, :target_type, :target_id, CAST(:details AS jsonb)
        )
        """,
        {
            "admin_user_id": audit["admin_user_id"],
            "admin_email": audit["admin_email"],
            "action": audit["action"],
            "target_type": audit["target_type"],
            "target_id": None if audit.get("target_id") is None else str(audit["target_id"]),
            "details": db.json_param(audit.get("details") or {}),
        },
    )


# ------------------------------------------------------------ monitoring views


def get_stats() -> dict[str, Any]:
    row = db.fetch_one("SELECT * FROM admin_stats")
    if row is None:
        raise RuntimeError("admin_stats returned no row")
    return row


# ------------------------------------------------------------ overview


def get_overview_counts() -> dict[str, Any]:
    row = db.fetch_one(
        f"""
        SELECT
            (SELECT count(*) FROM users) AS users_total,
            (SELECT count(*) FROM users WHERE email_verified_at IS NOT NULL) AS users_verified,
            (SELECT count(*) FROM users WHERE created_at >= now() - interval '7 days') AS users_new_7d,
            (SELECT count(*) FROM users WHERE disabled_at IS NOT NULL) AS users_disabled,
            (SELECT count(*) FROM brands) AS brands_total,
            (SELECT count(*) FROM brand_kits WHERE status = 'complete') AS brands_kits_complete,
            gs.total AS generations_total,
            gs.today AS generations_today,
            gs.last_7d AS generations_last_7d,
            gs.last_30d AS generations_last_30d,
            gs.succeeded AS generations_succeeded,
            gs.failed AS generations_failed,
            gs.pending AS generations_pending,
            gs.processing AS generations_processing,
            gs.succeeded_30d AS generations_succeeded_30d,
            gs.failed_30d AS generations_failed_30d,
            cost.credits_charged_30d,
            cost.estimated_provider_cost_30d
        FROM (
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE created_at >= {_TODAY_SQL}::timestamp AT TIME ZONE 'utc') AS today,
                count(*) FILTER (WHERE created_at >= now() - interval '7 days') AS last_7d,
                count(*) FILTER (WHERE created_at >= now() - interval '30 days') AS last_30d,
                count(*) FILTER (WHERE status = 'succeeded') AS succeeded,
                count(*) FILTER (WHERE status = 'failed') AS failed,
                count(*) FILTER (WHERE status = 'pending') AS pending,
                count(*) FILTER (WHERE status = 'processing') AS processing,
                count(*) FILTER (
                    WHERE status = 'succeeded' AND created_at >= now() - interval '30 days'
                ) AS succeeded_30d,
                count(*) FILTER (
                    WHERE status = 'failed' AND created_at >= now() - interval '30 days'
                ) AS failed_30d
            FROM generations
        ) gs
        CROSS JOIN (
            SELECT
                COALESCE(sum(credits_charged), 0) AS credits_charged_30d,
                sum(estimated_provider_cost) AS estimated_provider_cost_30d
            FROM generation_usage
            WHERE created_at >= now() - interval '30 days'
        ) cost
        """
    )
    if row is None:
        raise RuntimeError("overview query returned no row")
    return row


def get_daily_outcomes(days: int = 30) -> list[dict[str, Any]]:
    """One row per UTC day (oldest first, today included), zero-filled."""
    return db.fetch_all(
        f"""
        SELECT
            day.d::date AS date,
            count(g.id) FILTER (WHERE g.status = 'succeeded') AS succeeded,
            count(g.id) FILTER (WHERE g.status = 'failed') AS failed
        FROM generate_series(
            ({_TODAY_SQL} - (CAST(:days AS integer) - 1))::timestamp,
            {_TODAY_SQL}::timestamp,
            interval '1 day'
        ) AS day(d)
        LEFT JOIN generations g
            ON g.created_at >= day.d AT TIME ZONE 'utc'
           AND g.created_at < (day.d + interval '1 day') AT TIME ZONE 'utc'
           AND g.status IN ('succeeded', 'failed')
        GROUP BY day.d
        ORDER BY day.d
        """,
        {"days": days},
    )


def list_needs_review(limit: int = 20) -> list[dict[str, Any]]:
    return db.fetch_all(
        f"""
        {_GENERATION_SELECT}
        WHERE {NEEDS_REVIEW_SQL}
        ORDER BY g.created_at DESC, g.id DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


def list_recent_failures(limit: int = 10) -> list[dict[str, Any]]:
    return db.fetch_all(
        f"""
        {_GENERATION_SELECT}
        WHERE g.status = 'failed'
        ORDER BY g.created_at DESC, g.id DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


# ------------------------------------------------------------ users


def list_users(
    *,
    offset: int,
    limit: int,
    q: str | None = None,
    verified: bool | None = None,
    status: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[str] = []
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if q:
        conditions.append("(u.email ILIKE :q OR p.full_name ILIKE :q)")
        params["q"] = like_pattern(q)
    if verified is True:
        conditions.append("u.email_verified_at IS NOT NULL")
    elif verified is False:
        conditions.append("u.email_verified_at IS NULL")
    if status == "active":
        conditions.append("u.disabled_at IS NULL")
    elif status == "disabled":
        conditions.append("u.disabled_at IS NOT NULL")
    where = _where(conditions)

    with db.transaction() as tx:
        rows = tx.fetch_all(
            f"""
            {_USER_SELECT}
            {where}
            ORDER BY u.created_at DESC, u.id DESC
            OFFSET :offset LIMIT :limit
            """,
            params,
        )
        total = _count(
            tx,
            f"""
            SELECT count(*) AS total
            FROM users u LEFT JOIN profiles p ON p.user_id = u.id
            {where}
            """,
            params,
        )
    return rows, total


def get_user(user_id: str) -> dict[str, Any] | None:
    return db.fetch_one(
        f"{_USER_SELECT} WHERE u.id = CAST(:user_id AS uuid)",
        {"user_id": user_id},
    )


def get_user_target(user_id: str) -> dict[str, Any] | None:
    """The minimal row the action rules need (id and email)."""
    return db.fetch_one(
        "SELECT id, email FROM users WHERE id = CAST(:user_id AS uuid)",
        {"user_id": user_id},
    )


def list_user_brands(user_id: str) -> list[dict[str, Any]]:
    return db.fetch_all(
        """
        SELECT
            b.id, b.name,
            COALESCE(bk.status::text, 'not_started') AS kit_status,
            (SELECT count(*) FROM generations g WHERE g.brand_id = b.id) AS generation_count,
            b.created_at
        FROM brands b
        LEFT JOIN brand_kits bk ON bk.brand_id = b.id
        WHERE b.owner_user_id = CAST(:user_id AS uuid)
        ORDER BY b.created_at DESC, b.id DESC
        """,
        {"user_id": user_id},
    )


def list_user_generations(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    return db.fetch_all(
        f"""
        {_GENERATION_SELECT}
        WHERE b.owner_user_id = CAST(:user_id AS uuid)
        ORDER BY g.created_at DESC, g.id DESC
        LIMIT :limit
        """,
        {"user_id": user_id, "limit": limit},
    )


def list_user_ledger(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    return db.fetch_all(
        """
        SELECT id, operation, amount, metadata, created_at
        FROM credit_ledger
        WHERE user_id = CAST(:user_id AS uuid)
        ORDER BY created_at DESC, id DESC
        LIMIT :limit
        """,
        {"user_id": user_id, "limit": limit},
    )


# ------------------------------------------------------------ user actions
# Each returns None when the user does not exist (nothing is written then).


def verify_user_email(user_id: str, audit: dict[str, Any]) -> dict[str, Any] | None:
    with db.transaction() as tx:
        before = tx.fetch_one(
            "SELECT email_verified_at FROM users WHERE id = CAST(:user_id AS uuid) FOR UPDATE",
            {"user_id": user_id},
        )
        if before is None:
            return None
        row = tx.fetch_one(
            """
            UPDATE users SET email_verified_at = COALESCE(email_verified_at, now())
            WHERE id = CAST(:user_id AS uuid)
            RETURNING email_verified_at
            """,
            {"user_id": user_id},
        )
        details = {"already_verified": before["email_verified_at"] is not None}
        _insert_audit(tx, {**audit, "details": {**audit.get("details", {}), **details}})
        return row


def set_user_disabled(user_id: str, disabled: bool, audit: dict[str, Any]) -> dict[str, Any] | None:
    with db.transaction() as tx:
        before = tx.fetch_one(
            "SELECT disabled_at FROM users WHERE id = CAST(:user_id AS uuid) FOR UPDATE",
            {"user_id": user_id},
        )
        if before is None:
            return None
        new_value = "COALESCE(disabled_at, now())" if disabled else "NULL"
        row = tx.fetch_one(
            f"""
            UPDATE users SET disabled_at = {new_value}
            WHERE id = CAST(:user_id AS uuid)
            RETURNING disabled_at
            """,
            {"user_id": user_id},
        )
        details = {"was_disabled": before["disabled_at"] is not None}
        _insert_audit(tx, {**audit, "details": {**audit.get("details", {}), **details}})
        return row


def grant_generations(
    user_id: str,
    *,
    generations: int,
    credits: int,
    idempotency_key: str,
    metadata: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any] | None:
    """Raise the lifetime quota and the credit balance (one ``grant`` ledger row).

    ``admin_grant_generations`` (migration 0004) does both under the account
    lock; the audit row commits in the same transaction.
    """
    with db.transaction() as tx:
        if tx.fetch_one(
            "SELECT id FROM users WHERE id = CAST(:user_id AS uuid)", {"user_id": user_id}
        ) is None:
            return None
        row = tx.fetch_one(
            """
            SELECT admin_grant_generations(
                CAST(:user_id AS uuid), CAST(:generations AS integer),
                CAST(:credits AS integer), CAST(:idempotency_key AS text),
                CAST(:metadata AS jsonb)
            ) AS result
            """,
            {
                "user_id": user_id,
                "generations": generations,
                "credits": credits,
                "idempotency_key": idempotency_key,
                "metadata": db.json_param(metadata),
            },
        )
        if row is None or row.get("result") is None:
            raise RuntimeError("admin_grant_generations returned no result")
        _insert_audit(tx, audit)
        return row["result"]


def extend_trial(user_id: str, days: int, audit: dict[str, Any]) -> dict[str, Any] | None:
    with db.transaction() as tx:
        if tx.fetch_one(
            "SELECT id FROM users WHERE id = CAST(:user_id AS uuid)", {"user_id": user_id}
        ) is None:
            return None
        before = tx.fetch_one(
            "SELECT trial_ends_at FROM profiles WHERE user_id = CAST(:user_id AS uuid) FOR UPDATE",
            {"user_id": user_id},
        )
        # The signup trigger always creates the profile; the upsert covers a
        # missing row the same way.
        row = tx.fetch_one(
            """
            INSERT INTO profiles (user_id, trial_ends_at)
            VALUES (CAST(:user_id AS uuid), now() + make_interval(days => CAST(:days AS integer)))
            ON CONFLICT (user_id) DO UPDATE
            SET trial_ends_at = GREATEST(profiles.trial_ends_at, now())
                + make_interval(days => CAST(:days AS integer))
            RETURNING trial_ends_at
            """,
            {"user_id": user_id, "days": days},
        )
        assert row is not None
        details = {
            **audit.get("details", {}),
            "previous_trial_ends_at": before["trial_ends_at"] if before else None,
            "trial_ends_at": row["trial_ends_at"],
        }
        _insert_audit(tx, {**audit, "details": details})
        return row


def reset_daily_usage(user_id: str, audit: dict[str, Any]) -> dict[str, Any] | None:
    """Set today's ``consumed`` to 0; ``reserved`` (open reservations) is kept."""
    with db.transaction() as tx:
        if tx.fetch_one(
            "SELECT id FROM users WHERE id = CAST(:user_id AS uuid)", {"user_id": user_id}
        ) is None:
            return None
        before = tx.fetch_one(
            f"""
            SELECT usage_date, consumed, reserved FROM generation_daily_usage
            WHERE user_id = CAST(:user_id AS uuid) AND usage_date = {_TODAY_SQL}
            FOR UPDATE
            """,
            {"user_id": user_id},
        )
        if before is not None:
            tx.execute(
                """
                UPDATE generation_daily_usage SET consumed = 0, updated_at = now()
                WHERE user_id = CAST(:user_id AS uuid) AND usage_date = CAST(:usage_date AS date)
                """,
                {"user_id": user_id, "usage_date": before["usage_date"]},
            )
        details = {
            **audit.get("details", {}),
            "usage_date": before["usage_date"] if before else None,
            "previous_consumed": before["consumed"] if before else 0,
        }
        _insert_audit(tx, {**audit, "details": details})
        return {"usage_date": details["usage_date"], "previous_consumed": details["previous_consumed"]}


def delete_user(user_id: str, audit: dict[str, Any]) -> dict[str, Any] | None:
    """Delete the user (FKs cascade) and return the storage paths to clean up.

    Paths are collected inside the same transaction, before the cascade
    removes the rows that reference them. Storage is cleaned by the caller
    only after this commit, so a failed delete never loses files.
    """
    with db.transaction() as tx:
        user = tx.fetch_one(
            """
            SELECT u.id, u.email, p.avatar_path
            FROM users u LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id = CAST(:user_id AS uuid)
            FOR UPDATE OF u
            """,
            {"user_id": user_id},
        )
        if user is None:
            return None
        params = {"user_id": user_id}
        logos = tx.fetch_all(
            """
            SELECT logo_path AS path FROM brands
            WHERE owner_user_id = CAST(:user_id AS uuid) AND logo_path IS NOT NULL
            """,
            params,
        )
        images = tx.fetch_all(
            """
            SELECT g.image_path AS path
            FROM generations g JOIN brands b ON b.id = g.brand_id
            WHERE b.owner_user_id = CAST(:user_id AS uuid) AND g.image_path IS NOT NULL
            """,
            params,
        )
        assets = tx.fetch_all(
            """
            SELECT pa.storage_path AS path
            FROM product_assets pa
            WHERE pa.owner_user_id = CAST(:user_id AS uuid)
               OR pa.brand_id IN (
                   SELECT id FROM brands WHERE owner_user_id = CAST(:user_id AS uuid)
               )
            """,
            params,
        )
        brand_count = _count(
            tx,
            "SELECT count(*) AS total FROM brands WHERE owner_user_id = CAST(:user_id AS uuid)",
            params,
        )
        tx.execute("DELETE FROM users WHERE id = CAST(:user_id AS uuid)", params)
        details = {
            **audit.get("details", {}),
            "email": user["email"],
            "brands": brand_count,
            "generation_images": len(images),
            "product_assets": len(assets),
        }
        _insert_audit(tx, {**audit, "details": details})

    return {
        "email": user["email"],
        "brand_files": [r["path"] for r in logos] + [r["path"] for r in images],
        "product_asset_files": sorted({r["path"] for r in assets}),
        "avatar_files": [user["avatar_path"]] if user.get("avatar_path") else [],
    }


# ------------------------------------------------------------ brands


def list_brands(
    *,
    offset: int,
    limit: int,
    q: str | None = None,
    kit_status: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[str] = []
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if q:
        conditions.append("(b.name ILIKE :q OR u.email ILIKE :q)")
        params["q"] = like_pattern(q)
    if kit_status:
        conditions.append("COALESCE(bk.status::text, 'not_started') = :kit_status")
        params["kit_status"] = kit_status
    where = _where(conditions)

    with db.transaction() as tx:
        rows = tx.fetch_all(
            f"""
            SELECT
                b.id, b.name,
                u.id AS owner_id, u.email AS owner_email, p.full_name AS owner_full_name,
                COALESCE(bk.status::text, 'not_started') AS kit_status,
                COALESCE(cardinality(bk.colors), 0) AS colors_count,
                (b.logo_path IS NOT NULL) AS has_logo,
                (SELECT count(*) FROM generations g WHERE g.brand_id = b.id) AS generation_count,
                b.created_at
            {_BRAND_FROM}
            {where}
            ORDER BY b.created_at DESC, b.id DESC
            OFFSET :offset LIMIT :limit
            """,
            params,
        )
        total = _count(tx, f"SELECT count(*) AS total {_BRAND_FROM} {where}", params)
    return rows, total


# ------------------------------------------------------------ generations


def list_generations(
    *,
    offset: int,
    limit: int,
    status: str | None = None,
    provider: str | None = None,
    needs_review: bool | None = None,
    q: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[str] = []
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if status:
        conditions.append("g.status = CAST(:status AS generation_status_t)")
        params["status"] = status
    if provider:
        conditions.append("g.provider = CAST(:provider AS provider_t)")
        params["provider"] = provider
    if needs_review is True:
        conditions.append(NEEDS_REVIEW_SQL)
    elif needs_review is False:
        conditions.append(f"NOT {NEEDS_REVIEW_SQL}")
    if q:
        conditions.append("(u.email ILIKE :q OR b.name ILIKE :q)")
        params["q"] = like_pattern(q)
    if date_from is not None:
        conditions.append("g.created_at >= CAST(:date_from AS date)::timestamp AT TIME ZONE 'utc'")
        params["date_from"] = date_from.isoformat()
    if date_to is not None:
        # Inclusive: the whole "to" day (UTC).
        conditions.append(
            "g.created_at < (CAST(:date_to AS date) + 1)::timestamp AT TIME ZONE 'utc'"
        )
        params["date_to"] = date_to.isoformat()
    where = _where(conditions)

    with db.transaction() as tx:
        rows = tx.fetch_all(
            f"""
            {_GENERATION_SELECT}
            {where}
            ORDER BY g.created_at DESC, g.id DESC
            OFFSET :offset LIMIT :limit
            """,
            params,
        )
        total = _count(
            tx,
            f"""
            SELECT count(*) AS total
            FROM generations g
            JOIN brands b ON b.id = g.brand_id
            JOIN users u ON u.id = COALESCE(g.user_id, b.owner_user_id)
            {where}
            """,
            params,
        )
    return rows, total


# ------------------------------------------------------------ trends


def _trend_value_sql(field: str) -> str:
    if field in TREND_JSON_FIELDS:
        return f"CAST(:{field} AS jsonb)"
    if field in _TREND_CASTS:
        return f"CAST(:{field} AS {_TREND_CASTS[field]})"
    return f":{field}"


def _trend_params(values: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for field, value in values.items():
        if field in TREND_JSON_FIELDS:
            params[field] = db.json_param(list(value or []))
        elif isinstance(value, (dt.datetime, dt.date)):
            params[field] = value.isoformat()
        else:
            params[field] = value
    return params


def list_trends(
    *,
    offset: int,
    limit: int,
    q: str | None = None,
    status: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[str] = []
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if q:
        conditions.append("(name ILIKE :q OR slug ILIKE :q)")
        params["q"] = like_pattern(q)
    if status:
        conditions.append("status = :status")
        params["status"] = status
    where = _where(conditions)

    with db.transaction() as tx:
        rows = tx.fetch_all(
            f"""
            SELECT {_TREND_COLUMNS} FROM trends
            {where}
            ORDER BY created_at DESC, id DESC
            OFFSET :offset LIMIT :limit
            """,
            params,
        )
        total = _count(tx, f"SELECT count(*) AS total FROM trends {where}", params)
    return rows, total


def get_trend(trend_id: str) -> dict[str, Any] | None:
    return db.fetch_one(
        f"SELECT {_TREND_COLUMNS} FROM trends WHERE id = CAST(:trend_id AS uuid)",
        {"trend_id": trend_id},
    )


def create_trend(values: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    """Raises ``db.IntegrityError`` (trends_slug_key) when the slug is taken."""
    fields = [f for f in (*TREND_SCALAR_FIELDS, *TREND_JSON_FIELDS) if f in values]
    with db.transaction() as tx:
        row = tx.fetch_one(
            f"""
            INSERT INTO trends ({", ".join(fields)})
            VALUES ({", ".join(_trend_value_sql(f) for f in fields)})
            RETURNING {_TREND_COLUMNS}
            """,
            _trend_params({f: values[f] for f in fields}),
        )
        assert row is not None
        _insert_audit(
            tx,
            {
                **audit,
                "target_id": row["id"],
                "details": {"slug": row["slug"], "name": row["name"]},
            },
        )
    return row


def update_trend(
    trend_id: str, changes: dict[str, Any], audit: dict[str, Any]
) -> dict[str, Any] | None:
    """Apply a partial update. Raises ``db.IntegrityError`` on a taken slug."""
    fields = [f for f in (*TREND_SCALAR_FIELDS, *TREND_JSON_FIELDS) if f in changes]
    if not fields:
        return get_trend(trend_id)
    assignments = ", ".join(f"{f} = {_trend_value_sql(f)}" for f in fields)
    with db.transaction() as tx:
        row = tx.fetch_one(
            f"""
            UPDATE trends SET {assignments}, updated_at = now()
            WHERE id = CAST(:trend_id AS uuid)
            RETURNING {_TREND_COLUMNS}
            """,
            {**_trend_params({f: changes[f] for f in fields}), "trend_id": trend_id},
        )
        if row is None:
            return None
        _insert_audit(
            tx,
            {
                **audit,
                "target_id": row["id"],
                "details": {"slug": row["slug"], "fields": sorted(fields)},
            },
        )
    return row


def delete_trend(trend_id: str, audit: dict[str, Any]) -> dict[str, Any] | None:
    """Hard delete. ``generations.trend_id`` is ON DELETE SET NULL, so the
    generations keep their ``trend_snapshot``. Any FK that would block the
    delete surfaces as ``db.IntegrityError`` (SQLSTATE 23503)."""
    with db.transaction() as tx:
        referencing = _count(
            tx,
            "SELECT count(*) AS total FROM generations WHERE trend_id = CAST(:trend_id AS uuid)",
            {"trend_id": trend_id},
        )
        row = tx.fetch_one(
            "DELETE FROM trends WHERE id = CAST(:trend_id AS uuid) RETURNING id, slug, name",
            {"trend_id": trend_id},
        )
        if row is None:
            return None
        _insert_audit(
            tx,
            {
                **audit,
                "target_id": row["id"],
                "details": {
                    "slug": row["slug"],
                    "name": row["name"],
                    "generations_unlinked": referencing,
                },
            },
        )
    return row


# ------------------------------------------------------------ audit log


def list_audit_log(*, offset: int, limit: int) -> tuple[list[dict[str, Any]], int]:
    with db.transaction() as tx:
        rows = tx.fetch_all(
            """
            SELECT id, admin_email, action, target_type, target_id, details, created_at
            FROM admin_audit_log
            ORDER BY created_at DESC, id DESC
            OFFSET :offset LIMIT :limit
            """,
            {"offset": offset, "limit": limit},
        )
        total = _count(tx, "SELECT count(*) AS total FROM admin_audit_log", {})
    return rows, total
