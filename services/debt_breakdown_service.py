from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from engines.debt_breakdown_engine import (
    aggregate_debt,
    build_debt_breakdown,
    settle_debts,
    simplify_debt,
)
from repository.expense_repository import ExpenseRepository
from repository.group_member_repository import GroupMemberRepository
from repository.group_repository import GroupRepository
from repository.settlement_repository import SettlementRepository
from schemas.common import SuccessResponse


class DebtBreakdownService:
    def __init__(
        self,
        expense_repository: ExpenseRepository,
        settlement_repository: SettlementRepository,
    ):
        self.expense_repository = expense_repository
        self.settlement_repository = settlement_repository

    def _build_engine_input(self, expenses) -> list[dict]:
        return [
            {
                "expense_id": expense.id,
                "title": expense.title,
                "paid_by": expense.paid_by,
                "amount": expense.amount,
                "splits": [
                    {"user_id": split.user_id, "amount": split.amount}
                    for split in expense.splits
                ],
            }
            for expense in expenses
        ]

    async def get_group_debt_breakdown(self, group_id: UUID):
        expenses = await self.expense_repository.get_group_expense_with_splits(group_id)
        engine_input = self._build_engine_input(expenses)
        breakdown = build_debt_breakdown(engine_input)
        aggregated = aggregate_debt(breakdown)
        simplified = simplify_debt(aggregated)
        settled = settle_debts(simplified)

        return {
            "breakdown": breakdown,
            "aggregated": aggregated,
            "simplified": simplified,
            "settled": settled,
        }


async def get_user_debt_breakdown(
    group_id: UUID, current_user_id: UUID, db: AsyncSession
):
    member_repo = GroupMemberRepository(db)
    group_repo = GroupRepository(db)
    expense_repo = ExpenseRepository(db)
    settlement_repo = SettlementRepository(db)

    if not await member_repo.is_member(current_user_id, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    service = DebtBreakdownService(expense_repo, settlement_repo)
    breakdown = await service.get_group_debt_breakdown(group_id)

    return SuccessResponse(
        message="User debt breakdown fetched successfully",
        data=breakdown,
    )
