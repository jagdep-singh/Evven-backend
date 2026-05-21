from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from engines.balance_engine import (
    apply_settlements,
    compute_category_totals,
    compute_raw_balance,
)
from repository.balance_repository import BalanceRepository


class BalanceService:
    def __init__(self, session: AsyncSession):
        self.repo = BalanceRepository(session)

    async def calculate_balance(
        self, user_id: UUID, group_id: UUID
    ) -> dict[UUID, Decimal]:
        expenses_paid = await self.repo.get_expenses_paid_by_user(user_id, group_id)
        user_splits = await self.repo.get_user_splits(user_id, group_id)
        return compute_raw_balance(expenses_paid, user_splits, user_id)

    async def track_debts(self, user_id: UUID, group_id: UUID) -> dict[UUID, Decimal]:
        balances = await self.calculate_balance(user_id, group_id)
        payments_made = await self.repo.get_payments_made(user_id, group_id)
        payments_received = await self.repo.get_payments_received(user_id, group_id)
        return apply_settlements(balances, payments_made, payments_received)

    async def aggregate_totals(self, user_id: UUID) -> dict[str, Decimal]:
        expenses = await self.repo.get_personal_expenses(user_id)
        return compute_category_totals(expenses)


# Basic Business logic
