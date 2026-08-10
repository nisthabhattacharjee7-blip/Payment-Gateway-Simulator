from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.merchant import Merchant


def get_current_merchant(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Merchant:
    """
    FastAPI dependency that authenticates a request using the
    X-API-Key header, returning the matching Merchant.
    Raises 401 if the key is missing or invalid.
    """
    merchant = db.query(Merchant).filter(Merchant.api_key == x_api_key).first()

    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    return merchant