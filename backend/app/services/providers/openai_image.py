import base64
import logging

import httpx

from app.services.providers.base import (
    ProviderError,
    ProviderResult,
    ReferenceImage,
 )
from app.services.error_mapping import ERROR_USER_MESSAGES

logger = logging.getLogger(__name__)

OPENAI_IMAGES_GENERATIONS_URL = (
    "https://api.openai.com/v1/images/generations"
 )

OPENAI_IMAGES_EDITS_URL = (
    "https://api.openai.com/v1/images/edits"
 )


def _openai_size(width: int, height: int) -> str:
    if width == height:
        return "1024x1024"

    return "1536x1024" if width > height else "1024x1536"


def _decode_provider_image(data: dict) -> bytes:
    try:
        encoded = data["data"][0]["b64_json"]
        return base64.b64decode(encoded)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError(
            "EMPTY_RESPONSE",
            "The provider returned no image.",
        ) from exc


async def openai_generate(
    *,
    api_key: str,
    prompt: str,
    width: int,
    height: int,
    model: str,
    reference_image: ReferenceImage | None = None,
) -> ProviderResult:
    """
    Generate an image.

    - بدون reference_image:
      نستخدم Images Generations API.
    - مع reference_image:
      نستخدم Images Edits API ونرسل الصورة كـ multipart file.
    """
    size = _openai_size(width, height)

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    timeout = httpx.Timeout(120.0 )

    async with httpx.AsyncClient(timeout=timeout ) as client:
        if reference_image is None:
            response = await client.post(
                OPENAI_IMAGES_GENERATIONS_URL,
                headers=headers,
                json={
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "n": 1,
                },
            )
        else:
            filename = _filename_for_mime(
                reference_image.mime_type
            )

            response = await client.post(
                OPENAI_IMAGES_EDITS_URL,
                headers=headers,
                data={
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "n": "1",
                },
                files={
                    "image": (
                        filename,
                        reference_image.content,
                        reference_image.mime_type,
                    )
                },
            )

        if response.status_code >= 400:
            logger.error(
                "openai image request failed "
                "status=%s request_id=%s body=%s",
                response.status_code,
                response.headers.get("x-request-id"),
                response.text[:1000],
            )

            raise ProviderError(
                "PROVIDER_REQUEST_FAILED",
                "The image provider could not generate the image.",
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "The image provider returned an invalid response.",
            ) from exc

    return ProviderResult(
        image_bytes=_decode_provider_image(data),
        request_id=response.headers.get("x-request-id"),
    )


def _filename_for_mime(mime_type: str) -> str:
    """
    OpenAI يحتاج اسم ملف مناسبًا مع Multipart.
    """
    if mime_type == "image/png":
        return "product-reference.png"

    if mime_type == "image/webp":
        return "product-reference.webp"

    return "product-reference.jpg"

def _provider_error_from_response(
    response: httpx.Response,
 ) -> ProviderError:
    body = response.text.lower()

    if response.status_code == 401:
        return ProviderError(
            "INVALID_KEY",
            "The provider key was rejected.",
        )

    if response.status_code == 429:
        return ProviderError(
            "RATE_LIMITED",
            "The provider is rate limiting requests.",
        )

    if (
        "image edit" in body
        or "images/edits" in body
        or "unsupported" in body
        or "not supported" in body
    ):
        return ProviderError(
            "REFERENCE_IMAGE_UNSUPPORTED",
            (
                "Product image editing is not available "
                "for the current provider configuration."
            ),
        )

    if response.status_code in (400, 422):
        return ProviderError(
            "PROVIDER_CLIENT_ERROR",
            "The provider rejected the image edit request.",
        )

    if response.status_code >= 500:
        return ProviderError(
            "PROVIDER_SERVER_ERROR",
            "The image provider is temporarily unavailable.",
        )

    return ProviderError(
    "REFERENCE_IMAGE_UNSUPPORTED",
    ERROR_USER_MESSAGES[
        "REFERENCE_IMAGE_UNSUPPORTED"
    ],
)

