from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.personal_expenses import PersonalExpense


class PersonalExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_expense(self, expense: PersonalExpense) -> PersonalExpense:
        self.session.add(expense)
        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def list_expenses(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[PersonalExpense]:
        result = await self.session.execute(
            select(PersonalExpense)
            .where(PersonalExpense.user_id == user_id)
            .order_by(PersonalExpense.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_expense_by_id(
        self,
        expense_id: UUID,
        user_id: UUID,
    ) -> PersonalExpense | None:
        result = await self.session.execute(
            select(PersonalExpense).where(
                PersonalExpense.id == expense_id, PersonalExpense.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def update_expense(self, expense: PersonalExpense) -> PersonalExpense:
        self.session.add(expense)
        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def delete_expense(self, expense: PersonalExpense) -> None:
        await self.session.delete(expense)
        await self.session.commit()
