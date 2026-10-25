from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _validate_brand_name(v: str) -> str:
    v = v.strip()
    if len(v) < 2 or len(v) > 120:
        raise ValueError("Brand name must be between 2 and 120 characters")
    return v


class CreateBrandRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_brand_name(v)


class UpdateBrandRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_brand_name(v)


class BrandResponse(BaseModel):
    id: str
    name: str
    logo_url: Optional[str] = None
    kit_status: str = "not_started"
    created_at: datetime
    updated_at: datetime


class BrandListItem(BaseModel):
    id: str
    name: str
    logo_url: Optional[str] = None
    kit_status: str = "not_started"
    created_at: datetime
    colors: list[str] = Field(default_factory=list)
    industry: str | None = None
    tagline: str | None = None


class DeleteBrandRequest(BaseModel):
    confirm_name: str


class LogoUploadResponse(BaseModel):
    logo_url: str
