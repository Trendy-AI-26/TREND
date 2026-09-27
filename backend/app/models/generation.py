# D:\Level4\Trend\backend\app\models\generation.py

from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class ProviderEnum(str, Enum):
    openai = "openai"
    gemini = "gemini"

class TextLanguageEnum(str, Enum):
    en = "en"
    ar = "ar"

class LogoModeEnum(str, Enum):
    none = "none"
    prompt = "prompt"
    watermark = "watermark"
    both = "both"


class GenerationStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"


class PlatformPresetEnum(str, Enum):
    instagram_post = "instagram_post"
    instagram_story = "instagram_story"
    instagram_reel_cover = "instagram_reel_cover"
    facebook_post = "facebook_post"
    facebook_cover = "facebook_cover"
    facebook_story = "facebook_story"
    twitter_post = "twitter_post"
    twitter_header = "twitter_header"
    linkedin_post = "linkedin_post"
    linkedin_banner = "linkedin_banner"
    tiktok_video_cover = "tiktok_video_cover"
    youtube_thumbnail = "youtube_thumbnail"
    youtube_banner = "youtube_banner"





class GenerationResponse(BaseModel):
    id: str
    prompt: str
    provider: ProviderEnum
    model: str
    platform_preset: PlatformPresetEnum
    language: TextLanguageEnum
    width: int
    height: int
    logo_mode: LogoModeEnum
    status: GenerationStatusEnum
    image_url: str | None
    download_filename: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class GenerationHistoryStatusEnum(str, Enum):
    succeeded = "succeeded"
    failed = "failed"


class GenerationHistoryItem(BaseModel):
    id: str
    prompt_excerpt: str
    provider: ProviderEnum
    model: str
    platform_preset: PlatformPresetEnum
    language: TextLanguageEnum
    width: int
    height: int
    logo_mode: LogoModeEnum
    status: GenerationHistoryStatusEnum
    image_url: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class GenerationHistoryPage(BaseModel):
    items: list[GenerationHistoryItem]
    next_cursor: str | None
    page_size: Literal[24]


class GenerationDetailResponse(BaseModel):
    id: str
    prompt: str
    provider: ProviderEnum
    model: str
    platform_preset: PlatformPresetEnum
    language: TextLanguageEnum
    width: int
    height: int
    logo_mode: LogoModeEnum
    status: GenerationHistoryStatusEnum
    provider_request_id: str | None
    image_url: str | None
    download_filename: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class CampaignGoalEnum(str, Enum):
    brand_awareness = "brand_awareness"
    product_launch = "product_launch"
    product_showcase = "product_showcase"
    promotion_offer = "promotion_offer"
    sales_conversion = "sales_conversion"
    lead_generation = "lead_generation"
    engagement = "engagement"
    education = "education"
    announcement = "announcement"
    event_registration = "event_registration"
    seasonal_campaign = "seasonal_campaign"
    social_proof = "social_proof"
    custom = "custom"


class ContentTypeEnum(str, Enum):
    product_showcase = "product_showcase"
    service_showcase = "service_showcase"
    promotional_ad = "promotional_ad"
    announcement = "announcement"
    educational = "educational"
    testimonial = "testimonial"
    brand_story = "brand_story"
    event_promo = "event_promo"
    seasonal_post = "seasonal_post"
    quote_or_tip = "quote_or_tip"
    infographic = "infographic"
    social_proof = "social_proof"
    custom = "custom"


class AudienceSegmentEnum(str, Enum):
    general_consumers = "general_consumers"
    small_business_owners = "small_business_owners"
    entrepreneurs = "entrepreneurs"
    marketers_creators = "marketers_creators"
    professionals = "professionals"
    students = "students"
    online_shoppers = "online_shoppers"
    beauty_fashion_audience = "beauty_fashion_audience"
    food_hospitality_audience = "food_hospitality_audience"
    technology_users = "technology_users"
    local_community = "local_community"
    custom = "custom"


class AgeRangeEnum(str, Enum):
    under_18 = "under_18"
    age_18_24 = "18_24"
    age_25_34 = "25_34"
    age_35_44 = "35_44"
    age_45_54 = "45_54"
    age_55_plus = "55_plus"
    mixed = "mixed"
    unspecified = "unspecified"


class GenderFocusEnum(str, Enum):
    all = "all"
    women = "women"
    men = "men"
    gender_inclusive = "gender_inclusive"
    custom = "custom"
    unspecified = "unspecified"


class VoiceToneEnum(str, Enum):
    friendly = "friendly"
    professional = "professional"
    playful = "playful"
    bold = "bold"
    elegant = "elegant"
    warm = "warm"
    educational = "educational"
    inspirational = "inspirational"
    minimal = "minimal"
    trustworthy = "trustworthy"
    youthful = "youthful"
    urgent = "urgent"
    custom = "custom"


