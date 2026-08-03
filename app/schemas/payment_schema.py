from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.config.enums import PaymentStatus, Currency

class PaymentCreate(BaseModel):
    amount: int = Field( gt=0)
    currency: Currency = Currency.INR
    receipt: str | None = None
    description: str | None = None

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    merchant_id: str
    amount: int
    currency: Currency
    receipt: str | None = None
    description: str | None = None
    status: PaymentStatus
    created_at: datetime    
    updated_at: datetime

class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus