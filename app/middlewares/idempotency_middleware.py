import json

from fastapi import Header, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.merchant import Merchant
from app.middlewares.auth_middleware import get_current_merchant
from app.services import idempotency_service


class IdempotentReplayResponse(Exception):
    """Raised when an incoming request reuses an Idempotency-Key whose
    original request already completed. Caught in main.py, which
    replays the stored response directly instead of running the route."""

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self.body = body


async def check_idempotency(
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency that checks whether this request has already been
    processed under the given idempotency key.

    - Same key + same body + already completed  -> replay the ORIGINAL
      response (not a generic placeholder).
    - Same key + DIFFERENT body                  -> 422, this is a client
      bug or a parameter-swap attempt, never silently allowed.
    - Same key + same body + not yet completed   -> return the existing
      record so the route can finish processing it.
    - New key                                     -> reserve a new record.

    NOTE: reads request.body() here, before the route's own Pydantic
    parsing. Starlette caches the raw body bytes on the Request object,
    so the route handler can still read/parse the body normally after
    this dependency runs — this does not break the route's own parsing.
    """
    raw_body = await request.body()
    try:
        body_dict = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        body_dict = {}

    existing = idempotency_service.get_idempotency_record(
        db, merchant.id, idempotency_key
    )

    if existing is not None:
        incoming_hash = idempotency_service.hash_request_body(body_dict)
        if incoming_hash != existing.request_body_hash:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Idempotency-Key was already used with a different request body",
            )

        if existing.response_status_code is not None:
            cached_body = (
                json.loads(existing.response_body) if existing.response_body else {}
            )
            raise IdempotentReplayResponse(
                status_code=existing.response_status_code,
                body=cached_body,
            )

        return existing

    return idempotency_service.create_idempotency_record(
        db=db,
        merchant_id=merchant.id,
        key=idempotency_key,
        request_path=request.url.path,
        request_body=body_dict,
    )