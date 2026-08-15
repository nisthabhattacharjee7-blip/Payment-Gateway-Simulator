from app.models.payment import Payment
from app.models.webhook_log import WebhookStatus 
from app.config.enums import PaymentStatus, Currency, WebhookStatus
from app.services import webhook_service
from app.utils.retry import calculate_backoff_seconds


def _make_payment(db, merchant):
    payment = Payment(
        merchant_id=merchant.id,
        amount=50000,
        currency=Currency.INR,
        status=PaymentStatus.CAPTURED,
    )
    db.add(payment)
    db.flush()
    return payment


def test_build_webhook_payload_has_correct_fields(db, test_merchant):
    payment = _make_payment(db, test_merchant)

    payload = webhook_service.build_webhook_payload(payment, "payment.captured")

    assert payload.event == "payment.captured"
    assert payload.payment_id == payment.id
    assert payload.status == "captured"
    assert payload.amount == 50000


def test_create_webhook_log_starts_pending(db, test_merchant):
    payment = _make_payment(db, test_merchant)
    payload = webhook_service.build_webhook_payload(payment, "payment.captured")

    log = webhook_service.create_webhook_log(db, payment, "payment.captured", payload)

    assert log.status == WebhookStatus.PENDING
    assert log.attempt_count == 0
    assert log.payment_id == payment.id


def test_backoff_increases_with_each_attempt():
    delay_1 = calculate_backoff_seconds(1)
    delay_2 = calculate_backoff_seconds(2)
    delay_3 = calculate_backoff_seconds(3)

    assert delay_1 == 2
    assert delay_2 == 4
    assert delay_3 == 8
    assert delay_2 > delay_1
    assert delay_3 > delay_2


def test_backoff_is_capped_at_max_delay():
    large_attempt_delay = calculate_backoff_seconds(10)
    assert large_attempt_delay == 60


def test_schedule_retry_or_fail_marks_failed_after_max_attempts(db, test_merchant):
    payment = _make_payment(db, test_merchant)
    payload = webhook_service.build_webhook_payload(payment, "payment.captured")
    log = webhook_service.create_webhook_log(db, payment, "payment.captured", payload)

    log.attempt_count = webhook_service.MAX_WEBHOOK_ATTEMPTS

    webhook_service._schedule_retry_or_fail(log)

    assert log.status == WebhookStatus.FAILED
    assert log.next_retry_at is None


def test_schedule_retry_or_fail_schedules_retry_when_attempts_remain(db, test_merchant):
    payment = _make_payment(db, test_merchant)
    payload = webhook_service.build_webhook_payload(payment, "payment.captured")
    log = webhook_service.create_webhook_log(db, payment, "payment.captured", payload)

    log.attempt_count = 1

    webhook_service._schedule_retry_or_fail(log)

    assert log.status == WebhookStatus.RETRYING
    assert log.next_retry_at is not None
    