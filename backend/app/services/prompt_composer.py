from dataclasses import dataclass, field
from typing import Any
from app.models.generation import (
    GenerationBrief,
    TargetAudience,
)


@dataclass(frozen=True, slots=True)
class BrandContext:
    name: str
    tagline: str | None = None
    tone: str | None = None
    audience: str | None = None
    colors: list[str] = field(default_factory=list)
    avoid_words: str | None = None
    industry: str | None = None


@dataclass(frozen=True, slots=True)
class PlatformContext:
    label: str
    width: int
    height: int
    aspect_ratio: str
    note: str


SYSTEM_ROLE_PROMPT: str = (
    "You are a professional social media image designer. "
    "Create a high-quality image following these specifications. "
    "The bracketed section headers (lines wrapped in === ===) are "
    "instructions for you only — never reproduce them, the section "
    "names, or any of this metadata as visible text inside the image."
)

OUTPUT_RULES_PROMPT: str = (
    "=== OUTPUT RULES ===\n"
    "- Do NOT render section headers (such as === SYSTEM ROLE === or === CAMPAIGN BRIEF ===) in the image.\n"
    "- Avoid rendering metadata, labels, or variable names as visible text on the image canvas.\n"
    "- Only render textual elements explicitly requested in the text to include instructions."
)

TONE_STYLE_MAP: dict[str, str] = {
    "formal": (
        "Clean, sophisticated, and authoritative. "
        "Use structured layouts and restrained color usage."
    ),
    "casual": (
        "Relaxed and approachable. "
        "Favor organic shapes and warm, inviting compositions."
    ),
    "playful": (
        "Fun, energetic, and vibrant. "
        "Bold colors, dynamic layouts, and expressive elements are encouraged."
    ),
    "professional": (
        "Polished and trustworthy. "
        "Balanced layouts with clear visual hierarchy."
    ),
    "friendly": (
        "Warm, welcoming, and inclusive. "
        "Soft edges, open compositions, and accessible imagery."
    ),
}

PLATFORM_NOTES: dict[str, str] = {
    "instagram_post": (
        "Square 1:1 format. Design should work as a grid tile "
        "— keep key content centered."
    ),
    "instagram_story": (
        "Full-screen vertical format. Place key content in the safe middle 60% "
        "to avoid UI overlaps at top and bottom."
    ),
    "instagram_reel_cover": (
        "Full-screen vertical format. Place key content in the safe middle 60% "
        "to avoid UI overlaps at top and bottom."
    ),
    "facebook_post": (
        "Landscape format. Ensure text and focal elements "
        "are clear at small preview sizes."
    ),
    "facebook_cover": (
        "Ultra-wide banner. Design for horizontal scanning "
        "— no critical content at the extreme edges (may be cropped on mobile)."
    ),
    "facebook_story": (
        "Full-screen vertical format. Place key content in the safe middle 60% "
        "to avoid UI overlaps at top and bottom."
    ),
    "twitter_post": (
        "Landscape format. Ensure text and focal elements "
        "are clear at small preview sizes."
    ),
    "twitter_header": (
        "Ultra-wide banner. Design for horizontal scanning "
        "— no critical content at the extreme edges (may be cropped on mobile)."
    ),
    "linkedin_post": (
        "Landscape format. Ensure text and focal elements "
        "are clear at small preview sizes."
    ),
    "linkedin_banner": (
        "Ultra-wide banner. Design for horizontal scanning "
        "— no critical content at the extreme edges (may be cropped on mobile)."
    ),
    "tiktok_video_cover": (
        "Full-screen vertical format. Place key content in the safe middle 60% "
        "to avoid UI overlaps at top and bottom."
    ),
    "youtube_thumbnail": (
        "Landscape format. Ensure text and focal elements "
        "are clear at small preview sizes."
    ),
    "youtube_banner": (
        "Ultra-wide banner. Design for horizontal scanning "
        "— no critical content at the extreme edges (may be cropped on mobile)."
    ),
}

CAMPAIGN_GOAL_MAP: dict[str, str] = {
    "brand_awareness": "Increase brand awareness and introduce the brand to new audiences.",
    "product_launch": "Communicate a product or service launch.",
    "product_showcase": "Visually showcase product features and qualities.",
    "promotion_offer": "Highlight a promotional offer, discount, or special deal.",
    "sales_conversion": "Drive sales conversions and encourage immediate purchase action.",
    "lead_generation": "Generate leads and invite potential customers to connect or inquire.",
    "engagement": "Drive audience interaction, engagement, and conversation.",
    "education": "Educate the audience with helpful tips, explanations, or insights.",
    "announcement": "Make an important announcement, news update, or event notice.",
    "event_registration": "Promote event registration and attendance.",
    "seasonal_campaign": "Celebrate a seasonal campaign or holiday occasion.",
    "social_proof": "Showcase customer trust, reviews, or social proof.",
}

