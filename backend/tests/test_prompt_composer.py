import pytest
from app.services.prompt_composer import (
    BrandContext,
    PlatformContext,
    PLATFORM_NOTES,
    TONE_STYLE_MAP,
    build_generation_prompt,
    compose_full_prompt,

    
)
from app.models.generation import (
    AgeRangeEnum,
    AudienceSegmentEnum,
    CampaignGoalEnum,
    ContentTypeEnum,
    GenderFocusEnum,
    GenerationBrief,
    TargetAudience,
    VoiceToneEnum,
)
from app.services.presets import PLATFORM_PRESETS
from tests.test_generation import VALID_BRIEF


USER_PROMPT = "A modern minimal office"

SAMPLE_BRAND = BrandContext(
    name="Acme",
    tagline="Build the future",
    tone="professional",
    audience="startup founders aged 25-40",
    colors=["#1E3A8A", "#3B82F6"],
    avoid_words="cheap, discount, budget",
    industry="interior design",
)

SAMPLE_PLATFORM = PlatformContext(
    label="Instagram Post",
    width=1080,
    height=1080,
    aspect_ratio="1:1",
    note="Square 1:1 format. Design should work as a grid tile — keep key content centered.",
)


# --- Section ordering ---


def test_system_role_is_first():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert result.startswith("You are a professional social media image designer.")


def test_section_ordering_full():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="prompt",
        brand_has_logo=True,
    )
    brand_idx = result.index("=== BRAND IDENTITY ===")
    composition_idx = result.index("=== COMPOSITION ===")
    logo_idx = result.index("=== LOGO ===")
    request_idx = result.index("=== IMAGE REQUEST ===")
    assert brand_idx < composition_idx < logo_idx < request_idx


def test_user_request_is_last():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert result.endswith(f"=== IMAGE REQUEST ===\n{USER_PROMPT}")


# --- Brand context ---


def test_no_brand_context_omits_brand_section():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "BRAND IDENTITY" not in result


def test_full_brand_context_includes_all_fields():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "Brand: Acme" in result
    assert "Business field: interior design" in result
    assert 'Tagline: "Build the future"' in result
    assert "Visual style:" in result
    assert "Target audience: startup founders aged 25-40" in result
    assert "Brand colors: #1E3A8A, #3B82F6" in result
    assert "AVOID" in result
    assert "cheap, discount, budget" in result


def test_partial_brand_context_omits_null_fields():
    partial = BrandContext(name="MiniBrand", tone="casual", audience="teens", colors=["#FF0000"])
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=partial,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "Brand: MiniBrand" in result
    assert "Tagline" not in result
    assert "AVOID" not in result
    assert "Visual style:" in result
    assert "Target audience: teens" in result


def test_no_none_specified_in_output():
    partial = BrandContext(name="TestBrand")
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=partial,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "None specified" not in result
    assert "None" not in result.split("=== BRAND IDENTITY ===")[1].split("=== PLATFORM ===")[0]


# --- Tone mapping ---


def test_each_tone_maps_to_style():
    for tone, expected_style in TONE_STYLE_MAP.items():
        ctx = BrandContext(name="T", tone=tone, audience="x", colors=["#000"])
        result = compose_full_prompt(
            user_prompt=USER_PROMPT,
            brand_context=ctx,
            platform=SAMPLE_PLATFORM,
            logo_mode="none",
            brand_has_logo=False,
        )
        assert expected_style in result, f"tone={tone} style not found"


# --- Platform context ---


def test_platform_always_present():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "=== COMPOSITION ===" in result
    assert "grid tile" in result


def test_platform_label_and_dimensions_not_leaked_to_prompt():
    # Prevents Gemini from rendering platform metadata as on-canvas text.
    # See: regression where "Facebook Post" + "1200x630 landscape" appeared
    # as a header/subtitle on generated images.
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "Instagram Post" not in result
    assert "1080x1080" not in result
    assert "Platform:" not in result


def test_platform_notes_cover_all_presets():
    for preset_id in PLATFORM_PRESETS:
        assert preset_id in PLATFORM_NOTES, f"Missing PLATFORM_NOTES entry for {preset_id}"


# --- Logo mode ---


def test_logo_prompt_mode_with_logo():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="prompt",
        brand_has_logo=True,
    )
    assert "=== LOGO ===" in result
    assert "corner" in result


def test_logo_prompt_mode_without_logo():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="prompt",
        brand_has_logo=False,
    )
    assert "LOGO" not in result


def test_logo_watermark_mode_never_in_prompt():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="watermark",
        brand_has_logo=True,
    )
    assert "LOGO" not in result


def test_logo_both_mode_with_logo():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="both",
        brand_has_logo=True,
    )
    assert "=== LOGO ===" in result


