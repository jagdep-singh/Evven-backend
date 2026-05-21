from uuid import UUID

from engines.debt_breakdown_engine import (
    aggregate_debt,
    build_debt_breakdown,
    simplify_debt,
)
from repository.expense_repository import ExpenseRepository


class DebtBreakdownService:
    def __init__(self, expense_repository: ExpenseRepository):
        self.expense_repository = expense_repository

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

        return {
            "breakdown": breakdown,
            "aggregated": aggregated,
            "simplified": simplified,
        }
