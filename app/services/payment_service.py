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


def capture_payment(db: Session, payment: Payment) -> Payment:

    """
    Captures a previously authorized payment: moves it to CAPTURED
    and records the corresponding double-entry ledger transaction.
    """

    new_status = state_machine.transition(payment.status, PaymentStatus.CAPTURED)
    payment.status = new_status

    ledger_service.record_capture(db, payment)

    db.flush()
    return payment