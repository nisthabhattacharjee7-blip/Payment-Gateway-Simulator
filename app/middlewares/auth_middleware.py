from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.merchant import Merchant
from app.utils.hmac_utils import get_key_prefix, verify_api_key


def get_current_merchant(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Merchant:
    """
    FastAPI dependency, authenticates a request using the X-API-Key
    header, returning the matching Merchant. Raises 401 if the key is
    missing or invalid.

    Two-step lookup: the key's prefix (non-secret, indexed) narrows
    the search to a single candidate row, then verify_api_key does the
    real constant-time comparison against that row's full hash. This
    avoids hashing the incoming key and comparing it against every
    merchant's hash via a DB equality scan — the previous approach —
    in favor of the same prefix-then-verify pattern real payment
    gateways use for API keys.
    """
    prefix = get_key_prefix(x_api_key)
    merchant = db.query(Merchant).filter(Merchant.key_prefix == prefix).first()

    if merchant is None or not verify_api_key(x_api_key, merchant.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    return merchant