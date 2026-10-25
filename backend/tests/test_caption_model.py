import pytest
from pydantic import ValidationError

from app.models.caption import (
    CaptionPreferences,
    CaptionRequest,
    CaptionResponse,
)


def test_caption_request_accepts_preferences_only():
    request = CaptionRequest.model_validate(
        {
            "preferences": {
                "tone": "  friendly  ",
                "include_cta": True,
                "include_emojis": False,
                "max_hashtags": 5,
                "extra_notes": "  ركز على العرض الحالي  ",
            },
        }
    )

    assert request.preferences is not None
    assert request.preferences.tone == "friendly"
    assert request.preferences.extra_notes == "ركز على العرض الحالي"


def test_caption_request_accepts_empty_request():
    request = CaptionRequest.model_validate(
        {}
    )

    assert request.preferences is None


@pytest.mark.parametrize("field", ["language", "platform_preset"])
def test_caption_request_rejects_inherited_generation_fields(field):
    with pytest.raises(ValidationError):
        CaptionRequest.model_validate(
            {
                field: "ar" if field == "language" else "instagram_post",
            }
        )


def test_caption_request_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CaptionRequest.model_validate(
            {
                "trend_used": True,
            }
        )


@pytest.mark.parametrize(
    "max_hashtags",
    [
        -1,
        9,
        5.5,
        "5",
    ],
)
def test_caption_preferences_reject_invalid_max_hashtags(
    max_hashtags,
):
    with pytest.raises(ValidationError):
        CaptionPreferences.model_validate(
            {
                "max_hashtags": max_hashtags,
            }
        )


@pytest.mark.parametrize(
    "field",
    [
        "include_cta",
        "include_emojis",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        0,
        1,
        "false",
        "true",
        None,
    ],
)
def test_caption_preferences_require_real_booleans(
    field,
    value,
):
    with pytest.raises(ValidationError):
        CaptionPreferences.model_validate(
            {
                field: value,
            }
        )


def test_caption_preferences_normalize_empty_optional_text_to_none():
    preferences = CaptionPreferences.model_validate(
        {
            "tone": "  ",
            "extra_notes": "   ",
        }
    )

    assert preferences.tone is None
    assert preferences.extra_notes is None


def test_caption_preferences_reject_overlong_extra_notes():
    with pytest.raises(ValidationError):
        CaptionPreferences.model_validate(
            {
                "extra_notes": "x" * 501,
            }
        )


def test_caption_response_accepts_structured_arabic_output():
    response = CaptionResponse.model_validate(
        {
            "caption": "  اكتشفوا تشكيلتنا الجديدة الآن.  ",
            "hook": "رائحة تترك أثرًا",
            "hashtags": [
                "#عطور",
                "#عروض",
            ],
            "keywords": [
                "عطور",
                "عروض عطور",
            ],
            "trend_used": False,
            "language": "ar",
            "disclaimer": None,
        }
    )

    assert response.caption == "اكتشفوا تشكيلتنا الجديدة الآن."
    assert response.language.value == "ar"
    assert response.trend_used is False


def test_caption_response_allows_nullable_hook_and_empty_lists():
    response = CaptionResponse.model_validate(
        {
            "caption": "A concise English caption.",
            "hook": None,
            "hashtags": [],
            "keywords": [],
            "trend_used": False,
            "language": "en",
        }
    )

    assert response.hook is None
    assert response.hashtags == []
    assert response.keywords == []
    assert response.disclaimer is None


@pytest.mark.parametrize(
    "missing_field",
    [
        "hashtags",
        "keywords",
    ],
)
def test_caption_response_requires_structured_list_fields(
    missing_field,
):
    payload = {
        "caption": "Caption",
        "hook": None,
        "hashtags": [],
        "keywords": [],
        "trend_used": False,
        "language": "en",
    }

    del payload[missing_field]

    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(payload)


def test_caption_response_rejects_empty_caption_after_normalization():
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "   ",
                "hook": None,
                "hashtags": [],
                "keywords": [],
                "trend_used": False,
                "language": "ar",
            }
        )


def test_caption_response_rejects_more_than_eight_hashtags():
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "Caption",
                "hook": None,
                "hashtags": [
                    f"#{index}"
                    for index in range(9)
                ],
                "keywords": [],
                "trend_used": False,
                "language": "en",
            }
        )


@pytest.mark.parametrize(
    "hashtags",
    [
        ["عطور"],
        ["##عطور"],
        ["#عطور جديدة"],
        ["#عطور", "#عطور"],
        ["#عطور", "#عطور"],
    ],
)
def test_caption_response_rejects_invalid_hashtags(
    hashtags,
):
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "Caption",
                "hook": None,
                "hashtags": hashtags,
                "keywords": [],
                "trend_used": False,
                "language": "en",
            }
        )


def test_caption_response_rejects_invalid_keywords():
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "Caption",
                "hook": None,
                "hashtags": [],
                "keywords": ["#keyword"],
                "trend_used": False,
                "language": "en",
            }
        )


def test_caption_response_rejects_empty_keywords():
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "Caption",
                "hook": None,
                "hashtags": [],
                "keywords": [""],
                "trend_used": False,
                "language": "en",
            }
        )


def test_caption_response_rejects_duplicate_keywords():
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "Caption",
                "hook": None,
                "hashtags": [],
                "keywords": [
                    "Brand",
                    " brand ",
                ],
                "trend_used": False,
                "language": "en",
            }
        )


@pytest.mark.parametrize(
    "trend_used",
    [
        0,
        1,
        "false",
        "true",
        None,
    ],
)
def test_caption_response_requires_a_real_boolean_for_trend_used(
    trend_used,
):
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "Caption",
                "hook": None,
                "hashtags": [],
                "keywords": [],
                "trend_used": trend_used,
                "language": "en",
            }
        )


def test_caption_response_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CaptionResponse.model_validate(
            {
                "caption": "Caption",
                "hook": None,
                "hashtags": [],
                "keywords": [],
                "trend_used": False,
                "language": "en",
                "provider_secret": "must-not-be-accepted",
            }
        )
