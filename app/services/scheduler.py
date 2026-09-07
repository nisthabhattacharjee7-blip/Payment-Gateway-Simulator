import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.models.webhook_log import WebhookLog
from app.config.enums import WebhookStatus
from app.services import webhook_service

logger = logging.getLogger(__name__)


async def redrive_due_webhooks(db: Session | None = None) -> None:
   
    """Polls for webhook logs in RETRYING status whose next_retry_at has
    passed, and redrives delivery for each. Accepts an optional db
    session so tests can pass in the same transaction-scoped session
    the test fixture uses — opening a separate SessionLocal() would use
    a different connection and never see uncommitted test data"""
    
    owns_session = db is None
    if owns_session:
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
                log.status = WebhookStatus.FAILED
                log.next_retry_at = None
                continue
            try:
                await webhook_service.send_webhook(
                    log, merchant.webhook_url, merchant.webhook_secret, db
                )
            except Exception:
                logger.exception("Scheduled webhook redrive failed for log %s", log.id)

        if owns_session:
            db.commit()
    finally:
        if owns_session:
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

