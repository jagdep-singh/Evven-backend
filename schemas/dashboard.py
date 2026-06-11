from pydantic import BaseModel

from schemas.expense_split import ExpenseResponse
from schemas.groups import GroupResponse
from schemas.user import UserResponse


class ExpenseDashBoardResponse(BaseModel):
    personal_expense: list[ExpenseResponse]
    group_expense: list


class DashBoard(BaseModel):
    user: UserResponse
    groups: list[GroupResponse]