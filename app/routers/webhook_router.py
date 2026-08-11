from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.merchant import Merchant
from app.models.webhook_log import WebhookLog
from app.schemas.webhook_schema import WebhookLogResponse
from app.middlewares.auth_middleware import get_current_merchant
from app.services import webhook_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("", response_model=list[WebhookLogResponse])
def list_webhook_logs(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Lists all webhook delivery attempts belonging to the authenticated merchant.
    """
    logs = (
        db.query(WebhookLog)
        .filter(WebhookLog.merchant_id == merchant.id)
        .order_by(WebhookLog.created_at.desc())
        .all()
    )
    return logs


@router.post("/{webhook_log_id}/retry", response_model=WebhookLogResponse)
async def retry_webhook(
    webhook_log_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Manually triggers a delivery attempt for a specific webhook log.
    """
    log = db.query(WebhookLog).filter(WebhookLog.id == webhook_log_id).first()

    if log is None or log.merchant_id != merchant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook log not found"
        )

    if not merchant.webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merchant has no webhook_url configured",
        )

    await webhook_service.attempt_delivery(db, log, merchant.webhook_url)
    db.commit()
    db.refresh(log)
    return log