from pydantic import BaseModel


class QuotaSummaryResponse(BaseModel):
    plan: str
    max_active_brands: int
    active_brands: int
    generation_limit: int
    generation_reserved: int
    generation_consumed: int
    generation_remaining: int
