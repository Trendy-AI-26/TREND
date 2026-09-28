from uuid import UUID

from pydantic import BaseModel


class AvatarUploadResponse(BaseModel):
    user_id: UUID
    avatar_url: str
    content_type: str
    file_size_bytes: int
    width: int
    height: int
