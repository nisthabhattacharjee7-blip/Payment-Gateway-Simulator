from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.merchant import Merchant
from app.schemas.settlement_schema import SettlementResponse
from app.middlewares.auth_middleware import get_current_merchant
from app.services import settlement_service

router = APIRouter(prefix="/settlements", tags=["settlements"])


@router.post("/batch", response_model=SettlementResponse, status_code=201)
def create_settlement_batch(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Triggers a settlement batch for the authenticated merchant, bundling
    all captured-but-unsettled payments into one settlement and moving
    the funds toward their bank. In a real system, this would run on a
    schedule rather than be manually triggered.
    """
    try:
        settlement = settlement_service.create_settlement_batch(db, merchant.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db.commit()
    db.refresh(settlement)
    return settlement


@router.get("", response_model=list[SettlementResponse])
def list_settlements(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Lists all settlement batches belonging to the authenticated merchant.
    """
    from app.models.settlement import Settlement

    settlements = (
        db.query(Settlement)
        .filter(Settlement.merchant_id == merchant.id)
        .order_by(Settlement.created_at.desc())
        .all()
    )
    return settlements