from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.generation import GenerationBrief


class TrendRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: GenerationBrief
    platform_preset: str


class TrendRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trend_id: UUID
    trend_name: str
    match_score: int = Field(ge=0, le=100)
    reason: str
    how_to_apply: list[str]
    risks: list[str]


class TrendRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendations: list[TrendRecommendation]
    best_trend_id: UUID | None = None


class TrendRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: UUID
    name: str
    slug: str
    description: str | None = None
    category: str | None = None

    industry: list[str] = Field(default_factory=list)
    region: list[str] = Field(default_factory=list)
    platform: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)

    visual_style: list[str] = Field(default_factory=list)
    content_patterns: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    avoid_patterns: list[str] = Field(default_factory=list)

    popularity_score: int = Field(default=0, ge=0, le=100)
    growth_score: int = Field(default=0, ge=0, le=100)
    relevance_score: int = Field(default=0, ge=0, le=100)

    status: str = "active"
    source: str | None = None
    expires_at: str | None = None
