from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.merchant import Merchant
from app.middlewares.auth_middleware import get_current_merchant
from app.schemas.merchant_schema import MerchantResponse, MerchantCreate
from app.utils.hmac_utils import generate_api_key, hash_api_key

router = APIRouter(prefix="/merchants", tags=["merchants"])

@router.post("", response_model=MerchantResponse, status_code=201)
def create_merchant(payload: MerchantCreate, db: Session = Depends(get_db)):
    """
    Registers a new merchant. Generates a raw API key, returned once in
    this response — only its hash is stored, so it can never be retrieved
    again after this.
    """
    raw_api_key = generate_api_key()

    merchant = Merchant(
        name=payload.name,
        email=payload.email,
        webhook_url=payload.webhook_url,
        api_key=hash_api_key(raw_api_key),
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    response = MerchantResponse.model_validate(merchant)
    response.api_key = raw_api_key
    return response

@router.get("/me", response_model=MerchantResponse)
def get_my_merchant_profile(merchant: Merchant = Depends(get_current_merchant)):
    """
    Returns the profile of the merchant identified by the request's
    X-API-Key header.
    """
    return merchant