def test_logo_both_mode_without_logo():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="both",
        brand_has_logo=False,
    )
    assert "LOGO" not in result


def test_logo_none_mode():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=True,
    )
    assert "LOGO" not in result


# --- build_generation_prompt tests (Sprint 2 Structured Generation) ---

SAMPLE_BRIEF = GenerationBrief(
    campaign_goal=CampaignGoalEnum.product_launch,
    content_type=ContentTypeEnum.product_showcase,
    target_audience=TargetAudience(
        segments=[AudienceSegmentEnum.small_business_owners],
        location="Amman, Jordan",
        age_range=AgeRangeEnum.age_25_34,
        gender_focus=GenderFocusEnum.all,
        details="Local café and bakery owners looking to upgrade their summer menu.",
    ),
    core_idea="إطلاق مشروب قهوة بارد جديد ومنعش لصباح صيفي مزدحم.",
    voice_tone=VoiceToneEnum.friendly,
    optional_notes="اترك مساحة في الأعلى لكتابة نص عربي واضح.",
    text_to_include="خصم 20% لفترة محدودة",
)


def test_build_generation_prompt_section_ordering_full():
    result = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="prompt",
        brand_has_logo=True,
    )
    system_idx = result.index("You are a professional social media image designer.")
    brief_idx = result.index("=== CAMPAIGN BRIEF ===")
    brand_idx = result.index("=== BRAND IDENTITY ===")
    composition_idx = result.index("=== COMPOSITION ===")
    logo_idx = result.index("=== LOGO ===")
    output_idx = result.index("=== OUTPUT RULES ===")

    assert system_idx < brief_idx < brand_idx < composition_idx < logo_idx < output_idx


def test_build_generation_prompt_maps_enums_to_readable_instructions():
    result = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "Campaign Goal: Communicate a product or service launch." in result
    assert "Content Type: Visual product showcase focusing on aesthetic product presentation." in result
    assert "Tone & Style: Friendly, warm, and approachable." in result
    assert "Demographic: small business owners" in result
    assert "Location/Market: Amman, Jordan" in result
    assert "Age group: 25–34 years old" in result
    assert "Gender focus: all genders" in result
    assert "Details: Local café and bakery owners looking to upgrade their summer menu." in result


def test_build_generation_prompt_preserves_arabic_and_user_text():
    result = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "Core Idea: إطلاق مشروب قهوة بارد جديد ومنعش لصباح صيفي مزدحم." in result
    assert 'Exact visible text to include; preserve exactly: "خصم 20% لفترة محدودة"' in result
    assert "Design Notes: اترك مساحة في الأعلى لكتابة نص عربي واضح." in result


def test_build_generation_prompt_custom_fields():
    custom_brief = GenerationBrief(
        campaign_goal=CampaignGoalEnum.custom,
        campaign_goal_custom="احتفال بالذكرى السنوية الخامسة",
        content_type=ContentTypeEnum.custom,
        content_type_custom="بطاقة شكر مخصصة للعملاء",
        target_audience=TargetAudience(
            segments=[AudienceSegmentEnum.custom],
            details="عملاء المتجر الأوفياء في كافة الفروع.",
        ),
        core_idea="التعبير عن الامتنان للعملاء مع تقديم مفاجأة خاصة.",
        voice_tone=VoiceToneEnum.custom,
        voice_tone_custom="دافئ جدًا ومفعم بالتقدير",
    )
    result = build_generation_prompt(
        brief=custom_brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "Campaign Goal: احتفال بالذكرى السنوية الخامسة" in result
    assert "Content Type: بطاقة شكر مخصصة للعملاء" in result
    assert "Tone & Style: دافئ جدًا ومفعم بالتقدير" in result
    assert "Demographic: custom audience" in result
    assert "Details: عملاء المتجر الأوفياء في كافة الفروع." in result


def test_build_generation_prompt_output_rules_always_present():
    result = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )
    assert "=== OUTPUT RULES ===" in result
    assert "Do NOT render section headers" in result


def test_prompt_contains_english_language_instruction():
    result = build(language="en")

    assert "Write newly generated campaign copy in English." in result


def test_prompt_contains_arabic_language_instruction():
    result = build(language="ar")

    assert "Write newly generated campaign copy in Arabic." in result

def build(language=None, core_idea=None, logo_mode="none", brand_has_logo=False):
    brief_data = dict(VALID_BRIEF)

    if language is not None:
        brief_data["language"] = language

    if core_idea is not None:
        brief_data["core_idea"] = core_idea

    return build_generation_prompt(
        brief=GenerationBrief.model_validate(brief_data),
        brand_context=BrandContext(
            name="Acme Coffee",
            tagline="Make mornings brighter",
            tone="friendly",
            colors=["#123456", "#F4C95D"],
            avoid_words="cheap",
        ),
        platform= SAMPLE_PLATFORM,
        logo_mode=logo_mode,
        brand_has_logo=brand_has_logo,
    )

