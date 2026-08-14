import pytest

from app.models.payment import Payment
from app.config.enums import PaymentStatus, Currency
from app.services import state_machine, payment_service


def test_valid_transition_created_to_authorized():
    assert state_machine.can_transition(PaymentStatus.CREATED, PaymentStatus.AUTHORIZED)


def test_invalid_transition_created_to_settled():
    assert not state_machine.can_transition(PaymentStatus.CREATED, PaymentStatus.SETTLED)


def test_transition_raises_on_illegal_move():
    with pytest.raises(state_machine.InvalidTransitionError):
        state_machine.transition(PaymentStatus.FAILED, PaymentStatus.CAPTURED)


def test_terminal_states_have_no_valid_transitions():
    assert state_machine.TRANSITIONS[PaymentStatus.FAILED] == set()
    assert state_machine.TRANSITIONS[PaymentStatus.REFUNDED] == set()


def test_create_payment_starts_at_created_status(db, test_merchant):
    payment = payment_service.create_payment(
        db=db,
        merchant_id=test_merchant.id,
        amount=50000,
        currency=Currency.INR,
    )
    assert payment.status == PaymentStatus.CREATED
    assert payment.amount == 50000


def test_capture_payment_requires_authorized_status(db, test_merchant):
    payment = Payment(
        merchant_id=test_merchant.id,
        amount=50000,
        currency=Currency.INR,
        status=PaymentStatus.CREATED,
    )
    db.add(payment)
    db.flush()

    with pytest.raises(state_machine.InvalidTransitionError):
        payment_service.capture_payment(db, payment)


def test_capture_payment_succeeds_from_authorized(db, test_merchant):
    payment = Payment(
        merchant_id=test_merchant.id,
        amount=50000,
        currency=Currency.INR,
        status=PaymentStatus.AUTHORIZED,
    )
    db.add(payment)
    db.flush()

    result = payment_service.capture_payment(db, payment)
    assert result.status == PaymentStatus.CAPTURED


def test_refund_amount_cannot_exceed_payment_amount(db, test_merchant):
    payment = Payment(
        merchant_id=test_merchant.id,
        amount=50000,
        currency=Currency.INR,
        status=PaymentStatus.CAPTURED,
    )
    db.add(payment)
    db.flush()

    with pytest.raises(ValueError):
        payment_service.refund_payment(db, payment, refund_amount=60000)


def test_full_refund_moves_payment_to_refunded_status(db, test_merchant):
    payment = Payment(
        merchant_id=test_merchant.id,
        amount=50000,
        currency=Currency.INR,
        status=PaymentStatus.CAPTURED,
    )
    db.add(payment)
    db.flush()

    payment_service.refund_payment(db, payment, refund_amount=50000)
    assert payment.status == PaymentStatus.REFUNDED


def test_partial_refund_moves_payment_to_partially_refunded_status(db, test_merchant):
    payment = Payment(
        merchant_id=test_merchant.id,
        amount=50000,
        currency=Currency.INR,
        status=PaymentStatus.CAPTURED,
    )
    db.add(payment)
    db.flush()

    payment_service.refund_payment(db, payment, refund_amount=20000)
    assert payment.status == PaymentStatus.PARTIALLY_REFUNDED