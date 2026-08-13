from sqlalchemy.orm import Session
from app.db import session
from app.models.ledger_entry import LedgerEntry
from app.models.wallet import Wallet
from app.config.enums import LedgerEntryType


def get_or_create_wallet(db: Session, merchant_id: str):
    """
    Fetches a merchant's wallet, creating one with a zero balance
    if it doesn't already exist.
    """
    wallet =db.query(Wallet).filter_by(merchant_id=merchant_id).first()
    if not wallet:
        wallet = Wallet(merchant_id=merchant_id)
        db.add(wallet)
        db.flush()
    return wallet


def record_capture(db: Session, payment) -> None:
    """
    Records a captured payment as a double-entry ledger transaction:
    debits the customer_holding account, credits the merchant's wallet.
    Updates the merchant's cached wallet balance to match.
    """
    debit_entry = LedgerEntry(
        payment_id=payment.id,
        account="customer_holding",
        entry_type=LedgerEntryType.DEBIT,
        amount=payment.amount,
    )

    credit_entry = LedgerEntry(
        payment_id=payment.id,
        account="merchant_wallet",
        entry_type=LedgerEntryType.CREDIT,
        amount=payment.amount,
    )

    db.add(debit_entry)
    db.add(credit_entry)

    wallet = get_or_create_wallet(db, payment.merchant_id)
    wallet.balance += payment.amount

    db.flush()


def record_refund(db: Session, payment, refund_amount: int) -> None:
    """
    Records a refund as a reversing double-entry transaction:
    debits the merchant's wallet, credits the customer_holding account.
    Updates the merchant's cached wallet balance to match.
    """
    debit_entry = LedgerEntry(
        payment_id=payment.id,
        account="merchant_wallet",
        entry_type=LedgerEntryType.DEBIT,
        amount=refund_amount,
    )

    credit_entry = LedgerEntry(
        payment_id=payment.id,
        account="customer_holding",
        entry_type=LedgerEntryType.CREDIT,
        amount=refund_amount,
    )

    db.add(debit_entry)
    db.add(credit_entry)

    wallet = get_or_create_wallet(db, payment.merchant_id)
    wallet.balance -= refund_amount

    db.flush()    
