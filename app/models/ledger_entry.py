import uuid
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, DateTime, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.config.enums import LedgerEntryType
from app.models.payment import Payment

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id: Mapped[str] = mapped_column(String, ForeignKey("payments.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_type: Mapped[LedgerEntryType] = mapped_column(SAEnum(LedgerEntryType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                default=lambda: datetime.now(timezone.utc))
    payment: Mapped["Payment"] = relationship("Payment", back_populates="ledger_entries")
    