CONTENT_TYPE_MAP: dict[str, str] = {
    "product_showcase": "Visual product showcase focusing on aesthetic product presentation.",
    "service_showcase": "Service overview emphasizing value and capabilities.",
    "promotional_ad": "Promotional advertisement highlighting compelling offers.",
    "announcement": "Clean announcement layout suitable for news or milestones.",
    "educational": "Informative educational visual simplifying a concept.",
    "testimonial": "Customer testimonial or review highlight layout.",
    "brand_story": "Narrative brand story highlighting identity and values.",
    "event_promo": "Eye-catching event promotional graphic.",
    "seasonal_post": "Themed seasonal graphic tailored to current festivities or seasons.",
    "quote_or_tip": "Inspirational quote or actionable tip graphic.",
    "infographic": "Structured informational visual presenting insights clearly.",
    "social_proof": "Social proof graphic demonstrating community trust and satisfaction.",
}

AUDIENCE_SEGMENT_MAP: dict[str, str] = {
    "general_consumers": "general consumers",
    "small_business_owners": "small business owners",
    "entrepreneurs": "entrepreneurs",
    "marketers_creators": "marketers and content creators",
    "professionals": "professionals and corporate employees",
    "students": "students and young learners",
    "online_shoppers": "online shoppers and e-commerce buyers",
    "beauty_fashion_audience": "fashion and beauty enthusiasts",
    "food_hospitality_audience": "food and hospitality lovers",
    "technology_users": "technology users and tech-savvy individuals",
    "local_community": "the local community",
    "custom": "custom audience",
}

AGE_RANGE_MAP: dict[str, str] = {
    "under_18": "under 18 years old",
    "18_24": "18–24 years old",
    "25_34": "25–34 years old",
    "35_44": "35–44 years old",
    "45_54": "45–54 years old",
    "55_plus": "55+ years old",
    "mixed": "mixed age demographics",
}

GENDER_FOCUS_MAP: dict[str, str] = {
    "all": "all genders",
    "women": "primarily women",
    "men": "primarily men",
    "gender_inclusive": "gender-inclusive audience",
    "custom": "targeted gender audience",
}

VOICE_TONE_MAP: dict[str, str] = {
    "friendly": "Friendly, warm, and approachable.",
    "professional": "Polished, professional, and trustworthy.",
    "playful": "Playful, energetic, and vibrant.",
    "bold": "Bold, striking, and confident.",
    "elegant": "Elegant, luxurious, and sophisticated.",
    "warm": "Warm, human, and inviting.",
    "educational": "Educational, clear, and informative.",
    "inspirational": "Inspirational, uplifting, and visionary.",
    "minimal": "Minimalist, calm, and uncluttered.",
    "trustworthy": "Trustworthy, authentic, and dependable.",
    "youthful": "Youthful, trendy, and dynamic.",
    "urgent": "Urgent, action-oriented, and high-energy.",
}
LANGUAGE_INSTRUCTION_MAP: dict[str, str] = {
    "ar": (
        "Write newly generated campaign copy in Arabic. "
        "Preserve user-provided text exactly as written and do not translate it."
    ),
    "en": (
        "Write newly generated campaign copy in English. "
        "Preserve user-provided text exactly as written and do not translate it."
    ),
}



def build_platform_context(
    preset_id: str, width: int, height: int, aspect_ratio: str
) -> PlatformContext:
    from app.services.presets import PLATFORM_PRESETS

    _, _, label = PLATFORM_PRESETS[preset_id]
    return PlatformContext(
        label=label,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        note=PLATFORM_NOTES[preset_id],
    )


