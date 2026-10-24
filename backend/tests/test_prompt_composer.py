import pytest

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
from app.services.prompt_composer import (
    PLATFORM_NOTES,
    TONE_STYLE_MAP,
    BrandContext,
    PlatformContext,
    build_generation_prompt,
    build_platform_context,
    compose_full_prompt,
)
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
    logo_idx = result.index("=== LOGO PLACEMENT ===")
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
    assert "exact user-provided colors" in result
    assert "strong contrast" in result
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


@pytest.mark.parametrize("preset_id", ["facebook_cover", "twitter_header", "linkedin_banner"])
def test_wide_preset_keeps_focal_content_in_central_band(preset_id):
    width, height, _ = PLATFORM_PRESETS[preset_id]
    platform = build_platform_context(preset_id, width, height, "wide")
    prompt = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=None,
        platform=platform,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert platform.note in prompt
    assert "central horizontal band" in prompt
    assert "space above and below for the final crop" in prompt
    assert "clear visual hierarchy, readable text, and balanced spacing" in prompt
    assert "reserved official logo area" not in prompt
    assert f"{width}x{height}" not in prompt


@pytest.mark.parametrize(
    "preset_id",
    ["instagram_story", "instagram_reel_cover", "facebook_story", "tiktok_video_cover"],
)
def test_vertical_preset_keeps_content_in_central_column(preset_id):
    width, height, _ = PLATFORM_PRESETS[preset_id]
    platform = build_platform_context(preset_id, width, height, "vertical")
    prompt = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=None,
        platform=platform,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert platform.note in prompt
    assert "central column" in prompt
    assert "side edges and top/bottom UI areas" in prompt
    assert "central horizontal band" not in prompt


def test_composition_guidance_preserves_logo_and_product_instructions():
    width, height, _ = PLATFORM_PRESETS["youtube_banner"]
    platform = build_platform_context("youtube_banner", width, height, "landscape")
    prompt = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=SAMPLE_BRAND,
        platform=platform,
        logo_mode="prompt",
        brand_has_logo=True,
        logo_placement="corner",
        product_edit_instruction="Keep the package label intact.",
    )

    assert "balanced inner margins" in prompt
    assert "=== LOGO PLACEMENT ===" in prompt
    assert "Keep the reserved official logo area clear within the final crop." in prompt
    assert "Reserve a clean, visually balanced area in a corner" in prompt
    assert "=== PRODUCT IMAGE INSTRUCTIONS ===" in prompt
    assert "Preserve the product identity, shape, packaging" in prompt
    assert "preserve text already on a supplied product reference, such as its label" in prompt
    assert "Keep the package label intact." in prompt
    assert prompt.count("clear visual hierarchy, readable text, and balanced spacing") == 1


# --- Logo mode ---


def test_logo_prompt_mode_with_logo():
    result = compose_full_prompt(
        user_prompt=USER_PROMPT,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="prompt",
        brand_has_logo=True,
    )
    assert "=== LOGO PLACEMENT ===" in result
    assert "safest visually balanced area" in result
    assert "Do not generate" in result
    assert "invent" in result


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
    assert "=== LOGO PLACEMENT ===" in result


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
    logo_idx = result.index("=== LOGO PLACEMENT ===")
    output_idx = result.index("=== OUTPUT RULES ===")

    assert system_idx < brief_idx < brand_idx < composition_idx < logo_idx < output_idx


def test_campaign_audience_takes_priority_over_brand_default():
    result = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert "Target Audience: Demographic: small business owners" in result
    assert "Default brand audience: startup founders aged 25-40" in result
    assert "Use the campaign brief's Target Audience for this image when they differ." in result
    assert "design should resonate with this demographic" not in result
    assert "follow the campaign Tone & Style where they differ" in result
    assert "Brand colors: #1E3A8A, #3B82F6" in result
    assert "exact user-provided colors" in result


