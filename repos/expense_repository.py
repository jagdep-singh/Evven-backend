from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.expense_splits import ExpenseSplit
from models.group_expenses import GroupExpense


class ExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, expense: GroupExpense, splits: list[ExpenseSplit]) -> GroupExpense:

        self.session.add(expense)
        
        for split in splits:
            self.session.add(split)
        
        await self.session.commit()
        await self.session.refresh(expense)

        return expense

    async def get_by_id(self, expense_id: UUID) -> GroupExpense | None:

        result = await self.session.execute(
            select(GroupExpense).where(GroupExpense.id == expense_id)
        )

        return result.scalar_one_or_none()

    async def list_by_group(self, group_id: UUID) -> list[GroupExpense]:

        groups = await self.session.execute(
            select(GroupExpense).where(GroupExpense.group_id == group_id)
        )

        return list(groups.scalars().all())

    async def update(self, expense: GroupExpense, data: dict) -> GroupExpense:

        for key, val in data.items():
            setattr(expense, key, val)

        await self.session.commit()
        await self.session.refresh(expense)

        return expense

    async def delete(self, expense: GroupExpense) -> None:
        await self.session.delete(expense)
        await self.session.commit()

    async def get_splits(self, expense_id: UUID) -> list[ExpenseSplit]:

        result = await self.session.execute(
            select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id)
        )

        return list(result.scalars().all())
