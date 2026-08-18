from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.config.enums import SettlementStatus


class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_id: str
    amount: int
    status: SettlementStatus
    payment_count: int
    created_at: datetime
    settled_at: datetime | None