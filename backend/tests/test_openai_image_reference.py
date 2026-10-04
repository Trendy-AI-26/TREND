from types import SimpleNamespace

import pytest

from app.services.providers.base import ReferenceImage
from app.services.providers import openai_image


class FakeResponse:
    status_code = 200
    headers = {
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
