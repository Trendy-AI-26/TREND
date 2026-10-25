
from typing import ClassVar

import pytest

from app.services.presets import PLATFORM_PRESETS
from app.services.providers import openai_image
from app.services.providers.base import ReferenceImage

EXPECTED_PROVIDER_SIZES = {
    "instagram_post": "1024x1024",
    "instagram_story": "1024x1536",
    "instagram_reel_cover": "1024x1536",
    "facebook_post": "1536x1024",
    "facebook_cover": "1680x640",
    "facebook_story": "1024x1536",
    "twitter_post": "1536x1024",
    "twitter_header": "1536x512",
    "linkedin_post": "1536x1024",
    "linkedin_banner": "1536x1024",
    "tiktok_video_cover": "1024x1536",
    "youtube_thumbnail": "1536x1024",
    "youtube_banner": "1536x1024",
}


def test_provider_size_cases_cover_all_presets():
    assert set(EXPECTED_PROVIDER_SIZES) == set(PLATFORM_PRESETS)


class FakeResponse:
    status_code = 200
    headers: ClassVar[dict[str, str]] = {
        "x-request-id": "request-123",
    }

    def json(self):
        return {
            "data": [
                {
                    "b64_json": (
                        "aGVsbG8="
                    )
                }
            ]
        }

    def raise_for_status(self):
        return None


class ErrorResponse(FakeResponse):
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.headers = {"x-request-id": "request-error"}

    @property
    def text(self):
        return self.body

    def json(self):
        raise ValueError("not json")


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.last_call = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.last_call = (url, kwargs)
        self.url = url
        self.kwargs = kwargs
        return FakeResponse()


@pytest.mark.parametrize("preset_id", EXPECTED_PROVIDER_SIZES)
@pytest.mark.parametrize("with_reference", [False, True])
@pytest.mark.asyncio
async def test_each_preset_requests_current_provider_size(
    monkeypatch, preset_id, with_reference
):
    fake_client = FakeAsyncClient()
    monkeypatch.setattr(
        openai_image.httpx, "AsyncClient", lambda **kwargs: fake_client
    )
    width, height, _label = PLATFORM_PRESETS[preset_id]
    reference = (
        ReferenceImage(content=b"synthetic-reference", mime_type="image/png")
        if with_reference
        else None
    )

    await openai_image.openai_generate(
        api_key="test-only",
        prompt="Synthetic image test",
        width=width,
        height=height,
        model="gpt-image-2",
        reference_image=reference,
    )

    expected_size = EXPECTED_PROVIDER_SIZES[preset_id]
    assert (width, height) != tuple(map(int, expected_size.split("x")))
    if with_reference:
        assert fake_client.url == openai_image.OPENAI_IMAGES_EDITS_URL
        assert fake_client.kwargs["data"]["size"] == expected_size
    else:
        assert fake_client.url == openai_image.OPENAI_IMAGES_GENERATIONS_URL
        assert fake_client.kwargs["json"]["size"] == expected_size


@pytest.mark.asyncio
async def test_reference_image_uses_edit_endpoint(monkeypatch):
    fake_client = FakeAsyncClient()

    monkeypatch.setattr(
        openai_image.httpx,
        "AsyncClient",
        lambda **kwargs: fake_client,
     )

    result = await openai_image.openai_generate(
        api_key="test-key",
        prompt="Create an advertisement",
        width=1024,
        height=1024,
        model="gpt-image-2",
        reference_image=ReferenceImage(
            content=b"fake-image",
            mime_type="image/png",
        ),
    )

    assert result.image_bytes == b"hello"
    assert result.request_id == "request-123"
    assert (
        fake_client.url
        == openai_image.OPENAI_IMAGES_EDITS_URL
    )

    assert "image" in fake_client.kwargs["files"]
    assert (
        fake_client.kwargs["files"]["image"][2]
        == "image/png"
    )


@pytest.mark.asyncio
async def test_without_reference_image_uses_generation_endpoint(
    monkeypatch,
):
    fake_client = FakeAsyncClient()

    monkeypatch.setattr(
        openai_image.httpx,
        "AsyncClient",
        lambda **kwargs: fake_client,
     )

    await openai_image.openai_generate(
        api_key="test-key",
        prompt="Create an advertisement",
        width=1024,
        height=1024,
        model="gpt-image-2",
        reference_image=None,
    )

    assert (
        fake_client.url
        == openai_image.OPENAI_IMAGES_GENERATIONS_URL
    )

    assert "json" in fake_client.kwargs
    assert "files" not in fake_client.kwargs


@pytest.mark.asyncio
async def test_reference_image_unsupported_error_is_classified(monkeypatch):
    fake_client = FakeAsyncClient()

    async def post(_url, **_kwargs):
        return ErrorResponse(422, "image edits are not supported")

    fake_client.post = post
    monkeypatch.setattr(
        openai_image.httpx,
        "AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(openai_image.ProviderError) as error:
        await openai_image.openai_generate(
            api_key="test-key",
            prompt="Create an advertisement",
            width=1024,
            height=1024,
            model="gpt-image-2",
            reference_image=ReferenceImage(
                content=b"fake-image",
                mime_type="image/png",
            ),
        )

    assert error.value.code == "REFERENCE_IMAGE_UNSUPPORTED"


@pytest.mark.asyncio
async def test_invalid_key_error_is_classified(monkeypatch):
    fake_client = FakeAsyncClient()

    async def post(_url, **_kwargs):
        return ErrorResponse(401, "invalid api key")

    fake_client.post = post
    monkeypatch.setattr(
        openai_image.httpx,
        "AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(openai_image.ProviderError) as error:
        await openai_image.openai_generate(
            api_key="bad-key",
            prompt="Create an advertisement",
            width=1024,
            height=1024,
            model="gpt-image-2",
        )

    assert error.value.code == "INVALID_KEY"
