import uuid 
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, Integer, DateTime, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.merchant import Merchant

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    merchant_id: Mapped[str] = mapped_column(String, ForeignKey("merchants.id"), nullable=False)
    request_path : Mapped[str] = mapped_column(String, nullable=False)
    request_body_hash: Mapped[str] = mapped_column(String, nullable=False)
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="idempotency_keys")