def format_target_audience(target_audience: TargetAudience) -> str:
    parts = []
    if target_audience.segments:
        segment_strs = [
            AUDIENCE_SEGMENT_MAP.get(s.value if hasattr(s, "value") else str(s), str(s))
            for s in target_audience.segments
        ]
        parts.append(f"Demographic: {', '.join(segment_strs)}")
    if target_audience.location:
        parts.append(f"Location/Market: {target_audience.location}")
    if target_audience.age_range and target_audience.age_range.value != "unspecified":
        age_str = AGE_RANGE_MAP.get(target_audience.age_range.value, target_audience.age_range.value)
        parts.append(f"Age group: {age_str}")
    if target_audience.gender_focus and target_audience.gender_focus.value != "unspecified":
        gender_str = GENDER_FOCUS_MAP.get(target_audience.gender_focus.value, target_audience.gender_focus.value)
        parts.append(f"Gender focus: {gender_str}")
    if target_audience.details:
        parts.append(f"Details: {target_audience.details}")
    return " | ".join(parts) if parts else "General audience"


def _resolve_mapped_field(enum_val: Any, custom_val: str | None, mapping_dict: dict[str, str]) -> str:
    """Helper resolving enum key or custom value to a descriptive instruction."""
    key = enum_val.value if hasattr(enum_val, "value") else str(enum_val)
    if key == "custom" and custom_val:
        return custom_val
    return mapping_dict.get(key, key)


def _build_brand_identity_section(brand_context: BrandContext | None) -> str | None:
    """Helper building the === BRAND IDENTITY === prompt layer."""
    if brand_context is None:
        return None

    lines: list[str] = [f"Brand: {brand_context.name}"]
    if brand_context.tagline:
        lines.append(f'Tagline: "{brand_context.tagline}"')
    if brand_context.tone and brand_context.tone in TONE_STYLE_MAP:
        lines.append(f"Visual style: {TONE_STYLE_MAP[brand_context.tone]}")
    if brand_context.industry:
        lines.append(f"Business field: {brand_context.industry} — tailor concepts and recommendations to this industry.")
    if brand_context.audience:
        lines.append(
            f"Target audience: {brand_context.audience} "
            "— design should resonate with this demographic."
        )
    if brand_context.colors:
        lines.append(
            f"Brand colors: {', '.join(brand_context.colors)} "
            "— use these exact user-provided colors as the source of truth for "
            "the visual palette. Build a cohesive hierarchy with one dominant "
            "color, supporting colors, and intentional accents. You may use "
            "carefully derived tints, shades, and neutral backgrounds, but do "
            "not replace, distort, or introduce unrelated hues. Maintain strong "
            "contrast, legibility, color harmony, and professional saturation "
            "across the whole composition."
        )
    if brand_context.avoid_words:
        lines.append(
            "AVOID the following in all visual and textual elements: "
            f"{brand_context.avoid_words}"
        )
    return "=== BRAND IDENTITY ===\n" + "\n".join(lines)


LOGO_PLACEMENT_PROMPT: dict[str, str] = {
    "corner": "Reserve a clean, visually balanced area in a corner for the official logo.",
    "prominent": "Reserve a clear, prominent, uncluttered area for the official logo.",
    "watermark": "Keep a low-detail area suitable for a subtle official watermark.",
    "auto": "Reserve the safest visually balanced area for the official logo.",
}


def _build_logo_section(
    logo_mode: str,
    brand_has_logo: bool,
    logo_placement: str = "none",
) -> str | None:
    """Build instructions for a post-generation exact-logo overlay."""
    placement = logo_placement
    if placement == "none" and logo_mode in ("prompt", "both"):
        # Legacy callers requested a logo in the prompt; use the reliable
        # post-processing path instead of asking the model to redraw it.
        placement = "auto"

    if placement in LOGO_PLACEMENT_PROMPT and brand_has_logo:
        return (
            "=== LOGO PLACEMENT ===\n"
            "The official brand logo will be added after image generation. "
            "Do not generate, draw, recreate, imitate, redesign, replace, "
            "or invent any logo, brand mark, symbol, or fake brand text. "
            f"{LOGO_PLACEMENT_PROMPT[placement]}"
        )
    return None

def _build_trend_section(
    trend_context: dict | None,
) -> str | None:
    if not trend_context:
        return None

    lines = [
        f"Selected trend: {trend_context.get('name', '')}",
    ]

    visual_style = trend_context.get(
        "visual_style"
    ) or []

    if visual_style:
        lines.append("Apply the trend through:")
        lines.extend(
            f"- {item}"
            for item in visual_style
        )

    content_patterns = trend_context.get(
        "content_patterns"
    ) or []

    if content_patterns:
        lines.append("Suggested content patterns:")
        lines.extend(
            f"- {item}"
            for item in content_patterns
        )

    avoid_patterns = trend_context.get(
        "avoid_patterns"
    ) or []

    if avoid_patterns:
        lines.append("Avoid:")
        lines.extend(
            f"- {item}"
            for item in avoid_patterns
        )

    lines.append(
        "The selected trend is optional creative guidance. "
        "It must not override safety rules, brand identity, "
        "user-provided text, or platform constraints."
    )

    return (
        "=== TREND DIRECTION ===\n"
        + "\n".join(lines)
    )

