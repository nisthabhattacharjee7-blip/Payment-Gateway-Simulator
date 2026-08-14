from app.models.payment import Payment
from app.config.enums import PaymentStatus, Currency, LedgerEntryType
from app.services import ledger_service
from app.models.ledger_entry import LedgerEntry


def _make_captured_payment(db, merchant, amount=50000):
    payment = Payment(
        merchant_id=merchant.id,
        amount=amount,
        currency=Currency.INR,
        status=PaymentStatus.CAPTURED,
    )
    db.add(payment)
    db.flush()
    return payment


def test_record_capture_creates_balanced_ledger_entries(db, test_merchant):
    """
    Capturing a payment should create exactly two ledger entries —
    one debit, one credit — for the same amount.
    """
    payment = _make_captured_payment(db, test_merchant, amount=50000)

    ledger_service.record_capture(db, payment)

    entries = db.query(LedgerEntry).filter(LedgerEntry.payment_id == payment.id).all()

    assert len(entries) == 2

    debit_entries = [e for e in entries if e.entry_type == LedgerEntryType.DEBIT]
    credit_entries = [e for e in entries if e.entry_type == LedgerEntryType.CREDIT]

    assert len(debit_entries) == 1
    assert len(credit_entries) == 1
    assert debit_entries[0].amount == credit_entries[0].amount == 50000


def test_record_capture_updates_wallet_balance(db, test_merchant):
    """
    Capturing a payment should increase the merchant's wallet balance
    by exactly the payment amount.
    """
    payment = _make_captured_payment(db, test_merchant, amount=50000)

    ledger_service.record_capture(db, payment)

    wallet = ledger_service.get_or_create_wallet(db, test_merchant.id)
    assert wallet.balance == 50000


def test_record_refund_reverses_the_ledger_correctly(db, test_merchant):
    """
    A full refund should bring the wallet balance back to zero, and
    the debit/credit accounts should be exactly reversed compared
    to the original capture.
    """
    payment = _make_captured_payment(db, test_merchant, amount=50000)
    ledger_service.record_capture(db, payment)

    ledger_service.record_refund(db, payment, refund_amount=50000)

    wallet = ledger_service.get_or_create_wallet(db, test_merchant.id)
    assert wallet.balance == 0

    entries = db.query(LedgerEntry).filter(LedgerEntry.payment_id == payment.id).all()
    assert len(entries) == 4

    total_debits = sum(e.amount for e in entries if e.entry_type == LedgerEntryType.DEBIT)
    total_credits = sum(e.amount for e in entries if e.entry_type == LedgerEntryType.CREDIT)
    assert total_debits == total_credits


def test_partial_refund_leaves_correct_remaining_balance(db, test_merchant):
    """
    A partial refund should reduce the wallet balance by exactly the
    refunded amount, leaving the rest intact.
    """
    payment = _make_captured_payment(db, test_merchant, amount=100000)
    ledger_service.record_capture(db, payment)

    ledger_service.record_refund(db, payment, refund_amount=30000)

    wallet = ledger_service.get_or_create_wallet(db, test_merchant.id)
    assert wallet.balance == 70000