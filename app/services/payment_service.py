from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.refund import Refund
from app.config.enums import PaymentStatus, Currency
from app.services import state_machine
from app.services import ledger_service
from app.services.processor_simulator import (
    simulate_bank_authorization,
    ProcessorTimeoutError,
)


def create_payment(
    db: Session,
    merchant_id: str,
    amount: int,
    currency: Currency,
    receipt: str | None = None,
    description: str | None = None,
) -> Payment:
    
    """
    Creates a new payment in the CREATED state. Does not talk to the
    processor yet, that happens in a separate authorize_payment call.
    """
    payment = Payment(
        merchant_id=merchant_id,
        amount=amount,
        currency=currency,
        receipt=receipt,
        description=description,
        status=PaymentStatus.CREATED,
    )
    db.add(payment)
    db.flush()
    return payment


def authorize_payment(db: Session, payment: Payment) -> Payment:
    """
    Sends the payment to the (simulated) bank for authorization.
    On success, moves it to AUTHORIZED. On decline, moves it to FAILED.
    On timeout, leaves the payment status untouched.The outcome is
    unknown, and it's not safe to assume either success or failure.
    """

    try:
        outcome = simulate_bank_authorization(payment.amount)
    except ProcessorTimeoutError:
        return payment

    new_status = state_machine.transition(payment.status, outcome)
    payment.status = new_status
    db.flush()
    return payment


def capture_payment(db: Session, payment: Payment, amount: int | None = None) -> Payment:
    """
    Captures a previously authorized payment: moves it to CAPTURED
    and records the corresponding double-entry ledger transaction.

    amount defaults to the full authorized amount (payment.amount) if
    not provided. A partial capture (amount < payment.amount) is
    allowed exactly once — this is a single-capture model, not
    multi-capture: whatever isn't captured now is never captured later.
    """
    capture_amount = amount if amount is not None else payment.amount

    if capture_amount > payment.amount:
        raise ValueError(
            f"Capture amount {capture_amount} exceeds authorized amount {payment.amount}"
        )

    new_status = state_machine.transition(payment.status, PaymentStatus.CAPTURED)
    payment.status = new_status
    payment.captured_amount = capture_amount

    ledger_service.record_capture(db, payment, capture_amount)

    db.flush()
    return payment

def refund_payment(
    db: Session, payment: Payment, refund_amount: int, reason: str | None = None
) -> Refund:
    """
    Processes a full or partial refund against a captured/settled payment.
    Updates the payment's status appropriately and records the reversing
    ledger transaction.
    """
    already_refunded = sum(r.amount for r in payment.refunds)
    remaining_refundable = (payment.captured_amount or payment.amount) - already_refunded

    if refund_amount > remaining_refundable:
        raise ValueError(
            f"Refund amount {refund_amount} exceeds remaining refundable "
            f"amount {remaining_refundable}"
        )

    if refund_amount == remaining_refundable:
        target_status = PaymentStatus.REFUNDED
    else:
        target_status = PaymentStatus.PARTIALLY_REFUNDED

    new_status = state_machine.transition(payment.status, target_status)
    payment.status = new_status

    refund = Refund(
        payment_id=payment.id,
        amount=refund_amount,
        reason=reason,
    )
    db.add(refund)

    ledger_service.record_refund(db, payment, refund_amount)

    db.flush()
    return refund