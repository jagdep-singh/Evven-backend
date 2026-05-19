from uuid import UUID

from models.expense_split import ExpenseSplit
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.group_expenses import GroupExpense
from models.personal_expenses import PersonalExpense  # For V2
from models.settlements import Settlement


class BalanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_expenses_paid_by_user(self, user_id: UUID, group_id: UUID) -> list(
        GroupExpense
    ):

        result = await self.session.execute(
            select(GroupExpense)
            .options(selectinload(selectinload.splits))
            .where(
                GroupExpense.group_id == group_id,
                GroupExpense.paid_by == user_id,
            )
        )

        return list(result.scalar().all())

    async def get_user_splits(
        self, user_id: UUID, group_id: UUID
    ) -> list[ExpenseSplit]:

        result = await self.session.execute(
            select(ExpenseSplit)
            .join(GroupExpense, ExpenseSplit.expense_id == GroupExpense.id)
            .options((selectinload(ExpenseSplit.expense)))
            .where(
                GroupExpense.group_id == group_id,
                ExpenseSplit.user_id == user_id,
            )
        )

        return list(result.scalar().all())

    async def get_payments_made(
        self, user_id: UUID, group_id: UUID
    ) -> list[Settlement]:

        result = await self.session.execute(
            select(Settlement).where(
                Settlement.group_id == group_id,
                Settlement.payer_id == user_id,
            )
        )

        return list(result.scalar().all())

    async def get_payments_received(
        self, user_id: UUID, group_id: UUID
    ) -> list[Settlement]:

        result = await self.session.execute(
            select[Settlement].where(
                Settlement.group_id == group_id,
                Settlement.receiver_id == user_id,
            )
        )

        return list(result.scalar().all())

    async def get_personal_expenses(self, user_id: UUID) -> list[PersonalExpense]:

        result = await self.session.execute(
            select[PersonalExpense].where(PersonalExpense.user_id == user_id)
        )

        return list(result.scalar().all())
