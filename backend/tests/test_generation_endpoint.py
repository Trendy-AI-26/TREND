from app.services.providers.base import ReferenceImage
import pytest
from collections import defaultdict
from uuid import uuid4
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import User, get_current_user
from app.routers import generations
from app.models.generation import (
    GenerateRequest,
    ProviderEnum,
)

from pydantic import ValidationError

# Sample valid brief for the payload
VALID_BRIEF = {
    "campaign_goal": "product_launch",
    "content_type": "product_showcase",
    "target_audience": {
        "segments": ["small_business_owners"],
        "location": "Amman",
        "age_range": "25_34",
        "gender_focus": "all",
        "details": "أصحاب مشاريع صغيرة.",
    },
    "core_idea": "إطلاق قهوة باردة لصباح صيفي مزدحم.",
    "voice_tone": "friendly",
    "optional_notes": "اترك مساحة في الأعلى.",
    "text_to_include": "خصم 20%",
}


def _client():
    # The backend requires an Idempotency-Key on every generate request.
    return TestClient(app, headers={"Idempotency-Key": str(uuid4())})


class FakeBackend:
    """Stands in for the generation repository and the object storage helpers."""

    def __init__(self):
        self.inserted_rows = defaultdict(list)
        self.uploaded_files = {}
        self.finished_idempotency = []
        self.checkpoints = []
        self.failed = []
        self.last_row = None

    # --- repository (app.repositories.generations) -------------------------
    def get_idempotency(self, user_id, scope, idempotency_key):
        return None

    def create_idempotency(
        self, user_id, scope, idempotency_key, request_hash, generation_id=None
    ):
        # The record references the generation, so the row must exist first.
        assert generation_id is None or self.inserted_rows["generations"]
        self.inserted_rows["idempotency_records"].append(
            {
                "user_id": user_id,
                "idempotency_key": idempotency_key,
                "generation_id": None if generation_id is None else str(generation_id),
            }
        )
        return {
            "id": "idem-1",
            "user_id": user_id,
            "generation_id": None if generation_id is None else str(generation_id),
            "request_hash": request_hash,
        }

    def link_idempotency(self, record_id, generation_id):
        self.inserted_rows["idempotency_links"].append((record_id, str(generation_id)))

    def save_checkpoint(self, record_id, checkpoint):
        self.checkpoints.append(checkpoint)
        return True

    def finish_idempotency(self, record_id, status, response_status, completed_at=None):
        self.finished_idempotency.append((status, response_status))
        return True

    def delete_idempotency_for_generation(self, generation_id):
        return None

    def fail_idempotency_for_generation(self, generation_id, response_status):
        return None

    def delete_owned_generation(self, user_id, generation_id):
        return None

    def insert_generation(self, values):
        from datetime import datetime, timezone

        row = {**values, "status": "pending"}
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        self.inserted_rows["generations"].append(values)
        self.last_row = row
        return row

    def mark_processing(self, generation_id):
        if self.last_row:
            self.last_row["status"] = "processing"

    def mark_succeeded(self, generation_id, image_path, provider_request_id, completed_at):
        row = {
            **(self.last_row or {}),
            "id": str(generation_id),
            "status": "succeeded",
            "image_path": image_path,
            "provider_request_id": provider_request_id,
            "completed_at": completed_at,
        }
        self.last_row = row
        return row

    def mark_failed(self, generation_id, code, message, completed_at):
        self.failed.append((str(generation_id), code))

    def get_generation(self, generation_id):
        return self.last_row

    # --- storage (app.core.storage) ----------------------------------------
    def upload(self, bucket, path, data, content_type="application/octet-stream", *, upsert=True):
        self.uploaded_files[(bucket, path)] = data

    def download(self, bucket, path):
        return b"fake-logo-bytes"


@pytest.fixture
def mock_backend(monkeypatch):
    backend = FakeBackend()
    for name in (
        "get_idempotency",
        "create_idempotency",
        "link_idempotency",
        "save_checkpoint",
        "finish_idempotency",
        "delete_idempotency_for_generation",
        "fail_idempotency_for_generation",
        "delete_owned_generation",
        "insert_generation",
        "mark_processing",
        "mark_succeeded",
        "mark_failed",
        "get_generation",
    ):
        monkeypatch.setattr(generations.gen_repo, name, getattr(backend, name))
    monkeypatch.setattr(generations.storage, "upload", backend.upload)
    monkeypatch.setattr(generations.storage, "download", backend.download)
    monkeypatch.setattr(
        generations,
        "enforce_generation_rate_limit",
        lambda **_: None,
    )
    monkeypatch.setattr(
        generations,
        "reserve_generation_slot",
        lambda **_: None,
    )
    monkeypatch.setattr(
        generations,
        "commit_generation_slot",
        lambda **_: None,
    )
    monkeypatch.setattr(
        generations,
        "release_generation_slot",
        lambda **_: None,
    )
    return backend


@pytest.fixture
def no_generation_guards(monkeypatch):
    """Neutralise only the generation lock.

    Credits/usage are covered by the dedicated `mock_credits_and_usage`
    fixture, which builds a real Reservation object the router expects.
    """

    # The lock helpers are imported straight into the router module namespace,
    # so patching the service module attribute is what actually takes effect.
    from app.services import generation_lock

    monkeypatch.setattr(generation_lock, "acquire_generation_lock", lambda **_: None)
    monkeypatch.setattr(generation_lock, "release_generation_lock", lambda **_: None)
    monkeypatch.setattr(
        generations, "acquire_generation_lock", lambda **_: None, raising=False
    )
    monkeypatch.setattr(
        generations, "release_generation_lock", lambda **_: None, raising=False
    )
    monkeypatch.setattr(
        generations, "enforce_generation_rate_limit", lambda **_: None, raising=False
    )
    monkeypatch.setattr(
        generations, "get_available_credits", lambda *_: 999, raising=False
    )


@pytest.fixture
def override_auth():
    # Override authentication dependency to bypass actual JWT validation
    app.dependency_overrides[get_current_user] = lambda: User(
        id="user-123", email="user@example.com", access_token="mock-token"
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_helpers(monkeypatch):
    # Mock database helper calls
    monkeypatch.setattr(
        generations,
        "_get_brand_or_404",
        lambda brand_id, user_id: {
            "id": str(brand_id),
            "name": "Acme Brand",
            "logo_path": "brands/logo.png",
        },
    )
    monkeypatch.setattr(
        generations, "_get_brand_kit_context", lambda brand_id, brand_name: None
    )
    # Credentials come from server config, never from the request body.
    from app.services.generation_resolver import ManagedGenerationConfig

    monkeypatch.setattr(
        generations,
        "resolve_generation_config",
        lambda: ManagedGenerationConfig(
            provider="openai", model="gpt-image-2", api_key="fake-server-key"
        ),
    )


@pytest.mark.asyncio
async def test_generate_endpoint_success_openai(
    no_generation_guards,
    mock_credits_and_usage,
    override_auth,
    mock_backend,
    mock_helpers,
    monkeypatch,
):
    from app.services.providers.base import ProviderResult

    mock_result = ProviderResult(
        image_bytes=b"fake-image-bytes",
        request_id="req-123",
    )

    provider_mock = AsyncMock(return_value=mock_result)

    monkeypatch.setattr(
        generations,
        "openai_generate",
        provider_mock,
    )

    monkeypatch.setattr(
        generations,
        "resize_to_preset",
        lambda image_bytes, preset_w, preset_h: image_bytes,
    )

    client = _client()
    brand_id = uuid4()

    payload = {
        "brief": VALID_BRIEF,
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }

    response = client.post(
        f"/brands/{brand_id}/generate",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert provider_mock.await_count == 1


@pytest.mark.asyncio
async def test_generate_endpoint_validation_error(override_auth, mock_helpers):
    client = _client()
    brand_id = uuid4()

    # Payload is missing required field 'brief'
    payload = {
        "platform_preset": "instagram_post",
    }

    response = client.post(f"/brands/{brand_id}/generate", json=payload)
    assert response.status_code == 400
    res_data = response.json()
    assert res_data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_generate_endpoint_logo_required_check(
    no_generation_guards, override_auth, mock_backend, monkeypatch
):
    # Mock brand has no logo
    monkeypatch.setattr(
        generations,
        "_get_brand_or_404",
        lambda brand_id, user_id: {
            "id": str(brand_id),
            "name": "No Logo Brand",
            "logo_path": None,
        },
    )

    client = _client()
    brand_id = uuid4()

    # Requesting a watermark logo mode when brand has no logo
    payload = {
        "brief": VALID_BRIEF,
        "platform_preset": "instagram_post",
        "logo_mode": "watermark",
    }

    response = client.post(f"/brands/{brand_id}/generate", json=payload)
    assert response.status_code == 400
    res_data = response.json()
    assert res_data["error"]["code"] == "LOGO_REQUIRED"


@pytest.mark.asyncio
async def test_generate_endpoint_accepts_language_param(
    no_generation_guards,
    mock_credits_and_usage,
    override_auth,
    mock_backend,
    mock_helpers,
    monkeypatch,
):
    """Test that the endpoint accepts the language parameter and sends a 200 response on success."""
    from app.services.providers.base import ProviderResult

    mock_result = ProviderResult(image_bytes=b"fake-image-bytes", request_id="req-123")
    provider_mock = AsyncMock(return_value=mock_result)
    monkeypatch.setattr(generations, "openai_generate", provider_mock)
    monkeypatch.setattr(generations, "resize_to_preset", lambda img, w, h: img)

    client = _client()
    brand_id = uuid4()

    # نمرر brief يحتوي على language="en"
    payload_with_lang = {
        "brief": {**VALID_BRIEF, "language": "en"},
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }

    response = client.post(f"/brands/{brand_id}/generate", json=payload_with_lang)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "succeeded"
    sent_prompt = provider_mock.call_args.kwargs["prompt"]
    assert "Write newly generated campaign copy in English." in sent_prompt
    assert "إطلاق قهوة باردة لصباح صيفي مزدحم." in sent_prompt
    assert "خصم 20%" in sent_prompt


@pytest.mark.asyncio
async def test_generate_endpoint_rejects_invalid_language(override_auth, mock_helpers):
    """When the brief contains an invalid language, the endpoint should return a 400 validation error."""
    client = _client()
    brand_id = uuid4()

    payload_bad_lang = {
        "brief": {**VALID_BRIEF, "language": "invalid_lang"},
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }

    response = client.post(f"/brands/{brand_id}/generate", json=payload_bad_lang)
    assert response.status_code == 400
    res_data = response.json()
    assert res_data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_generate_endpoint_persists_language(
    no_generation_guards,
    mock_credits_and_usage,
    override_auth,
    mock_backend,
    mock_helpers,
    monkeypatch,
):
    from app.services.providers.base import ProviderResult

    mock_result = ProviderResult(
        image_bytes=b"fake-image-bytes",
        request_id="req-123",
    )

    provider_mock = AsyncMock(return_value=mock_result)
    monkeypatch.setattr(generations, "openai_generate", provider_mock)
    # The provider stub returns non-image bytes; skip real Pillow decoding.
    monkeypatch.setattr(generations, "resize_to_preset", lambda b, w, h: b)

    client = _client()
    brand_id = uuid4()

    payload = {
        "brief": {
            **VALID_BRIEF,
            "language": "en",
        },
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }

    response = client.post(
        f"/brands/{brand_id}/generate",
        json=payload,
    )

    # The endpoint must succeed and persist the language. It previously
    # asserted 500 because client errors were being relabelled as faults.
    assert response.status_code == 200

    inserted = mock_backend.inserted_rows["generations"][0]

    assert inserted["language"] == "en"
    # The idempotency record references the generation, so it is created
    # already linked to the row that exists by then, and it is closed as
    # succeeded after the output checkpoint was saved.
    record = mock_backend.inserted_rows["idempotency_records"][0]
    assert record["generation_id"] == inserted["id"]
    assert mock_backend.checkpoints[0]["phase"] == "output_ready"
    assert mock_backend.finished_idempotency == [("succeeded", 200)]
    assert (
        "brand-assets",
        f"brands/{inserted['brand_id']}/generations/{inserted['id']}.png",
    ) in mock_backend.uploaded_files


def test_generate_request_accepts_three_audience_segments():
    payload = {
        "brief": {
            "campaign_goal": "product_launch",
            "content_type": "product_showcase",
            "target_audience": {
                "segments": [
                    "small_business_owners",
                    "marketers_creators",
                    "online_shoppers",
                ],
                "location": "Amman",
                "age_range": "25_34",
                "gender_focus": "all",
                "details": "أصحاب مشاريع صغيرة",
            },
            "core_idea": "إطلاق منتج جديد",
            "voice_tone": "friendly",
        },
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }

    request = GenerateRequest.model_validate(payload)

    assert len(request.brief.target_audience.segments) == 3


def test_generate_request_rejects_four_audience_segments():
    payload = {
        "brief": {
            "campaign_goal": "product_launch",
            "content_type": "product_showcase",
            "target_audience": {
                "segments": [
                    "small_business_owners",
                    "marketers_creators",
                    "online_shoppers",
                    "professionals",
                ],
                "location": "Amman",
                "age_range": "25_34",
                "gender_focus": "all",
                "details": "أصحاب مشاريع صغيرة",
            },
            "core_idea": "إطلاق منتج جديد",
            "voice_tone": "friendly",
        },
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }

    with pytest.raises(ValidationError):
        GenerateRequest.model_validate(payload)


def test_history_filter_constants_match_supported_enums():
    assert generations._VALID_HISTORY_STATUSES == {
        status.value for status in generations.GenerationHistoryStatusEnum
    }
    assert generations._VALID_HISTORY_PROVIDERS == {
        provider.value for provider in ProviderEnum
    }


@pytest.mark.asyncio
async def test_generate_passes_product_reference_to_provider(
    no_generation_guards,
    mock_credits_and_usage,
    override_auth,
    mock_backend,
    mock_helpers,
    monkeypatch,
):
    from app.services.providers.base import ProviderResult

    provider_mock = AsyncMock(
        return_value=ProviderResult(
            image_bytes=b"fake-image-bytes",
            request_id="req-product-reference",
        )
    )

    monkeypatch.setattr(
        generations,
        "openai_generate",
        provider_mock,
    )

    monkeypatch.setattr(
        generations,
        "resize_to_preset",
        lambda image, width, height: image,
    )

    product_asset_id = uuid4()

    fake_reference_image = ReferenceImage(
        content=b"fake-product-image",
        mime_type="image/png",
    )

    monkeypatch.setattr(
        generations,
        "load_product_asset_reference",
        lambda **kwargs: fake_reference_image,
    )

    payload = {
        "brief": {
            **VALID_BRIEF,
            "language": "en",
        },
        "platform_preset": "instagram_post",
        "logo_mode": "none",
        "product_asset_id": str(product_asset_id),
        "product_edit_instruction": ("Place the product on a white background."),
    }

    client = _client()
    brand_id = uuid4()

    response = client.post(
        f"/brands/{brand_id}/generate",
        json=payload,
    )

    assert response.status_code == 200

    provider_mock.assert_awaited_once()

    call_kwargs = provider_mock.call_args.kwargs

    assert call_kwargs["reference_image"] is fake_reference_image
    assert "Place the product on a white background." in call_kwargs["prompt"]


@pytest.fixture
def mock_credits_and_usage(monkeypatch):
    reservation = type(
        "Reservation",
        (),
        {
            "amount": 1,
            "reservation_id": "test-receipt",
            "user_id": "user-123",
            "generation_id": "generation-123",
        },
    )()

    monkeypatch.setattr(
        generations,
        "reserve_credits",
        lambda **kwargs: reservation,
    )

    monkeypatch.setattr(
        generations,
        "commit_credits",
        lambda reservation: None,
    )

    monkeypatch.setattr(
        generations,
        "release_credits",
        lambda reservation: None,
    )

    class FakeUsageTimer:
        def __init__(self, **kwargs):
            self.statuses = []

        def start(self):
            return None

        def finish(self, **kwargs):
            self.statuses.append(kwargs)

    monkeypatch.setattr(
        generations,
        "UsageTimer",
        FakeUsageTimer,
    )

    return reservation


def test_generation_returns_402_when_credits_are_missing(
    mock_credits_and_usage,
    override_auth,
    mock_backend,
    mock_helpers,
    monkeypatch,
):
    from app.services.credits import CreditsError

    # The lock is acquired before credits are reserved; stub it so the test
    # exercises the credit path instead of hitting the real database.
    monkeypatch.setattr(
        generations, "acquire_generation_lock", lambda **_: None, raising=False
    )
    monkeypatch.setattr(
        generations, "release_generation_lock", lambda **_: None, raising=False
    )

    def reject_reservation(**kwargs):
        raise CreditsError(
            "INSUFFICIENT_CREDITS",
            "You do not have enough credits.",
        )

    monkeypatch.setattr(
        generations,
        "reserve_credits",
        reject_reservation,
    )

    client = _client()
    brand_id = uuid4()

    payload = {
        "brief": VALID_BRIEF,
        "platform_preset": "instagram_post",
        "logo_mode": "none",
    }

    response = client.post(
        f"/brands/{brand_id}/generate",
        json=payload,
    )

    assert response.status_code == 402

    body = response.json()

    # The app-level HTTPException handler flattens the envelope to "error".
    assert body["error"]["code"] == "INSUFFICIENT_CREDITS"


@pytest.mark.asyncio
async def test_provider_failure_releases_credits(
    no_generation_guards,
    override_auth,
    mock_backend,
    mock_helpers,
    monkeypatch,
):
    from app.services.providers.base import ProviderError

    from app.services.credits import CreditReservation

    reservation = CreditReservation("test-receipt", "user-123", "unused", 1)
    release_calls = []
    quota_release_calls = []

    monkeypatch.setattr(
        generations,
        "reserve_credits",
        lambda **kwargs: reservation,
    )

    monkeypatch.setattr(
        generations,
        "release_credits",
        lambda reservation: release_calls.append(reservation),
    )
    monkeypatch.setattr(
        generations,
        "release_generation_slot",
        lambda **kwargs: quota_release_calls.append(kwargs),
    )

    class FakeUsageTimer:
        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

        def finish(self, **kwargs):
            pass

    monkeypatch.setattr(
        generations,
        "UsageTimer",
        FakeUsageTimer,
    )

    async def failing_provider(**kwargs):
        # A definite provider rejection is refundable; ambiguous codes are not.
        raise ProviderError(
            "INVALID_KEY",
            "Provider failed.",
        )

    monkeypatch.setattr(
        generations,
        "openai_generate",
        failing_provider,
    )

    client = _client()
    brand_id = uuid4()

    response = client.post(
        f"/brands/{brand_id}/generate",
        json={
            "brief": VALID_BRIEF,
            "platform_preset": "instagram_post",
            "logo_mode": "none",
        },
    )

    assert response.status_code == 502
    assert len(release_calls) == 1
    assert release_calls[0].reservation_id == reservation.reservation_id
    assert len(quota_release_calls) == 1


def test_same_idempotency_key_is_not_processed_twice(
    monkeypatch,
):
    first = {
        "id": "generation-1",
        "request_hash": "hash-1",
        "generation_id": "generation-1",
        "status": "succeeded",
    }

    monkeypatch.setattr(
        generations,
        "_get_existing_idempotency",
        lambda **kwargs: first,
    )

    result = generations._get_existing_idempotency(
        user_id="user-1",
        scope="image_generation",
        idempotency_key="same-key-123456",
        request_hash="hash-1",
    )

    assert result["generation_id"] == "generation-1"


def test_second_generation_is_rejected_when_lock_exists(
    mock_credits_and_usage,
    override_auth,
    mock_backend,
    mock_helpers,
    monkeypatch,
):
    """While a generation lock is held, a second attempt gets 409."""
    from app.services.generation_lock import GenerationLockError

    def locked(**_kwargs):
        raise GenerationLockError("A generation is already in progress.")

    monkeypatch.setattr(generations, "acquire_generation_lock", locked)
    monkeypatch.setattr(generations, "release_generation_lock", lambda **_: None)

    client = _client()

    response = client.post(
        f"/brands/{uuid4()}/generate",
        json={
            "brief": VALID_BRIEF,
            "platform_preset": "instagram_post",
            "logo_mode": "none",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GENERATION_IN_PROGRESS"
