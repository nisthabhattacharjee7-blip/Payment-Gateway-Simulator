import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(String, unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    webhook_url: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                                        onupdate=lambda: datetime.now(timezone.utc))
    webhook_secret: Mapped[str] = mapped_column(String, nullable=True)
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="merchant")
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="merchant", uselist=False)
    webhook_logs: Mapped[list["WebhookLog"]] = relationship("WebhookLog", back_populates="merchant")
    idempotency_keys: Mapped[list["IdempotencyKey"]] = relationship("IdempotencyKey", back_populates="merchant")
    settlements: Mapped[list["Settlement"]] = relationship("Settlement", back_populates="merchant")