from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand_id: UUID
    image_url: str
    content_type: str
    file_size_bytes: int
    width: int
    height: int
    created_at: datetime


class ProductAssetUploadResponse(ProductAssetResponse):
    pass
