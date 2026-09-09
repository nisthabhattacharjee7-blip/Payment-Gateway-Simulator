from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.config.enums import PaymentStatus, Currency

class PaymentCreate(BaseModel):
    amount: int = Field(gt=0)
    currency: Currency = Currency.INR
    receipt: str | None = None
    description: str | None = None

class PaymentCaptureRequest(BaseModel):
    """
    Optional capture amount. If omitted (or the body is omitted
    entirely), the full authorized amount is captured — this preserves
    existing behavior for any client that doesn't know about partial
    capture yet.
    """
    amount: int | None = Field(default=None, gt=0)

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    merchant_id: str
    amount: int
    captured_amount: int | None = None
    currency: Currency
    receipt: str | None = None
    description: str | None = None
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime

class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus