from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from repository.balance_repository import BalanceRepository


class BalanceService:
    def __init__(self, session: AsyncSession):
        self.repo = BalanceRepository(session)

    async def calculate_balance(
        self, user_id: UUID, group_id: UUID
    ) -> dict[UUID, Decimal]:
        balances: dict[UUID, Decimal] = {}

        expenses_paid = await self.repo.get_expenses_paid_by_user(user_id, group_id)

        for expense in expenses_paid:
            for split in expense.splits:
                if split.user_id == user_id:
                    continue
                balances[split.user_id] =(
                    balances.get(
                        split.user_id, Decimal("0")) + Decimal(str(split.amount))
                ) 

        user_splits = await self.repo.get_user_splits(user_id, group_id)

        for split in user_splits:
            payer_id = split.expense.paid_by
            if payer_id == user_id:
                continue
            balances[payer_id] =(
                balances.get(
                    payer_id, Decimal("0")) - Decimal(str(split.amount))
            ) 

        return balances

    async def track_debts(self, user_id: UUID, group_id: UUID) -> dict[UUID, Decimal]:

        balances = await self.calculate_balance(user_id, group_id)

        payments_made = await self.repo.get_payments_made(user_id, group_id)

        for settlement in payments_made:
            receiver_id = settlement.receiver_id
            balances[receiver_id] = (
                balances.get(
                    receiver_id, Decimal("0")) + Decimal(str(settlement.amount))
            )

        payments_received = await self.repo.get_payments_received(user_id, group_id)

        for settlement in payments_received:
            payer_id = settlement.payer_id
            balances[payer_id] = (
                balances.get(
                    payer_id, Decimal("0")) - Decimal(str(settlement.amount))
            )

        return {uid: amt for uid, amt in balances.items() if amt != Decimal("0")}

    async def aggregate_totals(self, user_id: UUID) -> dict[str, Decimal]:

        expenses = await self.repo.get_personal_expenses(user_id)

        totals: dict[str, Decimal] = {}
        grand_total = Decimal("0")

        for expense in expenses:
            category = expense.category or "Uncategorized"
            amount = Decimal(str(expense.amount))
            totals[category] = totals.get(category, Decimal("0")) + amount
            grand_total += amount

        totals["__total__"] = grand_total
        return totals
