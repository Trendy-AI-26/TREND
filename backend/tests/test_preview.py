from app.models.generation import GenerationBrief
from app.services.brief_preview import build_creative_direction
from app.services.prompt_composer import build_generation_prompt
from tests.test_prompt_composer import SAMPLE_PLATFORM
from tests.test_generation import VALID_BRIEF

def test_creative_direction_preserves_user_text():
    brief_data = dict(VALID_BRIEF)
    brief_data.update(
        {
            "language": "ar",
            "core_idea": "إطلاق TREND AI 2026 — خصم 20% على Cold Brew #قهوة",
            "text_to_include": "خصم 20% لفترة محدودة",
            "optional_notes": "لا تغيّر النص! Keep this exact.",
        }
    )

    brief = GenerationBrief.model_validate(brief_data)

    result = build_creative_direction(
        brief=brief,
        brand_name="Test Brand",
        platform_preset="instagram_story",
        brand_context=None,
    )

    assert result["language"] == "ar"
    assert result["core_idea"] == brief_data["core_idea"]
    assert result["text_to_include"] == brief_data["text_to_include"]
    assert result["optional_notes"] == brief_data["optional_notes"]

def test_prompt_preserves_all_user_text_fields_exactly():
    brief_data = dict(VALID_BRIEF)
    brief_data.update(
        {
            "language": "ar",
            "core_idea": "إطلاق TREND AI 2026 — خصم 20% #قهوة",
            "text_to_include": "خصم 20% لفترة محدودة",
            "optional_notes": "لا تغيّر النص! Keep this exact.",
        }
    )

    brief = GenerationBrief.model_validate(brief_data)

    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    for field_name in ("core_idea", "text_to_include", "optional_notes"):
        assert brief_data[field_name] in result


def test_creative_direction_reflects_english_language():
    brief_data = dict(VALID_BRIEF)
    brief_data.update({"language": "en"})
    brief = GenerationBrief.model_validate(brief_data)

    result = build_creative_direction(
        brief=brief,
        brand_name="Test Brand",
        platform_preset="instagram_story",
        brand_context=None,
    )

    assert result["language"] == "en"


def test_creative_direction_does_not_build_full_prompt():
    """Ensure preview returns structured brief direction data without composing the full image prompt."""
    brief = GenerationBrief.model_validate(VALID_BRIEF)

    result = build_creative_direction(
        brief=brief,
        brand_name="Test Brand",
        platform_preset="instagram_story",
        brand_context=None,
    )

    # Preview should be a structured dictionary/payload, not a raw string prompt
    assert isinstance(result, dict)
    assert "You are a professional social media image designer" not in str(result)
    assert "=== OUTPUT RULES ===" not in str(result)        
