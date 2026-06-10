from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.settlements import Settlement
from repository.settlement_repository import SettlementRepository


class SettlementService:
    def __init__(self, session: AsyncSession):
        self.repo = SettlementRepository(session)

    async def record_payment(
        self, group_id: UUID, payer_id: UUID, receiver_id: UUID, amount: Decimal
    ) -> Settlement:
        if amount <= Decimal("0"):
            raise ValueError("Payment amount must be positive.")

        if payer_id == receiver_id:
            raise ValueError("Payer and receiver cannot be the same user.")
        settlement = Settlement(
            group_id=group_id,
            payer_id=payer_id,
            receiver_id=receiver_id,
            amount=amount,
        )
        return await self.repo.add_settlement(settlement)

    # async def update_balances():
