from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.supabase import get_service_client


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


def _rpc_data(response: Any) -> Any:
    data = getattr(response, "data", None)
    if data is None:
        raise QuotaError(
            "QUOTA_RPC_EMPTY_RESPONSE",
            "Quota operation returned no data.",
        )
    return data[0] if isinstance(data, list) and data else data


def _map_error(exc: Exception) -> QuotaError:
    message = str(exc).upper()

    if "BRAND_LIMIT_REACHED" in message:
        return QuotaError(
            "BRAND_LIMIT_REACHED",
            "You can have up to 3 active brands on the free plan.",
        )

    if "DUPLICATE_BRAND_NAME" in message or "UNIQUE" in message:
        return QuotaError(
            "DUPLICATE_BRAND_NAME",
            "A brand with this name already exists.",
        )

    if "GENERATION_LIMIT_REACHED" in message:
        return QuotaError(
            "GENERATION_LIMIT_REACHED",
            "You have reached the 15-image free-plan limit.",
        )

    if "RESERVATION_EXISTS" in message:
        return QuotaError(
            "GENERATION_QUOTA_RESERVATION_EXISTS",
            "This generation quota was already reserved.",
        )

    return QuotaError(
        "QUOTA_OPERATION_FAILED",
        "The quota operation failed.",
    )


def create_brand_if_allowed(*, user_id: str, name: str) -> dict:
    try:
        response = (
            get_service_client()
            .rpc(
                "create_brand_if_allowed",
                {"p_user_id": user_id, "p_name": name},
            )
            .execute()
        )
        return _rpc_data(response)
    except QuotaError:
        raise
    except Exception as exc:
        raise _map_error(exc) from exc


def reserve_generation_slot(*, user_id: str, generation_id: UUID) -> None:
    try:
        get_service_client().rpc(
            "reserve_generation_slot",
            {"p_user_id": user_id, "p_generation_id": str(generation_id)},
        ).execute()
    except Exception as exc:
        raise _map_error(exc) from exc


def commit_generation_slot(*, user_id: str, generation_id: UUID) -> None:
    try:
        get_service_client().rpc(
            "commit_generation_slot",
            {"p_user_id": user_id, "p_generation_id": str(generation_id)},
        ).execute()
    except Exception as exc:
        raise _map_error(exc) from exc


def release_generation_slot(*, user_id: str, generation_id: UUID) -> None:
    try:
        get_service_client().rpc(
            "release_generation_slot",
            {"p_user_id": user_id, "p_generation_id": str(generation_id)},
        ).execute()
    except Exception as exc:
        raise _map_error(exc) from exc


def get_quota_summary(*, user_id: str) -> QuotaSummary:
    try:
        response = (
            get_service_client()
            .rpc(
                "get_generation_quota_summary",
                {"p_user_id": user_id},
            )
            .execute()
        )

        data = _rpc_data(response)

        return QuotaSummary(
            plan=str(data.get("plan", "beta")),
            max_active_brands=int(data.get("max_active_brands", 3)),
            active_brands=int(data.get("active_brands", 0)),
            generation_limit=int(data.get("generation_limit", 15)),
            generation_reserved=int(data.get("generation_reserved", 0)),
            generation_consumed=int(data.get("generation_consumed", 0)),
            generation_remaining=int(data.get("generation_remaining", 0)),
        )
    except QuotaError:
        raise
    except Exception as exc:
        raise _map_error(exc) from exc
