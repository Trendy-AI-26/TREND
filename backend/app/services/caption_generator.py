"""Server-side caption generation and structured-output validation."""

import asyncio
import json
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.models.caption import CaptionPreferences, CaptionResponse
from app.models.generation import GenerationBrief, PlatformPresetEnum, TextLanguageEnum
from app.services.error_mapping import classify_provider_error
from app.services.prompt_composer import BrandContext
from app.services.providers.base import ProviderError

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_OPENAI_TEXT_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.5-flash"


class CaptionOutputError(ProviderError):
    """Provider returned output that does not satisfy the caption contract."""


def _language_name(language: TextLanguageEnum) -> str:
    return "Arabic" if language is TextLanguageEnum.ar else "English"


def build_caption_prompt(
    *,
    language: TextLanguageEnum,
    platform: PlatformPresetEnum,
    generation_prompt: str,
    brief: GenerationBrief | None,
    brand_context: BrandContext | None,
    preferences: CaptionPreferences,
) -> str:
    """Build a deterministic prompt from inherited generation context."""
    lines = [
        "You write social-media captions for an already generated campaign image.",
        f"Write the final caption in {_language_name(language)} only.",
        f"Target platform preset: {platform.value}.",
        "Use the image's generation brief and brand identity as the source of truth.",
        "Do not invent prices, claims, products, offers, or facts absent from the context.",
        "Use SEO naturally: choose only relevant keywords and never use keyword stuffing.",
        "Do not use trends or claim that a trend was used; trends are currently disabled.",
        "Return JSON matching the requested structured schema exactly.",
        "The hashtags field must be a separate array; do not put hashtags in keywords.",
        f"Use at most {preferences.max_hashtags} hashtags.",
        f"Include a call to action: {preferences.include_cta}.",
        f"Include emojis: {preferences.include_emojis}.",
        f"Tone override (if provided): {preferences.tone or 'inherit from the brief and brand kit'}.",
        f"Extra user notes: {preferences.extra_notes or 'none'}.",
        "\n=== IMAGE GENERATION PROMPT ===\n" + generation_prompt,
    ]
    if brief is not None:
        lines.extend(
            [
                "\n=== INHERITED QUESTIONNAIRE ===",
                f"Campaign goal: {brief.campaign_goal.value}",
                f"Content type: {brief.content_type.value}",
                f"Core idea: {brief.core_idea}",
                f"Voice tone: {brief.voice_tone.value}",
                f"Audience: {brief.target_audience.model_dump_json()}",
                f"Optional notes: {brief.optional_notes or 'none'}",
                f"Text to include: {brief.text_to_include or 'none'}",
            ]
        )
    if brand_context is not None:
        lines.extend(
            [
                "\n=== BRAND CONTEXT ===",
                f"Brand: {brand_context.name}",
                f"Tagline: {brand_context.tagline or 'none'}",
                f"Tone: {brand_context.tone or 'none'}",
                f"Business field: {brand_context.industry or 'none'}",
                f"Audience: {brand_context.audience or 'none'}",
                f"Colors: {', '.join(brand_context.colors) or 'none'}",
                f"Avoid words: {brand_context.avoid_words or 'none'}",
            ]
        )
    return "\n".join(lines)


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["caption", "hook", "hashtags", "keywords", "trend_used", "language"],
        "properties": {
            "caption": {"type": "string", "minLength": 1, "maxLength": 2200},
            "hook": {"type": ["string", "null"], "maxLength": 120},
            "hashtags": {"type": "array", "maxItems": 8, "items": {"type": "string"}},
            "keywords": {"type": "array", "maxItems": 10, "items": {"type": "string"}},
            "trend_used": {"type": "boolean"},
            "language": {"type": "string", "enum": ["ar", "en"]},
        },
    }


def _parse_json(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CaptionOutputError("CAPTION_INVALID_OUTPUT", "Caption provider returned invalid structured output.") from exc
    if not isinstance(value, dict):
        raise CaptionOutputError("CAPTION_INVALID_OUTPUT", "Caption provider returned invalid structured output.")
    return value


def validate_caption_output(
    payload: dict[str, Any],
    *,
    language: TextLanguageEnum,
    max_hashtags: int,
) -> CaptionResponse:
    """Validate provider output and enforce inherited context rules."""
    try:
        result = CaptionResponse.model_validate(payload)
    except ValidationError as exc:
        raise CaptionOutputError("CAPTION_INVALID_OUTPUT", "Caption provider returned invalid structured output.") from exc
    if result.language is not language:
        raise CaptionOutputError("CAPTION_LANGUAGE_MISMATCH", "Caption provider returned the wrong language.")
    if result.trend_used:
        raise CaptionOutputError("CAPTION_TREND_DISABLED", "Caption output requested a disabled trend.")
    if len(result.hashtags) > max_hashtags:
        raise CaptionOutputError("CAPTION_TOO_MANY_HASHTAGS", "Caption provider returned too many hashtags.")
    return result


async def _openai_caption(*, api_key: str, prompt: str, model: str) -> dict[str, Any]:
    timeout = httpx.Timeout(45.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            OPENAI_CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": "Return only valid JSON matching the supplied schema."},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "caption_response", "strict": True, "schema": _schema()},
                },
            },
        )
        if response.status_code >= 400:
            response.raise_for_status()
        data = response.json()
    try:
        return _parse_json(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise CaptionOutputError("CAPTION_INVALID_OUTPUT", "Caption provider returned no usable output.") from exc


async def _gemini_caption(*, api_key: str, prompt: str, model: str) -> dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0)) as client:
        response = await client.post(
            url,
            headers={"x-goog-api-key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "responseMimeType": "application/json",
                    "responseSchema": _schema(),
                },
            },
        )
        if response.status_code >= 400:
            response.raise_for_status()
        data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise CaptionOutputError("CAPTION_INVALID_OUTPUT", "Caption provider returned no usable output.") from exc
    return _parse_json(text)


async def generate_caption(
    *,
    provider: str,
    api_key: str,
    language: TextLanguageEnum,
    platform: PlatformPresetEnum,
    generation_prompt: str,
    brief: GenerationBrief | None,
    brand_context: BrandContext | None,
    preferences: CaptionPreferences,
) -> CaptionResponse:
    prompt = build_caption_prompt(
        language=language,
        platform=platform,
        generation_prompt=generation_prompt,
        brief=brief,
        brand_context=brand_context,
        preferences=preferences,
    )
    try:
        if provider == "openai":
            payload = await _openai_caption(
                api_key=api_key,
                prompt=prompt,
                model=DEFAULT_OPENAI_TEXT_MODEL,
            )
        elif provider == "gemini":
            payload = await _gemini_caption(
                api_key=api_key,
                prompt=prompt,
                model=DEFAULT_GEMINI_TEXT_MODEL,
            )
        else:
            raise CaptionOutputError("CAPTION_PROVIDER_UNSUPPORTED", "Caption provider is not supported.")
    except CaptionOutputError:
        raise
    except asyncio.TimeoutError as exc:
        raise CaptionOutputError("CAPTION_MODEL_TIMEOUT", "Caption generation timed out. The image is still available.") from exc
    except httpx.TimeoutException as exc:
        raise CaptionOutputError("CAPTION_MODEL_TIMEOUT", "Caption generation timed out. The image is still available.") from exc
    except Exception as exc:
        code, message = classify_provider_error(exc)
        raise CaptionOutputError(f"CAPTION_{code}", message) from exc
    return validate_caption_output(
        payload,
        language=language,
        max_hashtags=preferences.max_hashtags,
    )


__all__ = ["build_caption_prompt", "generate_caption", "validate_caption_output", "CaptionOutputError"]
