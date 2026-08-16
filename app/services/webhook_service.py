import json
import httpx
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.models.webhook_log import WebhookLog
from app.config.enums import WebhookStatus, WebhookStatus
from app.schemas.webhook_schema import  WebhookPayload
from app.utils.retry import calculate_backoff_seconds
from app.utils.hmac_utils import sign_webhook_payload

MAX_WEBHOOK_ATTEMPTS = 5

def build_webhook_payload(payment, event_type: str) -> WebhookPayload:
    """
    Builds the outbound payload describing a payment event,
    ready to be sent to a merchant's webhook URL"""
    return WebhookPayload(
    event=event_type,
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
    delivery attempt has been made"""
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

async def send_webhook(log: WebhookLog, webhook_url: str, webhook_secret: str, db: Session):
    """
    Attempts to deliver a single webhook. On success, marks it DELIVERED.
    On failure, increments the attempt count and schedules a retry with
    exponential backoff, or marks it permanently FAILED if attempts are
    exhausted"""

    log.attempt_count += 1

    signature = sign_webhook_payload(log.payload, webhook_secret)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                webhook_url,
                content=log.payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                },
            )

        log.response_status_code = response.status_code
        log.response_body = response.text[:1000]

        if 200 <= response.status_code < 300:
            log.status = WebhookStatus.DELIVERED
            log.next_retry_at = None
        else:
            _schedule_retry_or_fail(log)

    except httpx.RequestError as exc:
        log.response_status_code = None
        log.response_body = str(exc)[:1000]
        _schedule_retry_or_fail(log)

    db.flush()

def _schedule_retry_or_fail(log: WebhookLog) -> None:
    """
    Decides whether to schedule another retry attempt or give up,
    based on how many attempts have already been made"""
    if log.attempt_count >= MAX_WEBHOOK_ATTEMPTS:
        log.status = WebhookStatus.FAILED
        log.next_retry_at = None
    else:
        log.status = WebhookStatus.RETRYING
        backoff_seconds = calculate_backoff_seconds(log.attempt_count)
        log.next_retry_at = datetime.now(timezone.utc) + timedelta(
            seconds=backoff_seconds
        )    