import json
import httpx
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.models.webhook_log import WebhookLog
from app.config.enums import WebhookStatus, Webhookstatus
from app.schemas.webhook_schema import  WebhookPayload
from app.utils.retry import calculate_backoff_seconds

MAX_WEBHOOK_ATTEMPTS = 5

def build_webhook_payload(payment, event_type: str) -> WebhookPayload:
    """
    Builds the outbound payload describing a payment event,
    ready to be sent to a merchant's webhook URL.
    """
    return WebhookPayload(
        event_type=event_type,
        payment_id=payment.id,
        merchant_id=payment.merchant_id,
        status=payment.status.value,
        amount=payment.amount,
        currency=payment.currency.value,
        timestamp=datetime.now(timezone.utc),
    )


def create_webhook_log(
    db: Session, payment, event_type: str, payload: WebhookPayload
) -> WebhookLog:
    """
    Creates a new webhook log entry in PENDING status, before any
    delivery attempt has been made.
    """
    log = WebhookLog(
        payment_id=payment.id,
        merchant_id=payment.merchant_id,
        event_type=event_type,
        payload=payload.model_dump_json(),
        status=WebhookStatus.PENDING,
        attempt_count=0,
    )
    db.add(log)
    db.flush()
    return log
