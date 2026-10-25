import os

import pytest
from fastapi.testclient import TestClient

# Set required env vars before importing the app. Plain assignment (not
# setdefault) so a developer's shell or .env cannot change test behaviour.
TEST_ENV = {
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+psycopg://test:test@127.0.0.1:5432/test",
    "RUN_MIGRATIONS_ON_STARTUP": "false",
    "AUTH_JWT_SECRET": "test-jwt-secret-with-at-least-32-bytes-of-length",
    "AUTH_SESSION_TTL_SECONDS": "604800",
    "AUTH_COOKIE_SECURE": "false",
    "APP_ENCRYPTION_KEY": "n7Kzm1oSSOZEE5XDR6wPDfIm4CBrrq6xOS_4_T7C70Y=",
    "S3_ENDPOINT_URL": "http://127.0.0.1:9000",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "test-access-key",
    "S3_SECRET_ACCESS_KEY": "test-secret-key",
    "S3_PUBLIC_BASE_URL": "https://s3.example.test",
    "SMTP_HOST": "",
    "ADMIN_EMAILS": "",
}
os.environ.update(TEST_ENV)

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def store(monkeypatch):
    """In-memory generations / locks / idempotency tables (see generation_fakes)."""
    from tests import generation_fakes

    fake = generation_fakes.FakeStore()
    generation_fakes.install(monkeypatch, fake)
    return fake


@pytest.fixture
def endpoint(store, monkeypatch):
    """A TestClient for POST /brands/{id}/generate with every external seam faked.

    Yields ``(client, provider, store)``; ``provider`` is the AsyncMock that
    replaces the OpenAI call, so tests can count dispatches.
    """
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.core.auth import User, get_current_user
    from app.routers import generations
    from app.services.credits import CreditReservation
    from app.services.providers.base import ProviderResult

    provider = AsyncMock(
        return_value=ProviderResult(image_bytes=b"fake", request_id="test")
    )
    monkeypatch.setattr(generations, "openai_generate", provider)
    monkeypatch.setattr(
        generations, "_get_brand_or_404", lambda **_: {"name": "Test", "logo_path": None}
    )
    monkeypatch.setattr(generations, "_get_brand_kit_context", lambda **_: None)
    monkeypatch.setattr(
        generations,
        "resolve_generation_config",
        lambda: SimpleNamespace(provider="openai", model="test-model", api_key="fake"),
    )
    monkeypatch.setattr(generations, "enforce_generation_rate_limit", lambda **_: None)
    monkeypatch.setattr(generations, "resize_to_preset", lambda content, *_: content)
    for name in (
        "reserve_generation_slot",
        "commit_generation_slot",
        "release_generation_slot",
    ):
        monkeypatch.setattr(generations, name, lambda **_: None)
    monkeypatch.setattr(
        generations,
        "reserve_credits",
        lambda **kwargs: CreditReservation(
            reservation_id="test-receipt",
            user_id=kwargs["user_id"],
            generation_id=str(kwargs["generation_id"]),
            amount=1,
        ),
    )
    monkeypatch.setattr(generations, "commit_credits", lambda _: None)
    monkeypatch.setattr(generations, "release_credits", lambda _: None)
    monkeypatch.setattr(
        generations,
        "UsageTimer",
        lambda **_: SimpleNamespace(
            usage_id="test", start=lambda: None, finish=lambda **_: None
        ),
    )
    app.dependency_overrides[get_current_user] = lambda: User(
        id="user-123", email="test@example.invalid", access_token="fake"
    )
    try:
        yield TestClient(app), provider, store
    finally:
        app.dependency_overrides.pop(get_current_user, None)
