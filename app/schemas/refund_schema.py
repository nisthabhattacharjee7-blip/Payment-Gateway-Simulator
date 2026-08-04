from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.config.enums import RefundStatus

class RefundCreate(BaseModel):
    amount: int = Field(gt=0)
    reason: str | None = None

class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    payment_id: str
    amount: int
    reason: str | None
    status: RefundStatus
    created_at: datetime
    updated_at: datetime    