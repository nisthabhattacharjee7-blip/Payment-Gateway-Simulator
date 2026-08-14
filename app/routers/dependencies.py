from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.payment import Payment


def get_owned_payment(db: Session, payment_id: str, merchant: Merchant) -> Payment:
    
    """Fetches a payment by id, ensuring it belongs to the authenticated
    merchant. Raises 404 if it doesn't exist or isn't theirs."""

    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if payment is None or payment.merchant_id != merchant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    return payment
