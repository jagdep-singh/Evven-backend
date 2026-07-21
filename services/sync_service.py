from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from engines.sync_engine import (
    compute_personal_records_for_expense,
    diff_personal_records,
)
from models.personal_expenses import PersonalExpense
from repository.personal_expense_repository import PersonalExpenseRepository
from repository.sync_repository import SyncRepository


async def sync_on_expense_created(
    expense_id: UUID,
    group_id: UUID,
    title: str,
    paid_by: UUID,
    splits: list[dict],
    db: AsyncSession,
    payment_method: str | None = None,
) -> list[PersonalExpense]:
    from models.group_expenses import PaymentMethod

    sync_repo = SyncRepository(db)
    desired = compute_personal_records_for_expense(
        expense_id=expense_id,
        group_id=group_id,
        title=title,
        paid_by=paid_by,
        splits=splits,
    )

    pm = PaymentMethod(payment_method) if payment_method else None

    rows = [
        PersonalExpense(
            user_id=record["user_id"],
            group_id=record["group_id"],
            group_expense_id=record["group_expense_id"],
            title=record["title"],
            amount=record["amount"],
            payment_method=pm,
        )
        for record in desired
    ]

    return await sync_repo.bulk_create_expense(rows)


async def sync_on_expense_updated(
    expense_id: UUID,
    group_id: UUID,
    title: str,
    paid_by: UUID,
    splits: list[dict],
    db: AsyncSession,
    payment_method: str | None = None,
) -> dict:
    from models.group_expenses import PaymentMethod

    sync_repo = SyncRepository(db)
    personal_repo = PersonalExpenseRepository(db)
    existing_rows = await sync_repo.get_sync_group_expenses(expense_id)
    existing = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "title": row.title,
            "amount": Decimal(str(row.amount)),
        }
        for row in existing_rows
    ]

    desired = compute_personal_records_for_expense(
        expense_id=expense_id,
        group_id=group_id,
        title=title,
        paid_by=paid_by,
        splits=splits,
    )

    to_create, to_update, to_delete = diff_personal_records(existing, desired)

    if to_create:
        pm = PaymentMethod(payment_method) if payment_method else None
        new_rows = [
            PersonalExpense(
                user_id=record["user_id"],
                group_id=record["group_id"],
                group_expense_id=record["group_expense_id"],
                title=record["title"],
                amount=record["amount"],
                payment_method=pm,
            )
            for record in to_create
        ]

        await sync_repo.bulk_create_expense(new_rows)

    if to_update:
        rows_to_update = await sync_repo.get_by_ids([r["id"] for r in to_update])
        rows_by_id = {row.id: row for row in rows_to_update}

        for update_data in to_update:
            row = rows_by_id.get(update_data["id"])
            if row:
                row.title = update_data["title"]
                row.amount = update_data["amount"]
                await personal_repo.update_expense(row)

    if to_delete:
        delete_ids = {r["id"] for r in to_delete}
        rows_to_delete = [r for r in existing_rows if r.id in delete_ids]
        await sync_repo.bulk_delete_expense(rows_to_delete)

    return {
        "created": len(to_create),
        "updated": len(to_update),
        "deleted": len(to_delete),
    }


async def sync_on_expense_deleted(expense_id: UUID, db: AsyncSession) -> None:
    sync_repo = SyncRepository(db)
    rows = await sync_repo.get_sync_group_expenses(expense_id)
    return await sync_repo.bulk_delete_expense(rows)
