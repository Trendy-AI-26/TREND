from datetime import datetime

from pydantic import BaseModel


class CreditBalanceResponse(BaseModel):
    plan: str
    total: int
    reserved: int
    consumed: int
    remaining: int
    period_start: datetime
    period_end: datetime
