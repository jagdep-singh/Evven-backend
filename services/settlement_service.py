from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.group_expenses import PaymentMethod
from models.settlements import Settlement
from repository.group_member_repository import GroupMemberRepository
from repository.group_repository import GroupRepository
from repository.settlement_repository import SettlementRepository
from schemas.common import SuccessResponse
from schemas.settlement import SettlementListResponse, SettlementResponse


async def record_payment(
    group_id: UUID,
    payer_id: UUID,
    receiver_id: UUID,
    amount: Decimal,
    db: AsyncSession,
    payment_method: str | None = None,
) -> Settlement:
    settle_repo = SettlementRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    if not await member_repo.is_member(payer_id, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    if not await member_repo.is_member(receiver_id, group_id):
        raise HTTPException(status_code=404, detail="Member is not added in group")

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if amount <= Decimal("0"):
        raise ValueError("Payment amount must be positive.")

    if payer_id == receiver_id:
        raise ValueError("Payer and receiver cannot be the same user.")
    settlement = Settlement(
        group_id=group_id,
        payer_id=payer_id,
        receiver_id=receiver_id,
        amount=amount,
        payment_method=PaymentMethod(payment_method) if payment_method else None,
    )
    return await settle_repo.add_settlement(settlement)


async def list_settlements(
    group_id: UUID, user_id: UUID, db: AsyncSession
) -> SettlementListResponse:
    settle_repo = SettlementRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    if not await member_repo.is_member(user_id, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    settlements = await settle_repo.get_settlements_by_group_id(group_id)
    return SuccessResponse(
        message="Settlements fetched successfully",
        data=SettlementListResponse(
            settlements=[SettlementResponse.model_validate(s) for s in settlements],
            total_count=len(settlements),
        ),
    )

    # async def update_balances():
