from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.group_expenses import PaymentMethod
from models.personal_expenses import PersonalExpense
from repository.personal_expense_repository import PersonalExpenseRepository
from schemas.common import SuccessResponse
from schemas.personal_expenses import (
    PersonalExpenseCreate,
    PersonalExpenseResponse,
    PersonalExpenseUpdate,
)


async def create_personal_expense(
    user_id: UUID,
    db: AsyncSession,
    expense_data: PersonalExpenseCreate,
) -> SuccessResponse[PersonalExpenseResponse]:
    repo = PersonalExpenseRepository(db)

    expense = PersonalExpense(
        user_id=user_id,
        title=expense_data.title,
        amount=expense_data.amount,
        category=expense_data.category,
        date=expense_data.date,
        notes=expense_data.notes,
        payment_method=PaymentMethod(expense_data.payment_method)
        if expense_data.payment_method
        else None,
    )

    created_expense = await repo.create_expense(expense)

    return SuccessResponse(
        message="Personal expense created successfully",
        data=PersonalExpenseResponse.model_validate(created_expense),
    )


async def list_personal_expenses(
    db: AsyncSession,
    user_id: UUID,
) -> SuccessResponse[list[PersonalExpenseResponse]]:
    repo = PersonalExpenseRepository(db)

    expenses = await repo.list_expenses(user_id)

    return SuccessResponse(
        message="Personal expenses fetched successfully",
        data=[PersonalExpenseResponse.model_validate(expense) for expense in expenses],
    )


async def get_personal_expense(
    expense_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> SuccessResponse[PersonalExpenseResponse]:
    repo = PersonalExpenseRepository(db)

    expense = await repo.get_expense_by_id(expense_id, user_id)

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal expense not found",
        )

    return SuccessResponse(
        message="Personal expense fetched successfully",
        data=PersonalExpenseResponse.model_validate(expense),
    )


async def update_personal_expense(
    expense_id: UUID,
    user_id: UUID,
    expense_data: PersonalExpenseUpdate,
    db: AsyncSession,
) -> SuccessResponse[PersonalExpenseResponse]:
    repo = PersonalExpenseRepository(db)

    expense = await repo.get_expense_by_id(expense_id, user_id)

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal expense not found",
        )

    update_data = expense_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(expense, field, value)

    updated_expense = await repo.update_expense(expense)

    return SuccessResponse(
        message="Personal expense updated successfully",
        data=PersonalExpenseResponse.model_validate(updated_expense),
    )


async def delete_personal_expense(
    expense_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> SuccessResponse[None]:
    repo = PersonalExpenseRepository(db)

    expense = await repo.get_expense_by_id(expense_id, user_id)

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal expense not found",
        )

    await repo.delete_expense(expense)

    return SuccessResponse(
        message="Personal expense deleted successfully",
        data=None,
    )


async def generate_personal_expense_analytics(
    user_id: UUID,
    db: AsyncSession,
) -> SuccessResponse[dict]:
    repo = PersonalExpenseRepository(db)

    expenses = await repo.list_expenses(user_id)

    total_spent = 0
    category_totals = {}

    for expense in expenses:
        amount = expense.amount or 0
        category = expense.category or "uncategorized"

        total_spent += amount
        category_totals[category] = category_totals.get(category, 0) + amount

    return SuccessResponse(
        message="Personal expense analytics generated successfully",
        data={
            "total_spent": total_spent,
            "expense_count": len(expenses),
            "spending_by_category": category_totals,
        },
    )
