from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.expense_splits import ExpenseSplit
from models.group_expenses import GroupExpense
from schemas.expense_split import ExpenseOweResponse, ExpensePaidResponse


class ExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_expense(
        self, expense: GroupExpense, splits_dict: dict[UUID, Decimal]
    ) -> GroupExpense:
        self.session.add(expense)
        await self.session.flush()

        # Create splits with the expense ID
        for user_id, amount in splits_dict.items():
            split = ExpenseSplit(expense_id=expense.id, user_id=user_id, amount=amount)
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

    async def update_expense(self, expense: GroupExpense, data: dict) -> GroupExpense:
        for key, val in data.items():
            setattr(expense, key, val)

        await self.session.commit()
        await self.session.refresh(expense)

        return expense

    async def delete_expense(self, expense: GroupExpense) -> None:
        await self.session.delete(expense)
        await self.session.commit()

    async def get_splits(self, expense_id: UUID) -> list[ExpenseSplit]:
        result = await self.session.execute(
            select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id)
        )

        return list(result.scalars().all())

    async def has_pending_balance(self, group_id: UUID, user_id: UUID) -> bool:
        result = await self.session.execute(
            select(ExpenseSplit)
            .join(GroupExpense, ExpenseSplit.expense_id == GroupExpense.id)
            .where(
                GroupExpense.group_id == group_id,
                ExpenseSplit.user_id == user_id,
                ExpenseSplit.amount != 0,
            )
        )

        return result.scalar_one_or_none() is not None

    async def get_expense_paid_by_user(
        self, group_id: UUID, user_id: UUID, limit: 20
    ) -> list[ExpensePaidResponse]:
        result = await self.session.execute(
            select(GroupExpense)
            .where(GroupExpense.group_id == group_id, GroupExpense.paid_by == user_id)
            .order_by(GroupExpense.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_expense_owed_user(
        self, user_id: UUID, limit: 20
    ) -> list[ExpenseOweResponse]:
        result = await self.session.execute(
            select(ExpenseSplit).where(ExpenseSplit.user_id == user_id).limit(limit)
        )
        return list(result.scalars().all())
