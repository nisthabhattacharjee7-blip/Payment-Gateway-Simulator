from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import app
from app.db.session import get_db
from app.models.merchant import Merchant
from app.models.payment import Payment
from app.schemas.refund_schema import RefundCreate, RefundResponse
from app.middlewares.auth_middleware import get_current_merchant
from app.services import payment_service
from app.services import webhook_service
from app.services import state_machine
from app.routers.dependencies import get_owned_payment


router = APIRouter(prefix="/payments", tags=["refunds"])


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


@router.post(
    "/{payment_id}/refunds", response_model=RefundResponse, status_code=201
)
async def create_refund(
    payment_id: str,
    payload: RefundCreate,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Issues a full or partial refund against a captured/settled payment.
    """
    payment = _get_owned_payment(db, payment_id, merchant)

    try:
        refund = payment_service.refund_payment(
            db=db,
            payment=payment,
            refund_amount=payload.amount,
            reason=payload.reason,
        )
    except state_machine.InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    db.commit()
    db.refresh(refund)
    db.refresh(payment)

    event_type = f"payment.{payment.status.value}"
    webhook_payload = webhook_service.build_webhook_payload(payment, event_type)
    log = webhook_service.create_webhook_log(db, payment, event_type, webhook_payload)
    db.commit()

    if merchant.webhook_url:
        await webhook_service.send_webhook(log, merchant.webhook_url, merchant.webhook_secret, db)
        db.commit()

    return refund