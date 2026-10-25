"""Build human-readable creative direction from a generation brief."""

from app.models.generation import GenerationBrief
from app.services.prompt_composer import (
    CAMPAIGN_GOAL_MAP,
    CONTENT_TYPE_MAP,
    VOICE_TONE_MAP,
    PLATFORM_NOTES,
    format_target_audience,
    _resolve_mapped_field,
)
from app.services.presets import PLATFORM_PRESETS


def build_creative_direction(
    brief: GenerationBrief,
    brand_name: str,
    platform_preset: str,
    brand_context: dict | None = None,
) -> dict:
    """Translate a raw GenerationBrief into business-friendly creative direction.""" 
    # Resolve mapped fields using the same dictionaries as prompt_composer
    goal = _resolve_mapped_field(
        brief.campaign_goal, brief.campaign_goal_custom, CAMPAIGN_GOAL_MAP
    )
    content = _resolve_mapped_field(
        brief.content_type, brief.content_type_custom, CONTENT_TYPE_MAP
    )
    tone = _resolve_mapped_field(
        brief.voice_tone, brief.voice_tone_custom, VOICE_TONE_MAP
    )
    language = getattr(brief, "language", "ar")
    language = getattr(language, "value", language)
    
    # Audience
    audience = format_target_audience(brief.target_audience)
    
    # Platform
    _, _, label = PLATFORM_PRESETS[platform_preset]
    platform_note = PLATFORM_NOTES.get(platform_preset, "")
    
    # Build structured response
    direction = {
        "language": language,
        "campaign_goal": goal,
        "content_type": content,
        "target_audience": audience,
        "core_idea": brief.core_idea,
        "voice_tone": tone,
        "platform": {
            "name": label,
            "note": platform_note,
        },
    }
    
    if brief.text_to_include:
        direction["text_to_include"] = brief.text_to_include
    
    if brief.optional_notes:
        direction["optional_notes"] = brief.optional_notes
    
    # Brand identity layer
    if brand_context:
        brand_identity = {}
        if brand_context.get("language"):
            brand_identity["language"] = brand_context["language"]
        if brand_context.get("tagline"):
            brand_identity["tagline"] = brand_context["tagline"]
        if brand_context.get("tone"):
            brand_identity["tone"] = brand_context["tone"]
        if brand_context.get("colors"):
            brand_identity["colors"] = brand_context["colors"]
        if brand_context.get("avoid_words"):
            brand_identity["avoid_words"] = brand_context["avoid_words"]
        if brand_identity:
            direction["brand_identity"] = brand_identity
    
    return direction