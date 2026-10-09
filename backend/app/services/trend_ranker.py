import json
from typing import Any

import httpx

from app.config import settings


OPENAI_CHAT_COMPLETIONS_URL = (
    "https://api.openai.com/v1/chat/completions"
 )


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "trend_id": {"type": "string"},
                        "match_score": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "reason": {"type": "string"},
                        "how_to_apply": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "risks": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "trend_id",
                        "match_score",
                        "reason",
                        "how_to_apply",
                        "risks",
                    ],
                    "additionalProperties": False,
                },
            },
            "best_trend_id": {
                "type": ["string", "null"],
            },
        },
        "required": [
            "recommendations",
            "best_trend_id",
        ],
        "additionalProperties": False,
    }


async def rank_trends_with_openai(
    *,
    brief: dict,
    brand_context: dict | None,
    platform_preset: str,
    candidates: list[dict],
) -> dict:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    request_payload = {
        "brief": brief,
        "brand_context": brand_context,
        "platform_preset": platform_preset,
        "candidates": candidates,
    }

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "trend_recommendations",
            "strict": True,
            "schema": _schema(),
        },
    }

    payload = {
        "model": settings.OPENAI_TEXT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You rank only the provided creative trends. "
                    "Never invent a trend ID. "
                    "Return structured JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    request_payload,
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": response_format,
        "temperature": 0,
    }

    headers = {
        "Authorization": (
            f"Bearer {settings.OPENAI_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0 ) as client:
        response = await client.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
        )

    response.raise_for_status()

    body = response.json()
    content = body["choices"][0]["message"]["content"]

    if not content:
        raise RuntimeError(
            "OpenAI returned an empty trend response."
        )

    result = json.loads(content)

    candidate_ids = {
        str(candidate["id"])
        for candidate in candidates
    }

    for recommendation in result.get(
        "recommendations",
        [],
    ):
        if recommendation["trend_id"] not in candidate_ids:
            raise RuntimeError(
                "OpenAI returned an unknown trend_id."
            )

    best_trend_id = result.get("best_trend_id")

    if (
        best_trend_id is not None
        and best_trend_id not in candidate_ids
    ):
        raise RuntimeError(
            "OpenAI returned an unknown best_trend_id."
        )

    return result
