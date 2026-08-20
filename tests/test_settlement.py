import pytest

from app.models.payment import Payment
from app.models.ledger_entry import LedgerEntry
from app.config.enums import PaymentStatus, Currency, SettlementStatus, LedgerEntryType
from app.services import settlement_service


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


def test_create_settlement_batch_raises_when_no_unsettled_payments(db, test_merchant):
    with pytest.raises(ValueError):
        settlement_service.create_settlement_batch(db, test_merchant.id)


def test_settlement_moves_payment_to_settled_status(db, test_merchant):
    payment = _make_captured_payment(db, test_merchant, amount=50000)

    settlement_service.create_settlement_batch(db, test_merchant.id)

    assert payment.status == PaymentStatus.SETTLED


def test_settlement_sets_settlement_id_and_settled_at(db, test_merchant):
    payment = _make_captured_payment(db, test_merchant, amount=50000)

    settlement = settlement_service.create_settlement_batch(db, test_merchant.id)

    assert payment.settlement_id == settlement.id
    assert payment.settled_at is not None


def test_settlement_amount_equals_sum_of_payments(db, test_merchant):
    _make_captured_payment(db, test_merchant, amount=30000)
    _make_captured_payment(db, test_merchant, amount=70000)

    settlement = settlement_service.create_settlement_batch(db, test_merchant.id)

    assert settlement.amount == 100000
    assert settlement.payment_count == 2


def test_settlement_status_is_completed(db, test_merchant):
    _make_captured_payment(db, test_merchant, amount=50000)

    settlement = settlement_service.create_settlement_batch(db, test_merchant.id)

    assert settlement.status == SettlementStatus.COMPLETED


def test_settlement_ledger_entries_are_balanced(db, test_merchant):
    payment = _make_captured_payment(db, test_merchant, amount=50000)

    settlement_service.create_settlement_batch(db, test_merchant.id)

    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.payment_id == payment.id)
        .all()
    )

    total_debits = sum(e.amount for e in entries if e.entry_type == LedgerEntryType.DEBIT)
    total_credits = sum(e.amount for e in entries if e.entry_type == LedgerEntryType.CREDIT)

    assert total_debits == total_credits


def test_already_settled_payment_is_excluded_from_next_batch(db, test_merchant):
    payment = _make_captured_payment(db, test_merchant, amount=50000)
    settlement_service.create_settlement_batch(db, test_merchant.id)

    with pytest.raises(ValueError):
        settlement_service.create_settlement_batch(db, test_merchant.id)


def test_get_unsettled_payments_only_returns_captured_and_unsettled(db, test_merchant):
    unsettled = _make_captured_payment(db, test_merchant, amount=50000)
    created_payment = Payment(
        merchant_id=test_merchant.id,
        amount=20000,
        currency=Currency.INR,
        status=PaymentStatus.CREATED,
    )
    db.add(created_payment)
    db.flush()

    result = settlement_service.get_unsettled_payments(db, test_merchant.id)

    assert len(result) == 1
    assert result[0].id == unsettled.id