class TargetAudience(BaseModel):
    @field_validator("segments")
    @classmethod
    def validate_segments(
        cls,
        value: list[AudienceSegmentEnum],
    ) -> list[AudienceSegmentEnum]:
        if not value:
            raise ValueError("segments must contain at least one audience segment")

        if len(value) != len(set(value)):
            raise ValueError("segments must not contain duplicates")

        return value

    @field_validator("location", "details", mode="before")
    @classmethod
    def normalize_audience_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_custom_audience(self) -> "TargetAudience":
        has_custom_segment = AudienceSegmentEnum.custom in self.segments
        has_custom_gender = self.gender_focus == GenderFocusEnum.custom

        if (has_custom_segment or has_custom_gender) and (
            self.details is None or len(self.details) < 3
        ):
            raise ValueError(
                "details must contain at least 3 characters when a custom audience "
                "segment or gender focus is selected"
            )

        return self
    segments: list[AudienceSegmentEnum] = Field(
        default_factory=list,
        max_length=3,
    )
    location: str | None = Field(default=None, max_length=100)
    age_range: AgeRangeEnum | None = None
    gender_focus: GenderFocusEnum | None = None
    details: str | None = Field(default=None, max_length=1000)


class GenerationBrief(BaseModel):
    language: TextLanguageEnum = TextLanguageEnum.ar
    @field_validator(
        "campaign_goal_custom",
        "content_type_custom",
        "voice_tone_custom",
        "optional_notes",
        "text_to_include",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None

    @field_validator("core_idea", mode="before")
    @classmethod
    def normalize_core_idea(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator(
        "campaign_goal_custom",
        "content_type_custom",
        "voice_tone_custom",
    )
    @classmethod
    def validate_custom_text_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 3:
            raise ValueError("custom text must contain at least 3 characters")
        return value



    campaign_goal: CampaignGoalEnum
    campaign_goal_custom: str | None = Field(default=None, max_length=300)
    content_type: ContentTypeEnum
    content_type_custom: str | None = Field(default=None, max_length=300)
    target_audience: TargetAudience
    core_idea: str = Field(..., min_length=3, max_length=1000)
    voice_tone: VoiceToneEnum
    voice_tone_custom: str | None = Field(default=None, max_length=300)
    optional_notes: str | None = Field(default=None, max_length=2000)
    text_to_include: str | None = Field(default=None, max_length=500)


    @model_validator(mode="after")
    def validate_custom_fields(self) -> "GenerationBrief":
        self._validate_custom_pair(
            selected=self.campaign_goal,
            custom_value=self.campaign_goal_custom,
            custom_enum=CampaignGoalEnum.custom,
            field_name="campaign_goal_custom",
        )
        self._validate_custom_pair(
            selected=self.content_type,
            custom_value=self.content_type_custom,
            custom_enum=ContentTypeEnum.custom,
            field_name="content_type_custom",
        )
        self._validate_custom_pair(
            selected=self.voice_tone,
            custom_value=self.voice_tone_custom,
            custom_enum=VoiceToneEnum.custom,
            field_name="voice_tone_custom",
        )
        return self

    @staticmethod
    def _validate_custom_pair(
        *,
        selected: object,
        custom_value: str | None,
        custom_enum: object,
        field_name: str,
    ) -> None:
        is_custom = selected == custom_enum

        if is_custom and custom_value is None:
            raise ValueError(
                f"{field_name} is required when the selected value is custom"
            )

        if not is_custom and custom_value is not None:
            raise ValueError(
                f"{field_name} must be null when the selected value is not custom"
            )
        
class PreviewBriefRequest(BaseModel):
    brief: GenerationBrief
    platform_preset: PlatformPresetEnum

class GenerateRequest(BaseModel):
    brief: GenerationBrief
    provider: ProviderEnum
    platform_preset: PlatformPresetEnum
    logo_mode: LogoModeEnum = LogoModeEnum.none


__all__ = [
    "ProviderEnum",
    "TextLanguageEnum",
    "LogoModeEnum",
    "GenerationStatusEnum",
    "PlatformPresetEnum",
    "GenerateRequest",
    "GenerationResponse",
    "GenerationHistoryStatusEnum",
    "GenerationHistoryItem",
    "GenerationHistoryPage",
    "GenerationDetailResponse",
    "CampaignGoalEnum",
    "ContentTypeEnum",
    "AudienceSegmentEnum",
    "AgeRangeEnum",
    "GenderFocusEnum",
    "VoiceToneEnum",
    "TargetAudience",
    "GenerationBrief",
]