def build_generation_prompt(
    *,
    brief: GenerationBrief,
    brand_context: BrandContext | None,
    platform: PlatformContext,
    logo_mode: str,
    brand_has_logo: bool,
    logo_placement: str = "none",
    product_edit_instruction: str | None = None,
    trend_context: dict | None = None,
) -> str:
    """Deterministic prompt composer combining GenerationBrief with Brand, Platform and Logo rules."""
    sections: list[str] = [SYSTEM_ROLE_PROMPT]

    # Layer 2: Campaign Brief
    brief_lines: list[str] = [
        f"Campaign Goal: {_resolve_mapped_field(brief.campaign_goal, brief.campaign_goal_custom, CAMPAIGN_GOAL_MAP)}",
        f"Content Type: {_resolve_mapped_field(brief.content_type, brief.content_type_custom, CONTENT_TYPE_MAP)}",
        f"Target Audience: {format_target_audience(brief.target_audience)}",
        f"Core Idea: {brief.core_idea}",
        f"Tone & Style: {_resolve_mapped_field(brief.voice_tone, brief.voice_tone_custom, VOICE_TONE_MAP)}",
    ]

    language_instruction = _language_instruction(brief)
   

    if brief.text_to_include:
        brief_lines.append(f'Exact visible text to include; preserve exactly: "{brief.text_to_include}"')

    if brief.optional_notes:
        brief_lines.append(f"Design Notes: {brief.optional_notes}")

    sections.append("=== CAMPAIGN BRIEF ===\n" + "\n".join(brief_lines))

    # Layer 3: Brand identity (conditional)
    brand_sec = _build_brand_identity_section(brand_context)
    if brand_sec:
        sections.append(brand_sec)


    # Layer 4: Composition guidance (always present)
    sections.append(f"=== COMPOSITION ===\n{platform.note}")

    # Layer 5: Logo (conditional)
    logo_sec = _build_logo_section(logo_mode, brand_has_logo, logo_placement)
    if logo_sec:
        sections.append(logo_sec)

    # Layer 6: Product reference instructions
    if product_edit_instruction:
        sections.append(
            "=== PRODUCT IMAGE INSTRUCTIONS ===\n"
            "A product reference image is provided. "
            "Use the same product in the generated design.\n"
            "Preserve the product identity, shape, packaging, "
            "logo, label, and important colors unless the user "
            "explicitly asks to change them.\n"
            f"User product instruction: "
            f"{product_edit_instruction}"
        )
    trend_section = _build_trend_section(trend_context)

    if trend_section:
        sections.append(trend_section)
    

    # Layer 7: Output rules
    sections.append(
        OUTPUT_RULES_PROMPT
        + "\n"
        + language_instruction
    )

    return "\n\n".join(sections)


def compose_full_prompt(
    *,
    user_prompt: str,
    brand_context: BrandContext | None,
    platform: PlatformContext,
    logo_mode: str,
    brand_has_logo: bool,
    logo_placement: str = "none",
) -> str:
    """Legacy compose_full_prompt for backwards compatibility."""
    sections: list[str] = [SYSTEM_ROLE_PROMPT]

    brand_sec = _build_brand_identity_section(brand_context)
    if brand_sec:
        sections.append(brand_sec)

    sections.append(f"=== COMPOSITION ===\n{platform.note}")

    logo_sec = _build_logo_section(logo_mode, brand_has_logo, logo_placement)
    if logo_sec:
        sections.append(logo_sec)

    sections.append(f"=== IMAGE REQUEST ===\n{user_prompt}")

    return "\n\n".join(sections)


def _value(value: object) -> str:
    return getattr(value, "value", value) if value is not None else ""


def _language_instruction(brief: GenerationBrief) -> str:
    language = (
        brief.language.value
        if hasattr(brief.language, "value")
        else str(brief.language)
    )

    if language == "en":
        return "Write newly generated campaign copy in English."

    return "Write newly generated campaign copy in Arabic."


def _mapped(mapping: dict[str, str], value: object, custom: str | None = None) -> str:
    key = _value(value)
    if key == "custom":
        return custom or "Custom"
    return mapping.get(key, key.replace("_", " "))
