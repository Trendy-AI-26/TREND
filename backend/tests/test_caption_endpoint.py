from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.auth import User
from app.models.caption import CaptionRequest, CaptionResponse
from app.routers import generations
from app.services.caption_generator import CaptionOutputError
from app.services.caption_generator import generate_caption as real_generate_caption
from app.services.generation_resolver import ManagedGenerationConfig

USER = User(id="user-123", email="user@example.com", access_token="test-token")

SERVER_KEY = "server-secret-key"


def use_server_config(monkeypatch):
    """Caption generation reads credentials from server config, not the vault."""
    monkeypatch.setattr(
        generations,
        "resolve_caption_config",
        lambda: ManagedGenerationConfig(
            provider="openai", model="gpt-4o-mini", api_key=SERVER_KEY
        ),
    )


def valid_row(*, brand_id: str, status: str = "succeeded") -> dict:
    return {
        "id": str(uuid4()),
        "brand_id": brand_id,
        "status": status,
        "language": "ar",
        "platform_preset": "instagram_post",
        "provider": "openai",
        "prompt": "إطلاق عطر صيفي جديد.",
        "image_path": f"brands/{brand_id}/image.png",
    }


def valid_result() -> CaptionResponse:
    return CaptionResponse.model_validate(
        {
            "caption": "اكتشف عطرك الصيفي الجديد.",
            "hook": "رائحة تترك أثرًا",
            "hashtags": ["#عطور"],
            "keywords": ["عطر صيفي"],
            "trend_used": False,
            "language": "ar",
        }
    )


@pytest.mark.asyncio
async def test_caption_endpoint_calls_generator_with_supported_arguments(monkeypatch):
    brand_id = uuid4()
    generation_id = uuid4()
    row = valid_row(brand_id=str(brand_id))

    monkeypatch.setattr(generations, "_get_brand_or_404", lambda *_: {"name": "Acme"})
    monkeypatch.setattr(generations, "_find_generation_or_404", lambda *_: row)
    use_server_config(monkeypatch)
    monkeypatch.setattr(generations, "_get_brand_kit_context", lambda *_: None)
    caption_mock = create_autospec(real_generate_caption, return_value=valid_result())
    monkeypatch.setattr(generations, "generate_caption", caption_mock)

    result = await generations.create_caption(
        brand_id=brand_id,
        generation_id=generation_id,
        body=None,
        current_user=USER,
    )

    assert result == valid_result()
    caption_mock.assert_awaited_once()
    assert set(caption_mock.await_args.kwargs) == {
        "provider",
        "api_key",
        "language",
        "platform",
        "generation_prompt",
        "brief",
        "brand_context",
        "preferences",
    }


@pytest.mark.asyncio
async def test_caption_endpoint_inherits_generation_context_and_allows_empty_body(monkeypatch):
    brand_id = uuid4()
    generation_id = uuid4()
    row = valid_row(brand_id=str(brand_id))
    calls = []

    monkeypatch.setattr(generations, "_get_brand_or_404", lambda *_: {"name": "Acme"})
    monkeypatch.setattr(generations, "_find_generation_or_404", lambda *_: row)
    use_server_config(monkeypatch)
    monkeypatch.setattr(generations, "_get_brand_kit_context", lambda *_: None)

    async def fake_generate_caption(**kwargs):
        calls.append(kwargs)
        return valid_result()

    monkeypatch.setattr(generations, "generate_caption", fake_generate_caption)

    result = await generations.create_caption(
        brand_id=brand_id,
        generation_id=generation_id,
        body=None,
        current_user=USER,
    )

    assert result.language.value == "ar"
    assert result.trend_used is False
    assert calls[0]["language"].value == "ar"
    assert calls[0]["platform"].value == "instagram_post"
    assert calls[0]["generation_prompt"] == row["prompt"]
    assert calls[0]["brief"] is None
    assert calls[0]["api_key"] == SERVER_KEY


@pytest.mark.asyncio
async def test_caption_endpoint_rejects_non_successful_generation(monkeypatch):
    brand_id = uuid4()
    generation_id = uuid4()
    row = valid_row(brand_id=str(brand_id), status="processing")

    monkeypatch.setattr(generations, "_get_brand_or_404", lambda *_: {"name": "Acme"})
    monkeypatch.setattr(generations, "_find_generation_or_404", lambda *_: row)

    with pytest.raises(HTTPException) as error:
        await generations.create_caption(
            brand_id=brand_id,
            generation_id=generation_id,
            body=CaptionRequest.model_validate({}),
            current_user=USER,
        )

    assert error.value.status_code == 409
    assert error.value.detail["error"]["code"] == "GENERATION_NOT_READY"


