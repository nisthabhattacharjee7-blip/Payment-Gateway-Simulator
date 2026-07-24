import uuid 
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, DateTime, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.merchant import Merchant

class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id: Mapped[str] = mapped_column(String, ForeignKey("merchants.id"), nullable=False)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), 
                                                default=lambda: datetime.now(timezone.utc),
                                                            onupdate=lambda: datetime.now(timezone.utc))
    merchant = relationship("Merchant", backref="wallet", uselist=False)    
    

    