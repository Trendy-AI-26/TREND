from __future__ import annotations

import time
from uuid import UUID

from app import db


def start_usage(
    *,
    user_id: str,
    generation_id: UUID,
    feature: str,
    provider: str,
    model: str,
    credits: int,
) -> str:
    started = db.fetch_one(
        """
        INSERT INTO usage_events
            (user_id, generation_id, feature, provider, model, status, units, credits)
        VALUES
            (CAST(:user_id AS uuid), CAST(:generation_id AS uuid), :feature, :provider,
             :model, 'started', 1, :credits)
        RETURNING id
        """,
        {
            "user_id": user_id,
            "generation_id": str(generation_id),
            "feature": feature,
            "provider": provider,
            "model": model,
            "credits": credits,
        },
    )

    if not started:
        raise RuntimeError("Could not create usage event.")

    return str(started["id"])


def finish_usage(
    *,
    usage_id: str,
    status: str,
    duration_ms: int,
    request_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    if status not in {"succeeded", "failed"}:
        raise ValueError("Usage status must be succeeded or failed.")

    db.execute(
        """
        UPDATE usage_events
        SET status = :status,
            duration_ms = :duration_ms,
            request_id = :request_id,
            metadata = CAST(:metadata AS jsonb)
        WHERE id = CAST(:usage_id AS uuid)
        """,
        {
            "status": status,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "metadata": db.json_param(metadata or {}),
            "usage_id": usage_id,
        },
    )


class UsageTimer:
    def __init__(
        self,
        *,
        user_id: str,
        generation_id: UUID,
        feature: str,
        provider: str,
        model: str,
        credits: int,
    ) -> None:
        self.user_id = user_id
        self.generation_id = generation_id
        self.feature = feature
        self.provider = provider
        self.model = model
        self.credits = credits
        self.usage_id: str | None = None
        self.started_at: float | None = None

    def start(self) -> None:
        self.started_at = time.monotonic()

        self.usage_id = start_usage(
            user_id=self.user_id,
            generation_id=self.generation_id,
            feature=self.feature,
            provider=self.provider,
            model=self.model,
            credits=self.credits,
        )

    def finish(
        self,
        *,
        status: str,
        metadata: dict | None = None,
        provider_request_id: str | None = None,
    ) -> None:
        duration_ms = self.duration_ms()

        # Must UPDATE the row created by start(); inserting here would leave a
        # dangling "started" row per generation and double-count usage.
        db.execute(
            """
            UPDATE usage_events
            SET status = :status,
                duration_ms = :duration_ms,
                metadata = CAST(:metadata AS jsonb),
                provider_request_id = COALESCE(:provider_request_id, provider_request_id)
            WHERE id = CAST(:usage_id AS uuid)
            """,
            {
                "status": status,
                "duration_ms": duration_ms,
                "metadata": db.json_param(metadata or {}),
                "provider_request_id": provider_request_id,
                "usage_id": self.usage_id,
            },
        )

    def duration_ms(self) -> int:
        if self.started_at is None:
            return 0

        return int((time.monotonic() - self.started_at) * 1000)


__all__ = [
    "UsageTimer",
    "finish_usage",
    "start_usage",
]
