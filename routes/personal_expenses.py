from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.common import SuccessResponse
from schemas.personal_expenses import (
    PersonalExpenseCreate,
    PersonalExpenseResponse,
    PersonalExpenseUpdate,
)
from services.personal_expenses_services import (
    create_personal_expense,
    delete_personal_expense,
    generate_personal_expense_analytics,
    get_personal_expense,
    list_personal_expenses,
    update_personal_expense,
)

router = APIRouter(prefix="/expenses", tags=["Personal Expenses"])


@router.post(
    "/",
    response_model=SuccessResponse[PersonalExpenseResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create(
    expense_data: PersonalExpenseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_personal_expense(user.id, db, expense_data)


@router.get("/", response_model=SuccessResponse[list[PersonalExpenseResponse]])
async def list_expenses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_personal_expenses(db, user.id)


@router.get("/{expense_id}", response_model=SuccessResponse[PersonalExpenseResponse])
async def get_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_personal_expense(expense_id, user.id, db)


@router.put("/{expense_id}", response_model=SuccessResponse[PersonalExpenseResponse])
async def update_expense(
    expense_id: UUID,
    expense_data: PersonalExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await update_personal_expense(expense_id, user.id, expense_data, db)


@router.delete("/{expense_id}", response_model=SuccessResponse[None])
async def delete_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await delete_personal_expense(expense_id, user.id, db)


@router.get("/personal-data", response_model=SuccessResponse[dict])
async def get_personal_data(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await generate_personal_expense_analytics(user.id, db)
