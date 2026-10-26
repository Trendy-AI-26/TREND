"""Admin API (everything under /admin, gated by ADMIN_EMAILS).

Handlers are plain ``def`` so FastAPI runs the blocking database and storage
calls in its worker threads.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import status as http_status

from app import db
from app.config import settings
from app.core import storage
from app.core.auth import User, get_current_admin_user, is_admin_email
from app.models.admin import (
    AdminBrand,
    AdminOverview,
    AdminStatsResponse,
    AdminUser,
    AdminUserBrand,
    AdminUserDetail,
    AuditLogEntry,
    BrandOwner,
    BrandRef,
    CreditLedgerEntry,
    CreditsInfo,
    DailyPoint,
    ExtendTrialRequest,
    GenerationProviderBreakdown,
    GenerationRow,
    GenerationStatusBreakdown,
    GrantGenerationsRequest,
    OverviewAttention,
    OverviewBrands,
    OverviewCost,
    OverviewGenerations,
    OverviewUsers,
    Page,
    QuotaInfo,
    TodayUsage,
    Trend,
    TrendCreate,
    TrendUpdate,
    UserRef,
)
from app.repositories import admin as admin_repo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)],
)

DEFAULT_PER_PAGE = 24
MAX_PER_PAGE = 100
DAILY_DAYS = 30
NEEDS_REVIEW_LIMIT = 20
RECENT_FAILURES_LIMIT = 10
USER_RECENT_GENERATIONS = 10
USER_LEDGER_ENTRIES = 20
STORAGE_DELETE_BATCH = 1000

GenerationStatus = Literal["pending", "processing", "succeeded", "failed"]
Provider = Literal["openai", "gemini"]
KitStatus = Literal["not_started", "in_progress", "complete"]
TrendStatus = Literal["active", "inactive", "expired"]


def _error_response(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "request_id": str(uuid4())}},
    )


def _page_bounds(page: int, per_page: int) -> tuple[int, int]:
    """Validate pagination and return ``(offset, limit)``."""
    if page < 1:
        raise _error_response(
            400,
            "VALIDATION_ERROR",
            "page must be greater than or equal to 1",
        )
    if per_page < 1 or per_page > MAX_PER_PAGE:
        raise _error_response(
            400,
            "VALIDATION_ERROR",
            f"per_page must be between 1 and {MAX_PER_PAGE}",
        )
    return (page - 1) * per_page, per_page


def _search(q: str | None) -> str | None:
    if q is None:
        return None
    cleaned = q.strip()
    return cleaned or None


def _parse_id(raw: str, code: str, message: str) -> str:
    """Canonical UUID text; anything that is not a UUID is an unknown id."""
    try:
        return str(UUID(raw))
    except (ValueError, AttributeError, TypeError):
        raise _error_response(404, code, message) from None


def _user_id(raw: str) -> str:
    return _parse_id(raw, "USER_NOT_FOUND", "User not found")


def _trend_id(raw: str) -> str:
    return _parse_id(raw, "TREND_NOT_FOUND", "Trend not found")


def _user_not_found() -> HTTPException:
    return _error_response(404, "USER_NOT_FOUND", "User not found")


def _trend_not_found() -> HTTPException:
    return _error_response(404, "TREND_NOT_FOUND", "Trend not found")


def _audit(
    admin: User,
    action: str,
    target_type: str,
    target_id: str | None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "admin_user_id": admin.id,
        "admin_email": admin.email,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details or {},
    }


# ------------------------------------------------------------ row mapping


def _int(value: Any) -> int:
    return int(value or 0)


def _image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return storage.public_url(settings.STORAGE_BUCKET, image_path)


def _to_generation_row(row: dict[str, Any]) -> GenerationRow:
    return GenerationRow(
        id=str(row["id"]),
        status=row["status"],
        provider=row["provider"],
        model=row["model"],
        platform_preset=row["platform_preset"],
        error_code=row.get("error_code"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
        image_url=_image_url(row.get("image_path")),
        needs_review=bool(row.get("needs_review")),
        brand=BrandRef(id=str(row["brand_id"]), name=row["brand_name"]),
        user=UserRef(id=str(row["user_id"]), email=row["user_email"]),
    )


def _user_fields(row: dict[str, Any]) -> dict[str, Any]:
    quota = None
    if row.get("quota_limit") is not None:
        limit, consumed, reserved = (
            _int(row["quota_limit"]),
            _int(row.get("quota_consumed")),
            _int(row.get("quota_reserved")),
        )
        quota = QuotaInfo(
            limit=limit,
            consumed=consumed,
            reserved=reserved,
            remaining=max(limit - consumed - reserved, 0),
        )
    credits = None
    if row.get("credits_balance") is not None:
        balance, reserved = _int(row["credits_balance"]), _int(row.get("credits_reserved"))
        credits = CreditsInfo(
            balance=balance, reserved=reserved, available=max(balance - reserved, 0)
        )
    today = None
    if row.get("today_limit") is not None:
        today = TodayUsage(
            limit=_int(row["today_limit"]),
            consumed=_int(row.get("today_consumed")),
            reserved=_int(row.get("today_reserved")),
        )
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "full_name": row.get("full_name"),
        "email_verified": row.get("email_verified_at") is not None,
        "disabled": row.get("disabled_at") is not None,
        "is_admin": is_admin_email(row["email"]),
        "created_at": row["created_at"],
        "trial_ends_at": row.get("trial_ends_at"),
        "brands_count": _int(row.get("brands_count")),
        "generations_count": _int(row.get("generations_count")),
        "generations_succeeded": _int(row.get("generations_succeeded")),
        "quota": quota,
        "credits": credits,
        "today": today,
    }


def _to_admin_user(row: dict[str, Any]) -> AdminUser:
    return AdminUser(**_user_fields(row))


def _to_admin_brand(row: dict[str, Any]) -> AdminBrand:
    return AdminBrand(
        id=str(row["id"]),
        name=row["name"],
        owner=BrandOwner(
            id=str(row["owner_id"]),
            email=row["owner_email"],
            full_name=row.get("owner_full_name"),
        ),
        kit_status=row["kit_status"],
        colors_count=_int(row.get("colors_count")),
        has_logo=bool(row.get("has_logo")),
        generation_count=_int(row.get("generation_count")),
        created_at=row["created_at"],
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item if isinstance(item, str) else str(item) for item in value if item is not None]


def _to_trend(row: dict[str, Any]) -> Trend:
    data = dict(row)
    for field in admin_repo.TREND_JSON_FIELDS:
        data[field] = _string_list(data.get(field))
    data["id"] = str(data["id"])
    return Trend(**data)


def _current_user_or_404(user_id: str) -> AdminUser:
    row = admin_repo.get_user(user_id)
    if row is None:
        raise _user_not_found()
    return _to_admin_user(row)


def _daily_series(rows: list[dict[str, Any]]) -> list[DailyPoint]:
    """Exactly DAILY_DAYS UTC days, oldest first, ending today, zero-filled."""
    by_day: dict[date, dict[str, Any]] = {}
    for row in rows:
        day = row["date"]
        if isinstance(day, str):
            day = date.fromisoformat(day[:10])
        by_day[day] = row
    # The database's "today" wins, so app/DB clock skew cannot shift the window.
    end = max(by_day) if by_day else datetime.now(timezone.utc).date()
    series = []
    for offset in range(DAILY_DAYS - 1, -1, -1):
        day = end - timedelta(days=offset)
        row = by_day.get(day, {})
        series.append(
            DailyPoint(
                date=day,
                succeeded=_int(row.get("succeeded")),
                failed=_int(row.get("failed")),
            )
        )
    return series


# ------------------------------------------------------------ compatibility


def _to_stats_response(row: dict) -> AdminStatsResponse:
    return AdminStatsResponse(
        total_accounts=row["total_accounts"],
        total_brands=row["total_brands"],
        total_generations=row["total_generations"],
        generations_by_status=GenerationStatusBreakdown(
            pending=row["generations_pending"],
            processing=row["generations_processing"],
            succeeded=row["generations_succeeded"],
            failed=row["generations_failed"],
        ),
        generations_by_provider=GenerationProviderBreakdown(
            openai=row["generations_openai"],
            gemini=row["generations_gemini"],
        ),
        generations_last_7d=row["generations_last_7d"],
        generations_last_30d=row["generations_last_30d"],
        brand_kits_complete=row["brand_kits_complete"],
        active_provider_keys=row["active_provider_keys"],
    )


@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats() -> AdminStatsResponse:
    return _to_stats_response(admin_repo.get_stats())


# ------------------------------------------------------------ overview


@router.get("/overview", response_model=AdminOverview)
def get_overview() -> AdminOverview:
    counts = admin_repo.get_overview_counts()
    daily_rows = admin_repo.get_daily_outcomes(DAILY_DAYS)
    needs_review = admin_repo.list_needs_review(NEEDS_REVIEW_LIMIT)
    recent_failures = admin_repo.list_recent_failures(RECENT_FAILURES_LIMIT)

    succeeded_30d = _int(counts.get("generations_succeeded_30d"))
    failed_30d = _int(counts.get("generations_failed_30d"))
    finished_30d = succeeded_30d + failed_30d
    cost = counts.get("estimated_provider_cost_30d")

    return AdminOverview(
        users=OverviewUsers(
            total=_int(counts.get("users_total")),
            verified=_int(counts.get("users_verified")),
            new_7d=_int(counts.get("users_new_7d")),
            disabled=_int(counts.get("users_disabled")),
        ),
        brands=OverviewBrands(
            total=_int(counts.get("brands_total")),
            kits_complete=_int(counts.get("brands_kits_complete")),
        ),
        generations=OverviewGenerations(
            total=_int(counts.get("generations_total")),
            today=_int(counts.get("generations_today")),
            last_7d=_int(counts.get("generations_last_7d")),
            last_30d=_int(counts.get("generations_last_30d")),
            succeeded=_int(counts.get("generations_succeeded")),
            failed=_int(counts.get("generations_failed")),
            pending=_int(counts.get("generations_pending")),
            processing=_int(counts.get("generations_processing")),
            success_rate_30d=(succeeded_30d / finished_30d) if finished_30d else None,
        ),
        cost=OverviewCost(
            credits_charged_30d=_int(counts.get("credits_charged_30d")),
            estimated_provider_cost_30d=None if cost is None else float(cost),
        ),
        daily=_daily_series(daily_rows),
        attention=OverviewAttention(
            needs_review=[_to_generation_row(row) for row in needs_review],
            recent_failures=[_to_generation_row(row) for row in recent_failures],
        ),
    )


# ------------------------------------------------------------ users


@router.get("/users", response_model=Page[AdminUser])
def list_users(
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
    q: str | None = None,
    verified: bool | None = None,
    status: Literal["active", "disabled"] | None = None,
) -> Page[AdminUser]:
    offset, limit = _page_bounds(page, per_page)
    rows, total = admin_repo.list_users(
        offset=offset, limit=limit, q=_search(q), verified=verified, status=status
    )
    return Page[AdminUser](
        items=[_to_admin_user(row) for row in rows],
        page=page,
        per_page=per_page,
        total=total,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(user_id: str) -> AdminUserDetail:
    user_id = _user_id(user_id)
    row = admin_repo.get_user(user_id)
    if row is None:
        raise _user_not_found()
    return AdminUserDetail(
        **_user_fields(row),
        brands=[
            AdminUserBrand(
                id=str(brand["id"]),
                name=brand["name"],
                kit_status=brand["kit_status"],
                generation_count=_int(brand.get("generation_count")),
                created_at=brand["created_at"],
            )
            for brand in admin_repo.list_user_brands(user_id)
        ],
        recent_generations=[
            _to_generation_row(gen)
            for gen in admin_repo.list_user_generations(user_id, USER_RECENT_GENERATIONS)
        ],
        credit_ledger=[
            CreditLedgerEntry(
                id=str(entry["id"]),
                operation=entry["operation"],
                amount=_int(entry.get("amount")),
                metadata=entry.get("metadata") or {},
                created_at=entry["created_at"],
            )
            for entry in admin_repo.list_user_ledger(user_id, USER_LEDGER_ENTRIES)
        ],
    )


def _protected_target(admin: User, user_id: str) -> dict[str, Any]:
    """Load the target of disable/enable/delete and apply the admin-target rules."""
    target = admin_repo.get_user_target(user_id)
    if target is None:
        raise _user_not_found()
    # The caller's own email is always in ADMIN_EMAILS, so is_admin_email
    # also covers "yourself" under any id.
    if str(target["id"]) == admin.id or is_admin_email(target["email"] or ""):
        raise _error_response(
            403,
            "ADMIN_TARGET_FORBIDDEN",
            "This action is not allowed on your own account or on an admin account.",
        )
    return target


@router.post("/users/{user_id}/verify-email", response_model=AdminUser)
def verify_user_email(
    user_id: str, admin: User = Depends(get_current_admin_user)
) -> AdminUser:
    user_id = _user_id(user_id)
    if admin_repo.verify_user_email(user_id, _audit(admin, "user.verify_email", "user", user_id)) is None:
        raise _user_not_found()
    return _current_user_or_404(user_id)


@router.post("/users/{user_id}/disable", response_model=AdminUser)
def disable_user(user_id: str, admin: User = Depends(get_current_admin_user)) -> AdminUser:
    user_id = _user_id(user_id)
    _protected_target(admin, user_id)
    if admin_repo.set_user_disabled(
        user_id, True, _audit(admin, "user.disable", "user", user_id)
    ) is None:
        raise _user_not_found()
    return _current_user_or_404(user_id)


@router.post("/users/{user_id}/enable", response_model=AdminUser)
def enable_user(user_id: str, admin: User = Depends(get_current_admin_user)) -> AdminUser:
    user_id = _user_id(user_id)
    _protected_target(admin, user_id)
    if admin_repo.set_user_disabled(
        user_id, False, _audit(admin, "user.enable", "user", user_id)
    ) is None:
        raise _user_not_found()
    return _current_user_or_404(user_id)


@router.post("/users/{user_id}/grant-generations", response_model=AdminUser)
def grant_generations(
    user_id: str,
    body: GrantGenerationsRequest,
    admin: User = Depends(get_current_admin_user),
) -> AdminUser:
    user_id = _user_id(user_id)
    # One generation reserves GENERATION_CREDIT_COST credits, so this many
    # credits are needed for `amount` more generations (1:1 by default).
    credits = body.amount * max(settings.GENERATION_CREDIT_COST, 1)
    idempotency_key = f"admin-grant:{uuid4()}"
    metadata = {
        "source": "admin",
        "admin_user_id": admin.id,
        "admin_email": admin.email,
        "note": body.note,
    }
    details = {
        "amount": body.amount,
        "credits": credits,
        "note": body.note,
        "ledger_idempotency_key": idempotency_key,
    }
    result = admin_repo.grant_generations(
        user_id,
        generations=body.amount,
        credits=credits,
        idempotency_key=idempotency_key,
        metadata=metadata,
        audit=_audit(admin, "user.grant_generations", "user", user_id, details),
    )
    if result is None:
        raise _user_not_found()
    return _current_user_or_404(user_id)


@router.post("/users/{user_id}/extend-trial", response_model=AdminUser)
def extend_trial(
    user_id: str,
    body: ExtendTrialRequest,
    admin: User = Depends(get_current_admin_user),
) -> AdminUser:
    user_id = _user_id(user_id)
    audit = _audit(admin, "user.extend_trial", "user", user_id, {"days": body.days})
    if admin_repo.extend_trial(user_id, body.days, audit) is None:
        raise _user_not_found()
    return _current_user_or_404(user_id)


@router.post("/users/{user_id}/reset-daily-usage", response_model=AdminUser)
def reset_daily_usage(
    user_id: str, admin: User = Depends(get_current_admin_user)
) -> AdminUser:
    user_id = _user_id(user_id)
    audit = _audit(admin, "user.reset_daily_usage", "user", user_id)
    if admin_repo.reset_daily_usage(user_id, audit) is None:
        raise _user_not_found()
    return _current_user_or_404(user_id)


def _remove_files(bucket: str, paths: list[str]) -> None:
    """Best effort: failures are logged and never undo or block the delete."""
    unique = sorted({path for path in paths if path})
    for start in range(0, len(unique), STORAGE_DELETE_BATCH):
        batch = unique[start : start + STORAGE_DELETE_BATCH]
        try:
            storage.remove(bucket, batch)
        except storage.ObjectNotFoundError:
            pass  # already gone
        except Exception:
            logger.warning(
                "Admin user delete: could not remove %d object(s) from %s",
                len(batch),
                bucket,
                exc_info=True,
            )


@router.delete("/users/{user_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, admin: User = Depends(get_current_admin_user)) -> Response:
    user_id = _user_id(user_id)
    _protected_target(admin, user_id)
    removed = admin_repo.delete_user(user_id, _audit(admin, "user.delete", "user", user_id))
    if removed is None:
        raise _user_not_found()
    _remove_files(settings.STORAGE_BUCKET, removed["brand_files"])
    _remove_files(settings.PRODUCT_ASSETS_BUCKET, removed["product_asset_files"])
    _remove_files(settings.AVATARS_BUCKET, removed["avatar_files"])
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------ brands


@router.get("/brands", response_model=Page[AdminBrand])
def list_admin_brands(
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
    q: str | None = None,
    kit_status: KitStatus | None = None,
) -> Page[AdminBrand]:
    offset, limit = _page_bounds(page, per_page)
    rows, total = admin_repo.list_brands(
        offset=offset, limit=limit, q=_search(q), kit_status=kit_status
    )
    return Page[AdminBrand](
        items=[_to_admin_brand(row) for row in rows],
        page=page,
        per_page=per_page,
        total=total,
    )


# ------------------------------------------------------------ generations


@router.get("/generations", response_model=Page[GenerationRow])
def list_generations(
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
    status: GenerationStatus | None = None,
    provider: Provider | None = None,
    needs_review: bool | None = None,
    q: str | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
) -> Page[GenerationRow]:
    offset, limit = _page_bounds(page, per_page)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise _error_response(400, "VALIDATION_ERROR", "from must be on or before to")
    rows, total = admin_repo.list_generations(
        offset=offset,
        limit=limit,
        status=status,
        provider=provider,
        needs_review=needs_review,
        q=_search(q),
        date_from=date_from,
        date_to=date_to,
    )
    return Page[GenerationRow](
        items=[_to_generation_row(row) for row in rows],
        page=page,
        per_page=per_page,
        total=total,
    )


# ------------------------------------------------------------ trends


def _slug_taken() -> HTTPException:
    return _error_response(409, "TREND_SLUG_TAKEN", "A trend with this slug already exists")


def _is_foreign_key_violation(exc: BaseException) -> bool:
    return getattr(getattr(exc, "orig", None), "sqlstate", None) == "23503"


@router.get("/trends", response_model=Page[Trend])
def list_trends(
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
    q: str | None = None,
    status: TrendStatus | None = None,
) -> Page[Trend]:
    offset, limit = _page_bounds(page, per_page)
    rows, total = admin_repo.list_trends(offset=offset, limit=limit, q=_search(q), status=status)
    return Page[Trend](
        items=[_to_trend(row) for row in rows],
        page=page,
        per_page=per_page,
        total=total,
    )


@router.post("/trends", response_model=Trend, status_code=http_status.HTTP_201_CREATED)
def create_trend(body: TrendCreate, admin: User = Depends(get_current_admin_user)) -> Trend:
    try:
        row = admin_repo.create_trend(
            body.model_dump(), _audit(admin, "trend.create", "trend", None)
        )
    except db.IntegrityError as exc:
        if db.is_unique_violation(exc):
            raise _slug_taken() from exc
        raise
    return _to_trend(row)


@router.patch("/trends/{trend_id}", response_model=Trend)
def update_trend(
    trend_id: str,
    body: TrendUpdate,
    admin: User = Depends(get_current_admin_user),
) -> Trend:
    trend_id = _trend_id(trend_id)
    try:
        row = admin_repo.update_trend(
            trend_id, body.changes(), _audit(admin, "trend.update", "trend", trend_id)
        )
    except db.IntegrityError as exc:
        if db.is_unique_violation(exc):
            raise _slug_taken() from exc
        raise
    if row is None:
        raise _trend_not_found()
    return _to_trend(row)


@router.delete("/trends/{trend_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_trend(trend_id: str, admin: User = Depends(get_current_admin_user)) -> Response:
    trend_id = _trend_id(trend_id)
    try:
        row = admin_repo.delete_trend(trend_id, _audit(admin, "trend.delete", "trend", trend_id))
    except db.IntegrityError as exc:
        # generations.trend_id is ON DELETE SET NULL today; this guards any
        # future reference that would block the delete.
        if _is_foreign_key_violation(exc):
            raise _error_response(
                409,
                "TREND_IN_USE",
                "This trend is still referenced. Set its status to inactive instead.",
            ) from exc
        raise
    if row is None:
        raise _trend_not_found()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------ audit log


@router.get("/audit-log", response_model=Page[AuditLogEntry])
def list_audit_log(page: int = 1, per_page: int = DEFAULT_PER_PAGE) -> Page[AuditLogEntry]:
    offset, limit = _page_bounds(page, per_page)
    rows, total = admin_repo.list_audit_log(offset=offset, limit=limit)
    return Page[AuditLogEntry](
        items=[
            AuditLogEntry(
                id=str(row["id"]),
                admin_email=row["admin_email"],
                action=row["action"],
                target_type=row["target_type"],
                target_id=row.get("target_id"),
                details=row.get("details") or {},
                created_at=row["created_at"],
            )
            for row in rows
        ],
        page=page,
        per_page=per_page,
        total=total,
    )
