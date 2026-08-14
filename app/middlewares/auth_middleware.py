from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.merchant import Merchant
from app.utils.hmac_utils import hash_api_key


def get_current_merchant(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Merchant:
    """
    FastAPI dependency , authenticates a request using the
    X-API-Key header, returning the matching Merchant.
    Raises 401 if the key is missing or invalid.
    """
    hashed_incoming_key = hash_api_key(x_api_key)
    merchant = db.query(Merchant).filter(Merchant.api_key == hashed_incoming_key).first()

    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    return merchant