import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKey
from app.config.settings import settings


def hash_request_body(body: dict) -> str:
    """
    Deterministic hash of the request body, used to detect when the same
    Idempotency-Key is reused with a different payload (a client bug or
    a parameter-swap attempt) rather than a genuine retry.
    """
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_idempotency_record(db: Session, merchant_id: str, key: str) -> IdempotencyKey | None:
    return (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.merchant_id == merchant_id, IdempotencyKey.key == key)
        .first()
    )


def create_idempotency_record(
    db: Session,
    merchant_id: str,
    key: str,
    request_path: str,
    request_body: dict,
) -> IdempotencyKey:
    record = IdempotencyKey(
        merchant_id=merchant_id,
        key=key,
        request_path=request_path,
        request_body_hash=hash_request_body(request_body),
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=settings.IDEMPOTENCY_KEY_EXPIRY_HOURS),
    )
    db.add(record)
    db.flush()
    return record


def save_idempotency_response(
    db: Session, record: IdempotencyKey, status_code: int, response_body: dict
) -> None:
    record.response_status_code = status_code
    record.response_body = json.dumps(response_body)
    db.flush()