@pytest.mark.asyncio
async def test_caption_endpoint_does_not_cross_brand_access(monkeypatch):
    brand_id = uuid4()
    generation_id = uuid4()

    monkeypatch.setattr(generations, "_get_brand_or_404", lambda *_: {"name": "Acme"})

    def reject_cross_brand(*_):
        raise generations._error_response(404, "GENERATION_NOT_FOUND", "Generation not found")

    monkeypatch.setattr(generations, "_find_generation_or_404", reject_cross_brand)

    with pytest.raises(HTTPException) as error:
        await generations.create_caption(
            brand_id=brand_id,
            generation_id=generation_id,
            body=None,
            current_user=USER,
        )

    assert error.value.status_code == 404
    assert error.value.detail["error"]["code"] == "GENERATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_caption_endpoint_can_be_called_more_than_once(monkeypatch):
    brand_id = uuid4()
    generation_id = uuid4()
    row = valid_row(brand_id=str(brand_id))
    count = 0

    monkeypatch.setattr(generations, "_get_brand_or_404", lambda *_: {"name": "Acme"})
    monkeypatch.setattr(generations, "_find_generation_or_404", lambda *_: row)
    use_server_config(monkeypatch)
    monkeypatch.setattr(generations, "_get_brand_kit_context", lambda *_: None)

    async def fake_generate_caption(**_):
        nonlocal count
        count += 1
        return valid_result()

    monkeypatch.setattr(generations, "generate_caption", fake_generate_caption)

    first = await generations.create_caption(brand_id=brand_id, generation_id=generation_id, body=None, current_user=USER)
    second = await generations.create_caption(brand_id=brand_id, generation_id=generation_id, body=None, current_user=USER)

    assert count == 2
    assert first == second
    assert row["id"] == str(row["id"])
    assert row["image_path"].endswith("image.png")


@pytest.mark.asyncio
async def test_caption_timeout_returns_error_without_mutating_generation(monkeypatch):
    brand_id = uuid4()
    generation_id = uuid4()
    row = valid_row(brand_id=str(brand_id))
    original = row.copy()

    monkeypatch.setattr(generations, "_get_brand_or_404", lambda *_: {"name": "Acme"})
    monkeypatch.setattr(generations, "_find_generation_or_404", lambda *_: row)
    use_server_config(monkeypatch)
    monkeypatch.setattr(generations, "_get_brand_kit_context", lambda *_: None)

    async def timeout_caption(**_):
        raise CaptionOutputError("CAPTION_MODEL_TIMEOUT", "Caption generation timed out. The image is still available.")

    monkeypatch.setattr(generations, "generate_caption", timeout_caption)

    with pytest.raises(HTTPException) as error:
        await generations.create_caption(brand_id=brand_id, generation_id=generation_id, body=None, current_user=USER)

    assert error.value.status_code == 504
    assert error.value.detail["error"]["code"] == "CAPTION_MODEL_TIMEOUT"
    assert row == original


@pytest.mark.asyncio
async def test_caption_endpoint_passes_preferences_without_reasking_for_context(monkeypatch):
    brand_id = uuid4()
    generation_id = uuid4()
    row = valid_row(brand_id=str(brand_id))
    captured = {}

    monkeypatch.setattr(generations, "_get_brand_or_404", lambda *_: {"name": "Acme"})
    monkeypatch.setattr(generations, "_find_generation_or_404", lambda *_: row)
    use_server_config(monkeypatch)
    monkeypatch.setattr(generations, "_get_brand_kit_context", lambda *_: None)

    async def fake_generate_caption(**kwargs):
        captured.update(kwargs)
        return valid_result()

    monkeypatch.setattr(generations, "generate_caption", fake_generate_caption)
    body = CaptionRequest.model_validate({"preferences": {"max_hashtags": 2, "include_emojis": True}})

    await generations.create_caption(brand_id=brand_id, generation_id=generation_id, body=body, current_user=USER)

    assert captured["preferences"].max_hashtags == 2
    assert captured["preferences"].include_emojis is True
    assert captured["language"].value == row["language"]
    assert captured["platform"].value == row["platform_preset"]
