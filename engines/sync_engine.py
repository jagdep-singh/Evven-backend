from decimal import Decimal
from uuid import UUID


def compute_personal_records_for_expense(
    expense_id: UUID, group_id: UUID, title: str, paid_by: UUID, splits: list[dict]
) -> list[dict]:
    records = []
    for split in splits:
        records.append(
            {
                "user_id": split["user_id"],
                "group_id": group_id,
                "group_expense_id": expense_id,
                "title": title,
                "amount": Decimal(str(split["amount"])),
                "category": None,
                "source": "group",
            }
        )

    return records


def diff_personal_records(
    existing: list[dict], desired: list[dict]
) -> tuple[list[dict], list[dict], list[dict]]:
    existing_by_user: dict[UUID, dict] = {r["user_id"]: r for r in existing}
    desired_by_user: dict[UUID, dict] = {r["user_id"]: r for r in desired}

    to_create = []
    to_update = []
    to_delete = []

    for user_id, desired_record in desired_by_user.items():
        if user_id not in existing_by_user:
            to_create.append(desired_record)
        else:
            existing_record = existing_by_user[user_id]
            changed = (
                existing_record["amount"] != desired_record["amount"]
                or existing_record["title"] != desired_record["title"]
            )
            if changed:
                to_update.append(
                    {
                        "id": existing_record["id"],
                        "title": desired_record["title"],
                        "amount": desired_record["amount"],
                    }
                )

    for user_id, existing_record in existing_by_user.items():
        if user_id not in desired_by_user:
            to_delete.append(existing_record)

    return to_create, to_update, to_delete
