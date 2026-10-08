"""The client must not be able to influence provider, model, or API key.

These tests are the regression guard for the server-only generation config.
They assert the contract at the model level (cheap, exact) and at the HTTP
level (proves the rejection actually reaches the caller as a 400/422).
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import settings
from app.main import app
from app.core.auth import User, get_current_user
from app.models.generation import GenerateRequest, GenerationBrief
from app.services.generation_resolver import resolve_generation_config


BRIEF = {
    "campaign_goal": "product_launch",
    "content_type": "product_showcase",
    "target_audience": {
        "segments": ["small_business_owners"],
        "location": "Amman",
        "age_range": "25_34",
        "gender_focus": "all",
        "details": "test",
    },
    "core_idea": "Launch a new cold brew",
    "voice_tone": "friendly",
}


@pytest.fixture
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: User(
        id="user-123", email="user@example.com", access_token="mock-token"
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _base_payload(**extra):
    return {
        "brief": BRIEF,
        "platform_preset": "instagram_post",
        "logo_mode": "none",
        **extra,
    }


# --------------------------------------------------------------------------
# Model level: injection is rejected loudly
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "injected",
    [
        {"provider": "gemini"},
        {"provider": "openai"},
        {"model": "dall-e-3"},
        {"model": "gpt-image-1"},
        {"api_key": "sk-attacker-key"},
        {"vault_secret_id": "00000000-0000-0000-0000-000000000000"},
        {"GENERATION_API_KEY": "sk-env-leak"},
        {"GENERATION_MODEL": "dall-e-3"},
    ],
)
def test_generate_request_rejects_injected_credentials(injected):
    with pytest.raises(ValidationError) as exc:
        GenerateRequest.model_validate(_base_payload(**injected))

    assert "extra_forbidden" in str(exc.value)


def test_clean_payload_has_no_credential_attributes():
    request = GenerateRequest.model_validate(_base_payload())

    assert not hasattr(request, "provider")
    assert not hasattr(request, "model")
    assert not hasattr(request, "api_key")


def test_legitimate_client_choices_still_accepted():
    from uuid import uuid4

    asset_id = uuid4()
    request = GenerateRequest.model_validate(_base_payload(product_asset_id=str(asset_id)))

    assert str(request.product_asset_id) == str(asset_id)
    assert request.logo_mode.value == "none"


def test_resolver_is_the_only_credential_source(monkeypatch):
    """Even with injected-looking input, the resolver returns env values."""
    monkeypatch.setattr(settings, "MANAGED_PROVIDER", "openai")
    monkeypatch.setattr(settings, "MANAGED_MODEL", "gpt-image-2")
    monkeypatch.setattr(settings, "MANAGED_API_KEY", "server-secret-key")

    request = GenerateRequest.model_validate(_base_payload())
    resolved = resolve_generation_config()

    assert resolved.provider == "openai"
    assert resolved.model == "gpt-image-2"
    assert resolved.api_key == "server-secret-key"
    assert not hasattr(request, "api_key")


# --------------------------------------------------------------------------
# HTTP level: the rejection reaches the caller
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "injected",
    [
        {"provider": "gemini"},
        {"model": "dall-e-3"},
        {"api_key": "sk-attacker-key"},
    ],
)
def test_generate_endpoint_returns_400_for_injected_credentials(override_auth, injected):
    client = TestClient(app)
    brand_id = "11111111-1111-1111-1111-111111111111"

    response = client.post(
        f"/brands/{brand_id}/generate",
        json=_base_payload(**injected),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_openapi_contract_exposes_no_credential_fields():
    """Swagger must not advertise provider/model/api_key as body fields."""
    spec = app.openapi()
    schema = spec["paths"]["/brands/{brand_id}/generate"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    model_name = schema["$ref"].split("/")[-1]
    model = spec["components"]["schemas"][model_name]

    assert sorted(model["properties"]) == [
        "brief",
        "logo_mode",
        "logo_placement",
        "platform_preset",
        "product_asset_id",
        "product_edit_instruction",
]

    assert model["additionalProperties"] is False
