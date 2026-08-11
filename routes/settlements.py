from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.common import SuccessResponse
from schemas.settlement import SettlementListResponse, SettlementResponse
from services.settlement_service import list_settlements, record_payment

router = APIRouter(prefix="/groups", tags=["Settlements"])


@router.get(
    "/{group_id}/settlements",
    response_model=SuccessResponse[SettlementListResponse],
)
async def get_settlements(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_settlements(group_id, user.id, db)


@router.post(
    "/{group_id}/settlements",
    response_model=SuccessResponse[SettlementResponse],
)
async def create_settlement(
    group_id: UUID,
    receiver_id: UUID,
    amount: Decimal,
    payer_id: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    payment_method: Optional[str] = Query(None),
):
    settlement = await record_payment(
        group_id, payer_id.id, receiver_id, amount, db, payment_method
    )
    return SuccessResponse(
        message="Settlement recorded successfully",
        data=SettlementResponse.model_validate(settlement),
    )
