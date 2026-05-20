from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.expense_split import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)
from services.expense_service import (
    create_expenses,
    delete_expense_by_id,
    get_expense,
    list_expense,
    update_expense_by_id,
)

router = APIRouter(prefix="/groups", tags=["Group Expenses"])


@router.post(
    "/{group_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_expense_in_group(
    group_id: UUID,
    expense_data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_expenses(user.id, db, group_id, expense_data)


@router.get("/{group_id}/expenses")
async def list_expenses(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_expense(group_id, user.id, db)


@router.get("/{group_id}/expenses/{expense_id}")
async def get_expenses(
    expense_id: UUID,
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_expense(expense_id, group_id, user.id, db)


@router.put("/{group_id}/expenses/{expense_id}")
async def update_expenses(
    expense_id: UUID,
    group_id: UUID,
    expense_data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await update_expense_by_id(expense_id, group_id, expense_data, user.id, db)


@router.delete("/{group_id}/expenses/{expense_id}")
async def delete_expenses(
    expense_id: UUID,
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await delete_expense_by_id(expense_id, group_id, user.id, db)
