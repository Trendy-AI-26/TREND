
from app.models.provider_key import ProviderKeyResponse


def test_provider_key_response_does_not_expose_raw_key():
    response = ProviderKeyResponse(
        id="key-1",
        brand_id="brand-1",
        provider="openai",
        label="OpenAI key",
        key_hint=None,
        is_valid=True,
        is_active=True,
        last_validated_at=None,
        created_at="2026-09-24T00:00:00Z",
    )

    data = response.model_dump()

    assert "key" not in data
    assert "api_key" not in data
    assert "secret" not in data
    assert "plaintext_key" not in data
