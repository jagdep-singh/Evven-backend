from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from engines.split_engine import calculate_splits
from models.group_expenses import GroupExpense
from repository.expense_repository import ExpenseRepository
from repository.group_member_repository import GroupMemberRepository
from repository.group_repository import GroupRepository
from schemas.common import SuccessResponse
from schemas.expense_split import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSplitResponse,
    ExpenseUpdate,
)


async def create_expenses(
    paid_by: UUID, db: AsyncSession, group_id: UUID, expense_data: ExpenseCreate
) -> dict:

    expense_repo = ExpenseRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not await member_repo.is_member(paid_by, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    members = await member_repo.list_group_members(group_id)
    members_ids: list[UUID] = [m.user_id for m in members]

    splits = calculate_splits(
        total_amount=Decimal(str(expense_data.amount)),
        all_members_id=members_ids,
        split_type=expense_data.split_type,
        splits_input=expense_data.splits_input,
        equal_member_ids=expense_data.splits_input,
    )

    expense = GroupExpense(
        group_id=group_id,
        title=expense_data.title,
        paid_by=paid_by,
        amount=expense_data.amount,
        split_type=expense_data.split_type,
    )

    created_expense = await expense_repo.create_expense(expense, splits)

    return SuccessResponse(
        message="Expense created succesfully",
        data=ExpenseResponse.model_validate(created_expense),
    )


async def list_expense(group_id: UUID, current_user_id: UUID, db: AsyncSession) -> dict:

    expense_repo = ExpenseRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    if not await member_repo.is_member(current_user_id, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    expenses = await expense_repo.list_by_group(group_id)

    return SuccessResponse(
        message="Expenses fetched successfully",
        data=[ExpenseResponse.model_validate(e) for e in expenses],
    )


async def get_expense(
    expense_id: UUID, group_id: UUID, current_user_id: UUID, db: AsyncSession
) -> dict:

    expense_repo = ExpenseRepository(db)
    member_repo = GroupMemberRepository(db)

    if not await member_repo.is_member(current_user_id, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    expense = await expense_repo.get_by_id(expense_id)
    if not expense or expense.group_id != group_id:
        raise HTTPException(status_code=404, detail="Expense not found")

    splits = await expense_repo.get_splits(expense_id)

    return SuccessResponse(
        message="Expense fetched successfully",
        data={
            ExpenseResponse.model_validate(expense),
            [ExpenseSplitResponse.model_validate(s) for s in splits],
        },
    )


async def update_expense_by_id(
    expense_id: UUID,
    group_id: UUID,
    expense_data: ExpenseUpdate,
    current_user_id: UUID,
    db: AsyncSession,
) -> dict:

    expense_repo = ExpenseRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    if not await member_repo.is_member(current_user_id, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    expense = await expense_repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.paid_by != current_user_id:
        raise HTTPException(
            status_code=403, detail="Only person who created the expense can update it"
        )

    updated_expense = await expense_repo.update_expense(
        expense, expense_data.model_dump(exclude_unset=True)
    )

    return SuccessResponse(
        message="Expense updated successfully",
        data=ExpenseResponse.model_validate(updated_expense),
    )


async def delete_expense_by_id(
    expense_id: UUID, group_id: UUID, current_user_id: UUID, db: AsyncSession
) -> dict:

    expense_repo = ExpenseRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    if not await member_repo.is_member(current_user_id, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    expense = await expense_repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.paid_by != current_user_id and group.created_by != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Only payer or group created by can delete the expense",
        )

    await expense_repo.delete_expense(expense)

    return SuccessResponse(message="Expense deleted successfully", data=None)
