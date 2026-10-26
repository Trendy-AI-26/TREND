import datetime as dt
import re
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

T = TypeVar("T")


# ------------------------------------------------------------ /admin/stats
# Kept unchanged for compatibility.


class GenerationStatusBreakdown(BaseModel):
    pending: int
    processing: int
    succeeded: int
    failed: int


class GenerationProviderBreakdown(BaseModel):
    openai: int
    gemini: int


class AdminStatsResponse(BaseModel):
    total_accounts: int
    total_brands: int
    total_generations: int
    generations_by_status: GenerationStatusBreakdown
    generations_by_provider: GenerationProviderBreakdown
    generations_last_7d: int
    generations_last_30d: int
    brand_kits_complete: int
    active_provider_keys: int


# ------------------------------------------------------------ shared shapes


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    per_page: int
    total: int


class BrandRef(BaseModel):
    id: str
    name: str


class UserRef(BaseModel):
    id: str
    email: str


class GenerationRow(BaseModel):
    id: str
    status: str
    provider: str
    model: str
    platform_preset: str
    error_code: str | None
    error_message: str | None
    created_at: dt.datetime
    completed_at: dt.datetime | None
    image_url: str | None
    needs_review: bool
    brand: BrandRef
    user: UserRef


# ------------------------------------------------------------ overview


class OverviewUsers(BaseModel):
    total: int
    verified: int
    new_7d: int
    disabled: int


class OverviewBrands(BaseModel):
    total: int
    kits_complete: int


class OverviewGenerations(BaseModel):
    total: int
    today: int
    last_7d: int
    last_30d: int
    succeeded: int
    failed: int
    pending: int
    processing: int
    success_rate_30d: float | None


class OverviewCost(BaseModel):
    credits_charged_30d: int
    estimated_provider_cost_30d: float | None


class DailyPoint(BaseModel):
    date: dt.date
    succeeded: int
    failed: int


class OverviewAttention(BaseModel):
    needs_review: list[GenerationRow]
    recent_failures: list[GenerationRow]


class AdminOverview(BaseModel):
    users: OverviewUsers
    brands: OverviewBrands
    generations: OverviewGenerations
    cost: OverviewCost
    daily: list[DailyPoint]
    attention: OverviewAttention


# ------------------------------------------------------------ users


class QuotaInfo(BaseModel):
    limit: int
    consumed: int
    reserved: int
    remaining: int


class CreditsInfo(BaseModel):
    balance: int
    reserved: int
    available: int


class TodayUsage(BaseModel):
    limit: int
    consumed: int
    reserved: int


class AdminUser(BaseModel):
    id: str
    email: str
    full_name: str | None
    email_verified: bool
    disabled: bool
    is_admin: bool
    created_at: dt.datetime
    trial_ends_at: dt.datetime | None
    brands_count: int
    generations_count: int
    generations_succeeded: int
    quota: QuotaInfo | None
    credits: CreditsInfo | None
    today: TodayUsage | None


class AdminUserBrand(BaseModel):
    id: str
    name: str
    kit_status: str
    generation_count: int
    created_at: dt.datetime


class CreditLedgerEntry(BaseModel):
    id: str
    operation: str
    amount: int
    metadata: dict[str, Any]
    created_at: dt.datetime


class AdminUserDetail(AdminUser):
    brands: list[AdminUserBrand]
    recent_generations: list[GenerationRow]
    credit_ledger: list[CreditLedgerEntry]


class GrantGenerationsRequest(BaseModel):
    amount: Annotated[int, Field(strict=True, ge=1, le=1000)]
    note: Annotated[str | None, Field(max_length=300)] = None

    @field_validator("note")
    @classmethod
    def _blank_note_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ExtendTrialRequest(BaseModel):
    days: Annotated[int, Field(strict=True, ge=1, le=365)]


# ------------------------------------------------------------ brands


class BrandOwner(BaseModel):
    id: str
    email: str
    full_name: str | None


class AdminBrand(BaseModel):
    id: str
    name: str
    owner: BrandOwner
    kit_status: str
    colors_count: int
    has_logo: bool
    generation_count: int
    created_at: dt.datetime


# ------------------------------------------------------------ trends

TrendStatus = Literal["active", "inactive", "expired"]
Score = Annotated[int, Field(strict=True, ge=0, le=100)]

SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")

TREND_LIST_FIELDS = (
    "industry",
    "region",
    "platform",
    "audience",
    "visual_style",
    "content_patterns",
    "keywords",
    "avoid_patterns",
)
# NOT NULL columns: a PATCH may omit them but never set them to null.
TREND_REQUIRED_FIELDS = (
    "name",
    "slug",
    "status",
    "popularity_score",
    "growth_score",
    "relevance_score",
    *TREND_LIST_FIELDS,
)


class Trend(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    category: str | None
    industry: list[str]
    region: list[str]
    platform: list[str]
    audience: list[str]
    visual_style: list[str]
    content_patterns: list[str]
    keywords: list[str]
    avoid_patterns: list[str]
    popularity_score: int
    growth_score: int
    relevance_score: int
    status: str
    source: str | None
    observed_at: dt.datetime | None
    expires_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


def _clean_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name is required")
    return cleaned


def _check_slug(value: str | None) -> str | None:
    if value is None:
        return None
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError("slug must be lowercase letters, digits and hyphens ([a-z0-9-]+)")
    return value


def slugify(name: str) -> str:
    """Best-effort ASCII slug for a create request that omits ``slug``."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


class _TrendFields(BaseModel):
    description: str | None = None
    category: str | None = None
    source: str | None = None
    observed_at: dt.datetime | None = None
    expires_at: dt.datetime | None = None


class TrendCreate(_TrendFields):
    name: str
    slug: str | None = None
    industry: list[str] = Field(default_factory=list)
    region: list[str] = Field(default_factory=list)
    platform: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)
    visual_style: list[str] = Field(default_factory=list)
    content_patterns: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    avoid_patterns: list[str] = Field(default_factory=list)
    popularity_score: Score = 0
    growth_score: Score = 0
    relevance_score: Score = 0
    status: TrendStatus = "active"

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return _clean_name(value)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        return _check_slug(value)

    @model_validator(mode="after")
    def _default_slug(self) -> "TrendCreate":
        if self.slug is None:
            derived = slugify(self.name)
            if not derived:
                raise ValueError("slug is required when the name has no ASCII letters or digits")
            self.slug = derived
        return self


class TrendUpdate(_TrendFields):
    name: str | None = None
    slug: str | None = None
    industry: list[str] | None = None
    region: list[str] | None = None
    platform: list[str] | None = None
    audience: list[str] | None = None
    visual_style: list[str] | None = None
    content_patterns: list[str] | None = None
    keywords: list[str] | None = None
    avoid_patterns: list[str] | None = None
    popularity_score: Score | None = None
    growth_score: Score | None = None
    relevance_score: Score | None = None
    status: TrendStatus | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return _clean_name(value)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        return _check_slug(value)

    @model_validator(mode="after")
    def _no_null_for_required(self) -> "TrendUpdate":
        for field in TREND_REQUIRED_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self

    def changes(self) -> dict[str, Any]:
        """Only the fields the client sent."""
        return {field: getattr(self, field) for field in self.model_fields_set}


# ------------------------------------------------------------ audit log


class AuditLogEntry(BaseModel):
    id: str
    admin_email: str
    action: str
    target_type: str
    target_id: str | None
    details: dict[str, Any]
    created_at: dt.datetime
