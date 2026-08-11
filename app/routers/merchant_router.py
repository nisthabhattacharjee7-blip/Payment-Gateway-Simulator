from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.merchant import Merchant
from app.middlewares.auth_middleware import get_current_merchant
from app.schemas.merchant_schema import MerchantResponse, MerchantCreate

router = APIRouter(prefix="/merchants", tags=["merchants"])

@router.post("", response_model=MerchantResponse, status_code=201)
def create_merchant(payload: MerchantCreate, db: Session = Depends(get_db)):
    """
    Registers a new merchant. Generates an id and api_key automatically —
    the merchant does not choose these.
    """
    merchant = Merchant(
        name=payload.name,
        email=payload.email,
        webhook_url=payload.webhook_url,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant

@router.get("/me", response_model=MerchantResponse)
def get_my_merchant_profile(merchant: Merchant = Depends(get_current_merchant)):
    """
    Returns the profile of the merchant identified by the request's
    X-API-Key header.
    """
    return merchant
