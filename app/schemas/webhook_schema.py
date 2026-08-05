from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.config.enums import WebhookStatus 

class WebhookLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    payment_id: str
    merchant_id: str
    event: str
    status: WebhookStatus
    attempt_count: int
    response_status_code: int | None
    next_attempt_at: datetime | None
    payload: dict
    created_at: datetime
    updated_at: datetime

class WebhookPayload(BaseModel):
    event: str
    payment_id: str
    merchant_id: str
    status: WebhookStatus
    amount: int
    currency: str
    payload: dict
    timestamp: datetime
    


