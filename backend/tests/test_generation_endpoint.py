from urllib import response

from app.services.providers.base import ReferenceImage
import pytest
from collections import defaultdict
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import User, get_current_user
from app.routers import generations
from app.models.generation import (
    GenerateRequest,
    ProviderEnum,
    PlatformPresetEnum,
    LogoModeEnum,
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


# Fake objects for Supabase mocking
class FakeStorageBucket:
    def __init__(self):
        self.uploaded_files = {}

    def upload(self, path, data, options=None):
        self.uploaded_files[path] = data
        return {"path": path}

    def download(self, path):
        return b"fake-logo-bytes"


class FakeStorage:
    def __init__(self):
        self.bucket = FakeStorageBucket()

    def from_(self, bucket_name):
        return self.bucket


class FakeQuery:
    def __init__(self, table_name, client):
        self.table_name = table_name
        self.client = client
        self._eq_filters = {}
        self._delete = False
        self._select = False
        self._single = False

    def select(self, *_):
        self._select = True
        return self

    def maybe_single(self):
        self._single = True
        return self

    def insert(self, data):
        data = data.copy()
        if "created_at" not in data:
            from datetime import datetime, timezone

            data["created_at"] = datetime.now(timezone.utc).isoformat()
        self.client.inserted_rows[self.table_name].append(data)
        self.client.last_row = data
        return self

    def update(self, data):
        self.client.updated_rows[self.table_name].append(data)
        rows = self.client.inserted_rows[self.table_name]
        if rows:
            rows[-1].update(data)
        return self

    def delete(self):
        self._delete = True
        return self

    def eq(self, field, value):
        self._eq_filters[field] = value
        return self

    def execute(self):
        # Return a response containing the mock row
        rows = self.client.inserted_rows[self.table_name]
        if self._select:
            rows = [row for row in rows if all(row.get(k) == v for k, v in self._eq_filters.items())]
            return MagicMock(data=(rows[0] if rows else None) if self._single else rows)
        if self._delete:
            self.client.inserted_rows[self.table_name] = [
                row for row in rows if not all(row.get(k) == v for k, v in self._eq_filters.items())
            ]
            return MagicMock(data=[])
        row = rows[-1] if rows else {}
        # Callers read row["id"] (e.g. the idempotency record) after an insert.
        if "id" not in row:
            row = {**row, "id": f"row-{self.table_name}"}
        return MagicMock(data=[row])


class FakeSupabaseClient:
    def __init__(self):
        # Any table the router touches must be writable: idempotency_records,
        # generation_locks, usage_events, etc. A KeyError here used to surface
        # as a misleading 409 GENERATION_IN_PROGRESS.
        self.inserted_rows = defaultdict(list)
        self.updated_rows = defaultdict(list)
        self.storage = FakeStorage()
        self.last_row = None

    def table(self, table_name):
        return FakeQuery(table_name, self)


@pytest.fixture
def mock_supabase(monkeypatch):
    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(generations, "get_service_client", lambda: fake_client)
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
    return fake_client


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

    # The idempotency guard inserts into idempotency_records; the shared fake
    # client has no such table, and the router turns any failure there into a
    # 409 GENERATION_IN_PROGRESS. Give it a table and a permissive response.
    fake = generations.get_service_client()

    class _IdempotencyQuery:
        def insert(self, _data):
            return self

        def select(self, *_a):
            return self

        def eq(self, *_a):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            return MagicMock(data=[{"id": "idem-1", "request_hash": None}])

    real_table = fake.table

    def _table(name):
        if name == "idempotency_records":
            return _IdempotencyQuery()
        return real_table(name)

    monkeypatch.setattr(fake, "table", _table)


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
    mock_supabase,
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

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    no_generation_guards, override_auth, mock_supabase, monkeypatch
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

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    mock_supabase,
    mock_helpers,
    monkeypatch,
):
    """Test that the endpoint accepts the language parameter and sends a 200 response on success."""
    from app.services.providers.base import ProviderResult

    mock_result = ProviderResult(image_bytes=b"fake-image-bytes", request_id="req-123")
    provider_mock = AsyncMock(return_value=mock_result)
    monkeypatch.setattr(generations, "openai_generate", provider_mock)
    monkeypatch.setattr(generations, "resize_to_preset", lambda img, w, h: img)

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    mock_supabase,
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

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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

    inserted = mock_supabase.inserted_rows["generations"][0]

    assert inserted["language"] == "en"


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
    mock_supabase,
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

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    mock_supabase,
    mock_helpers,
    monkeypatch,
):
    from app.services.credits import CreditsError

    # The lock is acquired before credits are reserved; stub it so the test
    # exercises the credit path instead of hitting the real Supabase RPC.
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

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    mock_supabase,
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
        raise ProviderError(
            "INVALID_KEY",
            "Provider failed.",
        )

    monkeypatch.setattr(
        generations,
        "openai_generate",
        failing_provider,
    )

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})
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
    mock_supabase,
    mock_helpers,
    monkeypatch,
):
    """While a generation lock is held, a second attempt gets 409."""
    from app.services.generation_lock import GenerationLockError

    def locked(**_kwargs):
        raise GenerationLockError("A generation is already in progress.")

    monkeypatch.setattr(generations, "acquire_generation_lock", locked)
    monkeypatch.setattr(generations, "release_generation_lock", lambda **_: None)

    client = TestClient(app, headers={"Idempotency-Key": str(uuid4())})

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
