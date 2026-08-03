from datetime import datetime
from pydantic import BaseModel , ConfigDict , Emailstr


class MerchantCreate(BaseModel):
    name: str
    email: Emailstr
    webhook_url: str  | None = None

class MerchantResponse(MerchantCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    api_key: str
    email: Emailstr
    webhook_url: str | None
    created_at: datetime
    updated_at: datetime
