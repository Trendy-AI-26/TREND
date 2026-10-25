"""Validated request and response contracts for caption generation.

This module deliberately contains no provider or persistence logic. It defines
the boundary between the caption API and the caption-generation service.

Generation-level context (language, platform, image, brief, and brand context)
is inherited by the service from the referenced generation. The client may
send caption-specific preferences only.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
)

from app.models.generation import TextLanguageEnum


CAPTION_MAX_LENGTH = 2200
HOOK_MAX_LENGTH = 120
DISCLAIMER_MAX_LENGTH = 500
TONE_MAX_LENGTH = 50
EXTRA_NOTES_MAX_LENGTH = 500

MAX_HASHTAGS = 8
HASHTAG_MAX_LENGTH = 50

MAX_KEYWORDS = 10
KEYWORD_MAX_LENGTH = 80


class CaptionPreferences(BaseModel):
    """Optional, bounded preferences supplied by the user."""

    model_config = ConfigDict(extra="forbid")

    tone: str | None = Field(
        default=None,
        max_length=TONE_MAX_LENGTH,
    )

    include_cta: StrictBool = True

    include_emojis: StrictBool = False

    max_hashtags: StrictInt = Field(
        default=5,
        ge=0,
        le=MAX_HASHTAGS,
    )

    extra_notes: str | None = Field(
        default=None,
        max_length=EXTRA_NOTES_MAX_LENGTH,
    )

    @field_validator("tone", "extra_notes", mode="before")
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        normalized = value.strip()

        return normalized or None


class CaptionRequest(BaseModel):
    """Optional caption preferences for an existing successful generation.

    The endpoint derives language, platform, brief, image, and brand context
    from ``generation_id``. Those fields intentionally do not belong here so
    the client cannot create a context mismatch with the generated image.
    """

    model_config = ConfigDict(extra="forbid")

    preferences: CaptionPreferences | None = None


class CaptionResponse(BaseModel):
    """Structured caption output returned after provider validation."""

    model_config = ConfigDict(extra="forbid")

    caption: str = Field(
        ...,
        min_length=1,
        max_length=CAPTION_MAX_LENGTH,
    )

    # The key itself is required, but its value may be null.
    hook: str | None = Field(
        ...,
        max_length=HOOK_MAX_LENGTH,
    )

    # These fields are required even when the arrays are empty.
    hashtags: list[str] = Field(
        ...,
        max_length=MAX_HASHTAGS,
    )

    keywords: list[str] = Field(
        ...,
        max_length=MAX_KEYWORDS,
    )

    # StrictBool prevents values such as 0, 1, "true", and "false".
    trend_used: StrictBool

    language: TextLanguageEnum

    disclaimer: str | None = Field(
        default=None,
        max_length=DISCLAIMER_MAX_LENGTH,
    )

    @field_validator("caption", mode="before")
    @classmethod
    def normalize_caption(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        return value.strip()

    @field_validator("hook", "disclaimer", mode="before")
    @classmethod
    def normalize_optional_response_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        normalized = value.strip()

        return normalized or None

    @field_validator("hashtags")
    @classmethod
    def validate_hashtags(
        cls,
        value: list[str],
    ) -> list[str]:
        normalized: list[str] = []

        for hashtag in value:
            hashtag = hashtag.strip()

            invalid_hashtag = (
                len(hashtag) < 2
                or len(hashtag) > HASHTAG_MAX_LENGTH
                or not hashtag.startswith("#")
                or "#" in hashtag[1:]
                or any(character.isspace() for character in hashtag[1:])
            )

            if invalid_hashtag:
                raise ValueError(
                    "hashtags must start with #, contain no whitespace "
                    "or extra #, and be at most "
                    f"{HASHTAG_MAX_LENGTH} characters"
                )

            normalized.append(hashtag)

        normalized_values = {
            hashtag.casefold()
            for hashtag in normalized
        }

        if len(normalized_values) != len(normalized):
            raise ValueError(
                "hashtags must not contain duplicates"
            )

        return normalized

    @field_validator("keywords")
    @classmethod
    def validate_keywords(
        cls,
        value: list[str],
    ) -> list[str]:
        normalized: list[str] = []

        for keyword in value:
            keyword = keyword.strip()

            if not keyword:
                raise ValueError(
                    "keywords must not contain empty values"
                )

            if len(keyword) > KEYWORD_MAX_LENGTH:
                raise ValueError(
                    "keywords must be at most "
                    f"{KEYWORD_MAX_LENGTH} characters"
                )

            if keyword.startswith("#"):
                raise ValueError(
                    "keywords must not start with #"
                )

            normalized.append(keyword)

        normalized_values = {
            keyword.casefold()
            for keyword in normalized
        }

        if len(normalized_values) != len(normalized):
            raise ValueError(
                "keywords must not contain duplicates"
            )

        return normalized


__all__ = [
    "CAPTION_MAX_LENGTH",
    "HOOK_MAX_LENGTH",
    "DISCLAIMER_MAX_LENGTH",
    "TONE_MAX_LENGTH",
    "EXTRA_NOTES_MAX_LENGTH",
    "MAX_HASHTAGS",
    "HASHTAG_MAX_LENGTH",
    "MAX_KEYWORDS",
    "KEYWORD_MAX_LENGTH",
    "CaptionPreferences",
    "CaptionRequest",
    "CaptionResponse",
]
