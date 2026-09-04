from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.settlement import Settlement
from app.models.ledger_entry import LedgerEntry
from app.config.enums import PaymentStatus, SettlementStatus, LedgerEntryType
from app.services import state_machine


def get_unsettled_payments(db: Session, merchant_id: str) -> list[Payment]:
    """
    Finds all of a merchant's payments that have been captured but not
    yet included in any settlement batch.
    """
    return (
        db.query(Payment)
        .filter(
            Payment.merchant_id == merchant_id,
            Payment.status == PaymentStatus.CAPTURED,
            Payment.settlement_id.is_(None),
        )
        .all()
    )


def create_settlement_batch(db: Session, merchant_id: str) -> Settlement:
    """
    Bundles all of a merchant's unsettled captured payments into one
    settlement batch: moves funds from the merchant's wallet ledger
    account to a bank_settlement account, and marks each payment as
    settled. This simulates what a scheduled settlement job would do
    at a real payment processor.
    """
    payments = get_unsettled_payments(db, merchant_id)

    if not payments:
        raise ValueError("No unsettled payments available for this merchant")

    total_amount = sum(p.amount for p in payments)

    settlement = Settlement(
        merchant_id=merchant_id,
        amount=total_amount,
        payment_count=len(payments),
        status=SettlementStatus.PROCESSING,
    )
    db.add(settlement)
    db.flush()

    # One debit/credit pair PER PAYMENT, not one lump pair on payments[0].
    # The old version stamped both entries with payments[0].id regardless
    # of batch size, so every other payment in the batch had zero ledger
    # entries proving it was ever settled — the audit trail silently broke
    # for N-1 of N payments in every multi-payment batch.
    for payment in payments:
        debit_entry = LedgerEntry(
            payment_id=payment.id,
            account="merchant_wallet",
            entry_type=LedgerEntryType.DEBIT,
            amount=payment.amount,
        )
        credit_entry = LedgerEntry(
            payment_id=payment.id,
            account="bank_settlement",
            entry_type=LedgerEntryType.CREDIT,
            amount=payment.amount,
        )
        db.add(debit_entry)
        db.add(credit_entry)

        new_status = state_machine.transition(payment.status, PaymentStatus.SETTLED)
        payment.status = new_status
        payment.settlement_id = settlement.id
        payment.settled_at = datetime.now(timezone.utc)

    settlement.status = SettlementStatus.COMPLETED
    # NOTE: Settlement has no settled_at column (see app/models/settlement.py).
    # The old code did `settlement.settled_at = datetime.now(...)` here, which
    # set a plain Python attribute that SQLAlchemy silently never persisted —
    # it wasn't mapped, so it vanished on the next refresh. If you want this
    # field, add it via an Alembic migration first:
    #   settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    db.flush()
    return settlement