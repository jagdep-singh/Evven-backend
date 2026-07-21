from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from engines.split_engine import calculate_splits
from models.group_expenses import GroupExpense, PaymentMethod, SplitType
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
from services.sync_service import (
    sync_on_expense_created,
    sync_on_expense_deleted,
    sync_on_expense_updated,
)


async def create_expenses(
    paid_by: UUID, db: AsyncSession, group_id: UUID, expense_data: ExpenseCreate
) -> SuccessResponse[ExpenseResponse]:
    expense_repo = ExpenseRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    if not await member_repo.is_member(paid_by, group_id):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = await member_repo.list_group_members(group_id)
    members_ids: list[UUID] = [m.user_id for m in members]

    splits_dict = calculate_splits(
        total_amount=Decimal(str(expense_data.amount)),
        all_members_id=members_ids,
        split_type=expense_data.split_type,
        splits_input=expense_data.splits_input,
        equal_member_ids=expense_data.participant_ids,
    )

    expense = GroupExpense(
        group_id=group_id,
        title=expense_data.title,
        paid_by=paid_by,
        amount=expense_data.amount,
        split_type=SplitType(expense_data.split_type),
        category=expense_data.category,
        payment_method=PaymentMethod(expense_data.payment_method)
        if expense_data.payment_method
        else None,
    )

    created_expense = await expense_repo.create_expense(expense, splits_dict)

    await sync_on_expense_created(
        expense_id=created_expense.id,
        group_id=group_id,
        title=expense_data.title,
        paid_by=paid_by,
        splits=[{"user_id": uid, "amount": amt} for uid, amt in splits_dict.items()],
        db=db,
        payment_method=expense_data.payment_method,
    )

    return SuccessResponse(
        message="Expense created successfully",
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
            "expense": ExpenseResponse.model_validate(expense),
            "splits": [ExpenseSplitResponse.model_validate(s) for s in splits],
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

    members = await member_repo.list_group_members(group_id)
    members_ids: list[UUID] = [m.user_id for m in members]
    update_data = expense_data.model_dump(
        exclude_unset=True,
        exclude={"splits_input", "participant_ids"},
    )

    if expense_data.split_type:
        update_data["split_type"] = SplitType(expense_data.split_type)

    if expense_data.payment_method:
        update_data["payment_method"] = PaymentMethod(expense_data.payment_method)

    updated_expense = await expense_repo.update_expense(
        expense,
        update_data,
    )

    if expense_data.amount is not None or expense_data.split_type is not None:
        splits_dict = calculate_splits(
            total_amount=Decimal(str(updated_expense.amount)),
            all_members_id=members_ids,
            split_type=updated_expense.split_type.value,
            splits_input=expense_data.splits_input,
            equal_member_ids=expense_data.participant_ids,
        )
        existing_splits = await expense_repo.replace_splits(expense_id, splits_dict)
    else:
        existing_splits = await expense_repo.get_splits(expense_id)

    await sync_on_expense_updated(
        expense_id=expense_id,
        group_id=group_id,
        title=updated_expense.title,
        paid_by=updated_expense.paid_by,
        splits=[{"user_id": s.user_id, "amount": s.amount} for s in existing_splits],
        db=db,
        payment_method=expense_data.payment_method,
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

    await sync_on_expense_deleted(expense_id=expense_id, db=db)

    await expense_repo.delete_expense(expense)

    return SuccessResponse(message="Expense deleted successfully", data=None)