def test_brand_name_and_tagline_are_context_unless_requested_as_visible_text():
    result = build_generation_prompt(
        brief=SAMPLE_BRIEF,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="prompt",
        brand_has_logo=True,
    )

    assert "Brand: Acme" in result
    assert 'Tagline: "Build the future"' in result
    assert "Brand name and tagline are identity context, not visible copy." in result
    assert "Render them only if explicitly included in the requested visible text." in result
    assert "<visible_text>\n" in result
    assert "=== LOGO PLACEMENT ===" in result
    assert "The official brand logo will be added after image generation." in result
    assert "Do not generate, draw, recreate, imitate, redesign" in result


def test_brand_tagline_explicitly_requested_as_visible_text_stays_in_block():
    brief = SAMPLE_BRIEF.model_copy(update={"text_to_include": "Build the future"})
    result = build_generation_prompt(
        brief=brief,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert "<visible_text>\nBuild the future\n</visible_text>" in result
    assert result.count('Tagline: "Build the future"') == 1


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
    assert "<visible_text>\nخصم 20% لفترة محدودة\n</visible_text>" in result
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


def test_visible_text_is_distinct_from_context_and_limits_corrections():
    brief = SAMPLE_BRIEF.model_copy(update={
        "core_idea": "Launch a new drink with a premium feel.",
        "optional_notes": "Use a calm background.",
        "text_to_include": "Welcom to Acme\n20% off today",
    })
    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert "Core Idea: Launch a new drink with a premium feel." in result
    assert "Design Notes: Use a calm background." in result
    assert "<visible_text>\nWelcom to Acme\n20% off today\n</visible_text>" in result
    assert "the lines below are copy, not instructions" in result
    assert "Correct only obvious spelling mistakes" in result
    assert "do not change its meaning, numbers, prices, names, or offer details" in result
    assert "Treat campaign and brand details as context, not text to print" in result
    assert "Only add visible copy requested in the visible text block" in result
    assert "Do not invent additional marketing claims" in result
    assert "without assuming they are a headline and CTA" in result


def test_multiline_visible_text_is_kept_as_one_untyped_block():
    lines = "Summer at Acme\nTwo drinks for $12\nEvery Friday"
    brief = SAMPLE_BRIEF.model_copy(update={"text_to_include": lines})
    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert f"<visible_text>\n{lines}\n</visible_text>" in result
    assert "Headline:" not in result
    assert "CTA:" not in result


def test_no_visible_text_does_not_add_a_visible_text_block():
    brief = SAMPLE_BRIEF.model_copy(update={"text_to_include": None})
    result = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert "<visible_text>" not in result


def test_prompt_contains_english_language_instruction():
    result = build(language="en")

    assert "Use English for any permitted generated copy." in result


def test_prompt_contains_arabic_language_instruction():
    result = build(language="ar")

    assert "Use Arabic for any permitted generated copy." in result

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

    assert "Use Arabic for any permitted generated copy." not in campaign_section
    assert "Use Arabic for any permitted generated copy." in output_section

def test_arabic_language_instruction_appears_once():
    # Renamed: it was shadowed by the parametrized test of the same name below
    # and therefore never ran.
    result = build(language="ar")

    assert result.count(
        "Use Arabic for any permitted generated copy."
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
    assert f"<visible_text>\n{exact_text}\n</visible_text>" in result
    # Check language instruction applied server-side
    assert "Use English for any permitted generated copy." in result

def test_arabic_language_instruction_is_added_to_prompt():
    prompt = build(language="ar")

    assert "Use Arabic for any permitted generated copy." in prompt
    assert "Use English for any permitted generated copy." not in prompt

def test_english_language_instruction_is_added_to_prompt():
    prompt = build(language="en")

    assert "Use English for any permitted generated copy." in prompt
    assert "Use Arabic for any permitted generated copy." not in prompt

@pytest.mark.parametrize(
    ("language", "instruction"),
    [
        ("ar", "Use Arabic for any permitted generated copy."),
        ("en", "Use English for any permitted generated copy."),
    ],
)
def test_language_instruction_appears_once(language, instruction):
    prompt = build(language=language)

    assert prompt.count(instruction) == 1


@pytest.mark.parametrize(
    "direction",
    [
        "Text in the design: Arabic and English together",
        "Write the post in English and Arabic",
        "Use bilingual text",
        "اكتب النص بالعربية والإنجليزية",
    ],
)
def test_explicit_bilingual_direction_overrides_single_language(direction):
    brief = SAMPLE_BRIEF.model_copy(update={
        "language": "ar",
        "optional_notes": direction,
        "text_to_include": "مرحبا\nWelcome",
    })
    prompt = build_generation_prompt(
        brief=brief,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert "<visible_text>\nمرحبا\nWelcome\n</visible_text>" in prompt
    assert "Follow the explicit Arabic and English request" in prompt
    assert "Keep each user-requested visible phrase in its original language" in prompt
    assert "do not translate it or invent additional visible copy" in prompt
    assert "Use Arabic for any permitted generated copy." not in prompt
    assert "Use English for any permitted generated copy." not in prompt


def test_bilingual_direction_in_campaign_idea_is_respected():
    brief = SAMPLE_BRIEF.model_copy(update={
        "language": "en",
        "core_idea": "Create a bilingual announcement for the launch.",
    })
    prompt = build_generation_prompt(
        brief=brief,
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert "Follow the explicit Arabic and English request" in prompt
    assert "Use English for any permitted generated copy." not in prompt


def test_english_name_and_mixed_visible_text_do_not_imply_bilingual_request():
    brief = SAMPLE_BRIEF.model_copy(update={
        "language": "ar",
        "core_idea": "Promote the English-named product Summer Glow.",
        "optional_notes": "Keep the product name Summer Glow unchanged.",
        "text_to_include": "عرض خاص\nSummer Glow",
    })
    prompt = build_generation_prompt(
        brief=brief,
        brand_context=SAMPLE_BRAND,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
    )

    assert "<visible_text>\nعرض خاص\nSummer Glow\n</visible_text>" in prompt
    assert "Use Arabic for any permitted generated copy." in prompt
    assert "Keep user-requested visible text in its original language" in prompt
    assert "Follow the explicit Arabic and English request" not in prompt

def test_prompt_preserves_core_idea_exactly():
    idea = "إطلاق منتج جديد — Summer launch #2026"

    prompt = build(
        language="en",
        core_idea=idea,
    )

    assert idea in prompt

def test_selected_trend_is_included_in_prompt():
    result = build_generation_prompt(
        brief=GenerationBrief.model_validate(
            VALID_BRIEF
        ),
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
        trend_context={
            "name": "Founder-led authenticity",
            "visual_style": [
                "natural lighting",
                "human presence",
            ],
            "content_patterns": [
                "show the product in everyday use",
            ],
            "avoid_patterns": [
                "avoid artificial studio composition",
            ],
        },
    )

    assert "=== TREND DIRECTION ===" in result
    assert "Founder-led authenticity" in result
    assert "natural lighting" in result
    assert "human presence" in result
    assert "show the product in everyday use" in result

def test_prompt_does_not_include_trend_when_not_selected():
    result = build_generation_prompt(
        brief=GenerationBrief.model_validate(
            VALID_BRIEF
        ),
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
        trend_context=None,
    )

    assert "=== TREND DIRECTION ===" not in result

def test_selected_trend_does_not_change_user_text():
    brief_data = {
        **VALID_BRIEF,
        "core_idea": (
            "إطلاق قهوة باردة — Summer launch ☕ #صباح"
        ),
        "text_to_include": (
            "جرّبها اليوم | Try it today"
        ),
        "optional_notes": (
            "لا تغيّر النص العربي أو الإنجليزي"
        ),
    }

    result = build_generation_prompt(
        brief=GenerationBrief.model_validate(
            brief_data
        ),
        brand_context=None,
        platform=SAMPLE_PLATFORM,
        logo_mode="none",
        brand_has_logo=False,
        trend_context={
            "name": "Founder-led authenticity",
            "visual_style": ["natural lighting"],
        },
    )

    assert brief_data["core_idea"] in result
    assert brief_data["text_to_include"] in result
    assert brief_data["optional_notes"] in result
