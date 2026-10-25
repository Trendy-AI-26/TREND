from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from app import db

GENERATION_CREDIT_COST = 1


class CreditsError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CreditReservation:
    reservation_id: str
    user_id: str
    generation_id: str
    amount: int


def _call(sql: str, params: dict[str, Any]) -> Any:
    """Run ``SELECT <plpgsql function>(...) AS result`` and return the value."""
    row = db.fetch_one(sql, params)

    if row is None or row.get("result") is None:
        raise CreditsError(
            "CREDITS_RPC_EMPTY_RESPONSE",
            "The credits function returned an empty response.",
        )

    return row["result"]


def _map_rpc_error(exc: Exception) -> CreditsError:
    """
    Convert database errors into stable application errors.
    """

    raw_message = str(exc)
    normalized = raw_message.upper()

    if "INSUFFICIENT_CREDITS" in normalized:
        return CreditsError(
            "INSUFFICIENT_CREDITS",
            "You do not have enough credits to generate an image.",
        )

    if "IDEMPOTENCY_KEY_REUSED" in normalized:
        return CreditsError(
            "IDEMPOTENCY_KEY_REUSED",
            "This credit operation was already used with another request.",
        )

    if "RESERVATION_NOT_FOUND" in normalized:
        return CreditsError(
            "CREDIT_RESERVATION_NOT_FOUND",
            "The credit reservation was not found.",
        )

    if "ALREADY_COMMITTED" in normalized:
        return CreditsError(
            "CREDIT_ALREADY_COMMITTED",
            "This credit reservation was already committed.",
        )

    if "ALREADY_RELEASED" in normalized:
        return CreditsError(
            "CREDIT_ALREADY_RELEASED",
            "This credit reservation was already released.",
        )

    return CreditsError(
        "CREDITS_OPERATION_FAILED",
        "The credits operation failed.",
    )


def _read_reservation(
    *,
    data: Any,
    user_id: str,
    generation_id: UUID,
    amount: int,
    fallback_reservation_id: str,
) -> CreditReservation:
    """
    Convert the function result into the Python reservation object.
    """

    if isinstance(data, list):
        data = data[0] if data else {}

    if not isinstance(data, dict):
        data = {}

    reservation_id = str(
        data.get("reservation_id") or data.get("id") or fallback_reservation_id
    )

    returned_amount = int(data.get("amount") or amount)

    return CreditReservation(
        reservation_id=reservation_id,
        user_id=user_id,
        generation_id=str(generation_id),
        amount=returned_amount,
    )


def get_available_credits(user_id: str) -> int:
    """
    Read the available credit balance.

    This is a read-only operation. The actual reservation must still
    be performed through the reserve_generation_credit function.
    """

    try:
        data = _call(
            "SELECT get_available_credits(CAST(:p_user_id AS uuid)) AS result",
            {"p_user_id": user_id},
        )

        if isinstance(data, list):
            data = data[0] if data else {}

        if isinstance(data, dict):
            return max(
                int(data.get("available_credits", 0)),
                0,
            )

        return max(int(data), 0)

    except CreditsError:
        raise
    except Exception as exc:
        raise _map_rpc_error(exc) from exc


def reserve_credits(
    *,
    user_id: str,
    generation_id: UUID,
    amount: int = GENERATION_CREDIT_COST,
    idempotency_key: str | None = None,
) -> CreditReservation:
    """
    Reserve credits atomically inside PostgreSQL.

    The balance check and reservation happen together inside the function.
    Do not read the balance and update it separately in Python.
    """

    if amount <= 0:
        raise ValueError("Credit amount must be positive.")

    reservation_id = idempotency_key or f"credit-reservation-{uuid4()}"

    params = {
        "p_user_id": user_id,
        "p_generation_id": str(generation_id),
        "p_amount": amount,
        "p_idempotency_key": reservation_id,
    }

    try:
        data = _call(
            "SELECT reserve_generation_credit("
            "CAST(:p_user_id AS uuid), CAST(:p_generation_id AS uuid), "
            "CAST(:p_amount AS integer), CAST(:p_idempotency_key AS text)) AS result",
            params,
        )

        return _read_reservation(
            data=data,
            user_id=user_id,
            generation_id=generation_id,
            amount=amount,
            fallback_reservation_id=reservation_id,
        )

    except CreditsError:
        raise
    except Exception as exc:
        raise _map_rpc_error(exc) from exc


def commit_credits(
    reservation: CreditReservation,
) -> None:
    """
    Permanently consume a successful reservation.
    """

    try:
        db.fetch_one(
            "SELECT commit_generation_credit("
            "CAST(:p_user_id AS uuid), CAST(:p_generation_id AS uuid), "
            "CAST(:p_reservation_id AS text), CAST(:p_amount AS integer)) AS result",
            {
                "p_user_id": reservation.user_id,
                "p_generation_id": reservation.generation_id,
                "p_reservation_id": reservation.reservation_id,
                "p_amount": reservation.amount,
            },
        )

    except Exception as exc:
        raise _map_rpc_error(exc) from exc


def release_credits(
    reservation: CreditReservation | None = None,
    *,
    user_id: str | None = None,
    generation_id: UUID | str | None = None,
    amount: int | None = None,
    reservation_id: str | None = None,
) -> None:
    """
    Release a reservation after provider/storage failure.

    The function supports both forms:

        release_credits(reservation)

    and the explicit keyword form used by older code.
    """

    if reservation is not None:
        resolved_user_id = reservation.user_id
        resolved_generation_id = reservation.generation_id
        resolved_amount = reservation.amount
        resolved_reservation_id = reservation.reservation_id
    else:
        if (
            user_id is None
            or generation_id is None
            or amount is None
            or reservation_id is None
        ):
            raise ValueError(
                "A reservation or all explicit credit fields are required."
            )

        resolved_user_id = user_id
        resolved_generation_id = str(generation_id)
        resolved_amount = amount
        resolved_reservation_id = reservation_id

    try:
        db.fetch_one(
            "SELECT release_generation_credit("
            "CAST(:p_user_id AS uuid), CAST(:p_generation_id AS uuid), "
            "CAST(:p_reservation_id AS text), CAST(:p_amount AS integer)) AS result",
            {
                "p_user_id": resolved_user_id,
                "p_generation_id": resolved_generation_id,
                "p_reservation_id": resolved_reservation_id,
                "p_amount": resolved_amount,
            },
        )

    except Exception as exc:
        raise _map_rpc_error(exc) from exc


__all__ = [
    "GENERATION_CREDIT_COST",
    "CreditReservation",
    "CreditsError",
    "commit_credits",
    "get_available_credits",
    "release_credits",
    "reserve_credits",
]