def test_language_instruction_is_in_output_rules():
    result = build(language="ar")

    campaign_start = result.index("=== CAMPAIGN BRIEF ===")
    output_start = result.index("=== OUTPUT RULES ===")

    campaign_section = result[campaign_start:output_start]
    output_section = result[output_start:]

    assert "Write newly generated campaign copy in Arabic." not in campaign_section
    assert "Write newly generated campaign copy in Arabic." in output_section

def test_language_instruction_appears_once():
    result = build(language="ar")

    assert result.count(
        "Write newly generated campaign copy in Arabic."
    ) == 1

def test_prompt_language_output_is_deterministic():
    assert build(language="ar") == build(language="ar")



def test_generation_brief_preserves_unicode_text():
    unicode_text = "مرحباً — إصدار 3.0 ☕ #قهوة"

    brief_data = dict(VALID_BRIEF)
    brief_data["core_idea"] = unicode_text

    brief = GenerationBrief.model_validate(brief_data)

    assert brief.core_idea == unicode_text

def test_prompt_preserves_arabic_mixed_script_and_user_text():
    brief_data = dict(VALID_BRIEF)
    brief_data.update(
        {
            "language": "ar",
            "core_idea": "إطلاق TREND AI 2026 — خصم 20% #قهوة",
            "text_to_include": "خصم 20% لفترة محدودة",
            "optional_notes": "لا تغيّر النص! Keep it exact.",
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

    assert brief_data["core_idea"] in result
    assert brief_data["text_to_include"] in result
    assert brief_data["optional_notes"] in result

def test_prompt_does_not_corrupt_unicode_text():
    value = "مرحباً — إصدار 3.0 ☕ #قهوة"
    brief_data = dict(VALID_BRIEF)
    brief_data["core_idea"] = value

    brief = GenerationBrief.model_validate(brief_data)
    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert value in result
    assert "�" not in result
    assert "����" not in result

def test_language_instruction_does_not_translate_user_text():
    original = "إطلاق TREND AI 2026 — خصم 20%"
    brief_data = dict(VALID_BRIEF)
    brief_data.update({"language": "en", "core_idea": original})

    brief = GenerationBrief.model_validate(brief_data)
    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert original in result
    
def test_user_text_is_preserved_from_model_to_prompt():
    original_values = {
        "core_idea": "إطلاق TREND AI 2026 — خصم 20% #قهوة",
        "text_to_include": "خصم 20% لفترة محدودة",
        "optional_notes": "لا تغيّر النص! Keep this exact.",
    }

    brief_data = dict(VALID_BRIEF)
    brief_data.update(
        {
            "language": "ar",
            **original_values,
        }
    )

    brief = GenerationBrief.model_validate(brief_data)

    assert brief.core_idea == original_values["core_idea"]
    assert brief.text_to_include == original_values["text_to_include"]
    assert brief.optional_notes == original_values["optional_notes"]

    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    for value in original_values.values():
        assert value in result

    assert "\ufffd" not in result


def test_prompt_composer_language_instruction_server_side_formatting():
    """Verify that language directive reaches prompt composer output rules without modifying exact visible text."""
    exact_text = "WELCOME 2026! خصم خاص"
    brief_data = dict(VALID_BRIEF)
    brief_data.update({
        "language": "en",
        "text_to_include": exact_text
    })

    brief = GenerationBrief.model_validate(brief_data)
    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    # Check exact visible text preserved
    assert f'Exact visible text to include; preserve exactly: "{exact_text}"' in result
    # Check language instruction applied server-side
    assert "Write newly generated campaign copy in English." in result

def test_arabic_language_instruction_is_added_to_prompt():
    prompt = build(language="ar")

    assert "Write newly generated campaign copy in Arabic." in prompt
    assert "Write newly generated campaign copy in English." not in prompt

def test_english_language_instruction_is_added_to_prompt():
    prompt = build(language="en")

    assert "Write newly generated campaign copy in English." in prompt
    assert "Write newly generated campaign copy in Arabic." not in prompt

@pytest.mark.parametrize(
    ("language", "instruction"),
    [
        ("ar", "Write newly generated campaign copy in Arabic."),
        ("en", "Write newly generated campaign copy in English."),
    ],
)
def test_language_instruction_appears_once(language, instruction):
    prompt = build(language=language)

    assert prompt.count(instruction) == 1

def test_prompt_preserves_core_idea_exactly():
    idea = "إطلاق منتج جديد — Summer launch #2026"

    prompt = build(
        language="en",
        core_idea=idea,
    )

    assert idea in prompt

