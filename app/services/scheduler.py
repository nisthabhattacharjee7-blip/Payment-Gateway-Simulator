import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import SessionLocal
from app.models.webhook_log import WebhookLog
from app.config.enums import WebhookStatus
from app.services import webhook_service

logger = logging.getLogger(__name__)


async def redrive_due_webhooks() -> None:
   
    """Polls for webhook logs in RETRYING status whose next_retry_at has
    passed, and redrives delivery for each — the automated equivalent
    of a merchant hitting POST /webhooks/{id}/retry.

    This is what closes the previously-documented limitation that
    webhook retries only fired when someone manually called the retry
    endpoint. Runs on its own DB session per tick, since this executes
    outside any request lifecycle and can't reuse a request-scoped session"""
    
    db = SessionLocal()
    try:
        due_logs = (
            db.query(WebhookLog)
            .filter(
                WebhookLog.status == WebhookStatus.RETRYING,
                WebhookLog.next_retry_at <= datetime.now(timezone.utc),
            )
            .all()
        )

        for log in due_logs:
            merchant = log.merchant
            if not merchant.webhook_url:
                # Merchant removed their webhook_url after the log was
                # created — nowhere to deliver to, so mark it FAILED
                # instead of leaving it stuck retrying forever.
                log.status = WebhookStatus.FAILED
                log.next_retry_at = None
                continue

            try:
                await webhook_service.send_webhook(
                    log, merchant.webhook_url, merchant.webhook_secret, db
                )
            except Exception:
                # A single delivery failure must not crash the whole
                # scheduler tick — log it and let this entry's own
                # backoff/max-attempt logic (already inside send_webhook)
                # handle the retry state.
                logger.exception("Scheduled webhook redrive failed for log %s", log.id)

        db.commit()
    finally:
        db.close()


scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    scheduler.add_job(
        redrive_due_webhooks,
        trigger="interval",
        seconds=30,
        id="redrive_due_webhooks",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)