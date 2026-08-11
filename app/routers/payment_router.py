from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.merchant import Merchant
from app.models.payment import Payment
from app.schemas.payment_schema import PaymentCreate, PaymentResponse
from app.middlewares.auth_middleware import get_current_merchant
from app.services import payment_service
from app.services import webhook_service
from app.services import state_machine

router = APIRouter(prefix="/payments", tags=["payments"])


def _get_owned_payment(db: Session, payment_id: str, merchant: Merchant) -> Payment:
    """
    Fetches a payment by id, ensuring it belongs to the authenticated
    merchant. Raises 404 if it doesn't exist or isn't theirs.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if payment is None or payment.merchant_id != merchant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    return payment


@router.post("", response_model=PaymentResponse, status_code=201)
def create_payment(
    payload: PaymentCreate,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Creates a new payment in the CREATED state for the authenticated merchant.
    """
    payment = payment_service.create_payment(
        db=db,
        merchant_id=merchant.id,
        amount=payload.amount,
        currency=payload.currency,
        receipt=payload.receipt,
        description=payload.description,
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Fetches a single payment belonging to the authenticated merchant.
    """
    return _get_owned_payment(db, payment_id, merchant)


@router.post("/{payment_id}/authorize", response_model=PaymentResponse)
def authorize_payment(
    payment_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Sends the payment to the (simulated) bank for authorization.
    """
    payment = _get_owned_payment(db, payment_id, merchant)

    try:
        payment = payment_service.authorize_payment(db, payment)
    except state_machine.InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    db.commit()
    db.refresh(payment)

    event_type = f"payment.{payment.status.value}"
    webhook_payload = webhook_service.build_webhook_payload(payment, event_type)
    webhook_service.create_webhook_log(db, payment, event_type, webhook_payload)
    db.commit()

    return payment


@router.post("/{payment_id}/capture", response_model=PaymentResponse)
def capture_payment(
    payment_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Captures a previously authorized payment and records the ledger entry.
    """
    payment = _get_owned_payment(db, payment_id, merchant)

    try:
        payment = payment_service.capture_payment(db, payment)
    except state_machine.InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    db.commit()
    db.refresh(payment)

    event_type = f"payment.{payment.status.value}"
    webhook_payload = webhook_service.build_webhook_payload(payment, event_type)
    webhook_service.create_webhook_log(db, payment, event_type, webhook_payload)
    db.commit()

    return payment