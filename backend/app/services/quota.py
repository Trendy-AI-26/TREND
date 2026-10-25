from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID
from app import db

FREE_TRIAL_DAYS = 14
DAILY_GENERATION_LIMIT = 3

class QuotaError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

@dataclass(frozen=True)
class QuotaSummary:
    plan: str
    max_active_brands: int
    active_brands: int
    generation_limit: int
    generation_reserved: int
    generation_consumed: int
    generation_remaining: int
    daily_generation_limit: int = DAILY_GENERATION_LIMIT
    daily_generation_reserved: int = 0
    daily_generation_consumed: int = 0
    daily_generation_remaining: int = DAILY_GENERATION_LIMIT
    trial_ends_at: datetime | None = None
    trial_active: bool = True

def _call(sql: str, params: dict[str, Any]) -> Any:
    """Run ``SELECT <plpgsql function>(...) AS result`` and return the value."""
    row = db.fetch_one(sql, params)
    data = None if row is None else row.get("result")
    if data is None:
        raise QuotaError("QUOTA_RPC_EMPTY_RESPONSE", "Quota operation returned no data.")
    return data[0] if isinstance(data, list) and data else data

def _map_error(exc: Exception) -> QuotaError:
    message = str(exc).upper()
    if "TRIAL_EXPIRED" in message:
        return QuotaError("TRIAL_EXPIRED", "Your 14-day free trial has ended.")
    if "DAILY_GENERATION_LIMIT_REACHED" in message:
        return QuotaError("DAILY_GENERATION_LIMIT_REACHED", "You have reached the free trial limit of 3 image generations today.")
    if "GENERATION_LIMIT_REACHED" in message:
        return QuotaError("GENERATION_LIMIT_REACHED", "You have reached the free-plan limit.")
    if "BRAND_LIMIT_REACHED" in message:
        return QuotaError("BRAND_LIMIT_REACHED", "You can have up to 3 active brands on the free plan.")
    if "DUPLICATE_BRAND_NAME" in message or "UNIQUE" in message:
        return QuotaError("DUPLICATE_BRAND_NAME", "A brand with this name already exists.")
    if "RESERVATION_EXISTS" in message:
        return QuotaError("GENERATION_QUOTA_RESERVATION_EXISTS", "This generation quota was already reserved.")
    return QuotaError("QUOTA_OPERATION_FAILED", "The quota operation failed.")

def _slot_call(function: str, user_id: str, generation_id: UUID) -> None:
    db.fetch_one(
        f"SELECT {function}(CAST(:p_user_id AS uuid), CAST(:p_generation_id AS uuid)) AS result",
        {"p_user_id": user_id, "p_generation_id": str(generation_id)},
    )

def create_brand_if_allowed(*, user_id: str, name: str) -> dict:
    try:
        return _call(
            "SELECT create_brand_if_allowed(CAST(:p_user_id AS uuid), CAST(:p_name AS text)) AS result",
            {"p_user_id": user_id, "p_name": name},
        )
    except QuotaError:
        raise
    except Exception as exc:
        raise _map_error(exc) from exc

def reserve_generation_slot(*, user_id: str, generation_id: UUID) -> None:
    try:
        _slot_call("reserve_generation_slot", user_id, generation_id)
    except Exception as exc:
        raise _map_error(exc) from exc

def commit_generation_slot(*, user_id: str, generation_id: UUID) -> None:
    try:
        _slot_call("commit_generation_slot", user_id, generation_id)
    except Exception as exc:
        raise _map_error(exc) from exc

def release_generation_slot(*, user_id: str, generation_id: UUID) -> None:
    try:
        _slot_call("release_generation_slot", user_id, generation_id)
    except Exception as exc:
        raise _map_error(exc) from exc

def get_quota_summary(*, user_id: str) -> QuotaSummary:
    try:
        data = _call(
            "SELECT get_generation_quota_summary(CAST(:p_user_id AS uuid)) AS result",
            {"p_user_id": user_id},
        )
        trial_ends_at = data.get("trial_ends_at")
        if isinstance(trial_ends_at, str):
            trial_ends_at = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
        return QuotaSummary(
            plan=str(data.get("plan", "beta")),
            max_active_brands=int(data.get("max_active_brands", 3)),
            active_brands=int(data.get("active_brands", 0)),
            generation_limit=int(data.get("generation_limit", 42)),
            generation_reserved=int(data.get("generation_reserved", 0)),
            generation_consumed=int(data.get("generation_consumed", 0)),
            generation_remaining=int(data.get("generation_remaining", 0)),
            daily_generation_limit=int(data.get("daily_generation_limit", DAILY_GENERATION_LIMIT)),
            daily_generation_reserved=int(data.get("daily_generation_reserved", 0)),
            daily_generation_consumed=int(data.get("daily_generation_consumed", 0)),
            daily_generation_remaining=int(data.get("daily_generation_remaining", DAILY_GENERATION_LIMIT)),
            trial_ends_at=trial_ends_at,
            trial_active=bool(data.get("trial_active", True)),
        )
    except QuotaError:
        raise
    except Exception as exc:
        raise _map_error(exc) from exc
