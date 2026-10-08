from __future__ import annotations

import time
from uuid import UUID

from app.core.supabase import get_service_client


def start_usage(
    *,
    user_id: str,
    generation_id: UUID,
    feature: str,
    provider: str,
    model: str,
    credits: int,
) -> str:
    client = get_service_client()

    started = (
        client.table("usage_events")
        .insert(
            {
                "user_id": user_id,
                "generation_id": str(generation_id),
                "feature": feature,
                "provider": provider,
                "model": model,
                "status": "started",
                "units": 1,
                "credits": credits,
            }
        )
        .execute()
    )

    if not started.data:
        raise RuntimeError("Could not create usage event.")

    return str(started.data[0]["id"])


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

    client = get_service_client()

    client.table("usage_events").update(
        {
            "status": status,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "metadata": metadata or {},
        }
    ).eq("id", usage_id).execute()


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
        payload = {
            "status": status,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        }

        if provider_request_id is not None:
            payload["provider_request_id"] = provider_request_id

        get_service_client().table("usage_events").update(payload).eq(
            "id", self.usage_id
        ).execute()

    def duration_ms(self) -> int:
        if self.started_at is None:
            return 0

        return int((time.monotonic() - self.started_at) * 1000)


__all__ = [
    "UsageTimer",
    "finish_usage",
    "start_usage",
]
