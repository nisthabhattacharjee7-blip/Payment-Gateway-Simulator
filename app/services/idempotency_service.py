import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKey


IDEMPOTENCY_KEY_EXPIRY_HOURS = 24


def hash_request_body(body: dict) -> str:
    """
    Produces a consistent SHA-256 hash of a request body,
    used to detect if a key is being reused for a different request.
    """
    normalized_body = json.dumps(body, sort_keys=True)
    return hashlib.sha256(normalized_body.encode()).hexdigest()


def get_idempotency_record(
    db: Session, merchant_id: str, key: str
) -> IdempotencyKey | None:
    """
    Looks up an existing idempotency record for this merchant + key combination.
    Returns None if no record exists, or if it has expired.
    """
    record = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.merchant_id == merchant_id,
            IdempotencyKey.key == key,
        )
        .first()
    )

    if record is None:
        return None

    if record.expires_at and record.expires_at < datetime.now(timezone.utc):
        return None

    return record


def create_idempotency_record(
    db: Session,
    merchant_id: str,
    key: str,
    request_path: str,
    request_body: dict,
) -> IdempotencyKey:
    """
    Creates a new idempotency record before the actual request is processed,
    reserving this key so concurrent duplicate requests can be detected.
    """
    record = IdempotencyKey(
        merchant_id=merchant_id,
        key=key,
        request_path=request_path,
        request_body_hash=hash_request_body(request_body),
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=IDEMPOTENCY_KEY_EXPIRY_HOURS),
    )
    db.add(record)
    db.flush()
    return record


def save_idempotency_response(
    db: Session, record: IdempotencyKey, status_code: int, response_body: dict
) -> None:
    """
    Stores the response for a completed request against its idempotency record,
    so future duplicate requests can be replayed without redoing the work.
    """
    record.response_status_code = status_code
    record.response_body = json.dumps(response_body)
    db.flush()