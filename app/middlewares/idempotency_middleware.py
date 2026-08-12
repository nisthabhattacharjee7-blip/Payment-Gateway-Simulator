from fastapi import Header, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.merchant import Merchant
from app.middlewares.auth_middleware import get_current_merchant
from app.models.idempotency_key import IdempotencyKey
from app.services import idempotency_service
from app.services import idempotency_service
from app.services import IdempotencyService


class IdempotentReplayResponse(Exception):
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self.body = body
        super().__init__("Replaying cached idempotent response")

"""Raised when a request is a genuine duplicate and already has a cached
    response. It is Caught by a FastAPI exception handler in main.py, which
    replays the stored response directly instead of running the route."""


def check_idempotency(
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
) -> IdempotencyKey:
    """
    FastAPI dependency that checks whether this request has already been
    processed under the given idempotency key. If a cached response
    exists, raises IdempotentReplayResponse to short-circuit the route.
    Otherwise, reserves a new idempotency record for this request.
    """
    existing = idempotency_service.get_idempotency_record(
        db, merchant.id, idempotency_key
    )

    if existing is not None and existing.response_status_code is not None:
        raise IdempotentReplayResponse(
            status_code=existing.response_status_code,
            body={"replayed": True, "note": "Duplicate request, original response returned"},
        )

    if existing is not None:
        return existing

    return idempotency_service.create_idempotency_record(
        db=db,
        merchant_id=merchant.id,
        key=idempotency_key,
        request_path="",
        request_body={},
    )