import asyncio
from datetime import datetime, timedelta, timezone

from app.services import webhook_service
from app.services.scheduler import redrive_due_webhooks
from app.config.enums import WebhookStatus

def _make_webhook_log(db, payment, merchant, status, next_retry_at=None):
    payload = webhook_service.build_webhook_payload(payment, "payment.captured")
    log = webhook_service.create_webhook_log(db, payment, "payment.captured", payload)
    log.status = status
    log.next_retry_at = next_retry_at
    db.flush()
    return log

def test_redrive_due_webhooks_picks_up_past_due_retries(db, test_merchant, test_payment):
    log = _make_webhook_log(
        db, test_payment, test_merchant,
        status=WebhookStatus.RETRYING,
        next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    db.commit()
    asyncio.run(redrive_due_webhooks())
    db.refresh(log)

    assert log.attempt_count == 1
    assert log.status in (WebhookStatus.DELIVERED, WebhookStatus.RETRYING, WebhookStatus.FAILED)