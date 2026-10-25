from datetime import datetime
from pydantic import BaseModel

class QuotaSummaryResponse(BaseModel):
    plan: str
    max_active_brands: int
    active_brands: int
    generation_limit: int
    generation_reserved: int
    generation_consumed: int
    generation_remaining: int
    daily_generation_limit: int = 3
    daily_generation_reserved: int = 0
    daily_generation_consumed: int = 0
    daily_generation_remaining: int = 3
    trial_ends_at: datetime | None = None
    trial_active: bool = True
