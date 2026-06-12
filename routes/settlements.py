from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.settlement import SettlementListResponse, SettlementResponse
from services.settlement_service import list_settlements, record_payment

router = APIRouter(prefix="/groups", tags=["Settlements"])


@router.get("/{group_id}/settlements", response_model=SettlementListResponse)
async def get_settlements(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_settlements(group_id, user.id, db)


@router.post("/{group_id}/settlements", response_model=SettlementResponse)
async def create_settlement(
    group_id: UUID,
    receiver_id: UUID,
    amount: Decimal,
    payer_id: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await record_payment(group_id, payer_id.id, receiver_id, amount, db)
