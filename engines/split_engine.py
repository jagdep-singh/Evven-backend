from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException


def calculate_splits(
    total_amount: Decimal,
    all_members_id: list[UUID],
    split_type: str,
    splits_input: dict[UUID, Decimal] | None = None,
    equal_member_ids: list[UUID] | None = None,
) -> dict[UUID, Decimal]:
    if split_type == "equal":
        if equal_member_ids:
            invalid = set(equal_member_ids) - set(all_members_id)

            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"These users are not group members: {invalid}",
                )

            target_ids = equal_member_ids

        else:
            target_ids = all_members_id

        if not target_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one member is required for equal split",
            )

        share = (total_amount / len(target_ids)).quantize(Decimal("0.01"))

        result = {uid: share for uid in target_ids}

        total_assigned = sum(result.values())
        remainder = total_amount - total_assigned

        if remainder != Decimal("0.00"):
            last_id = target_ids[-1]
            result[last_id] += remainder

        return result

    elif split_type == "exact":
        if not splits_input:
            raise HTTPException(
                status_code=400, detail="Splits_input is required for exact split"
            )

        invalid = set(splits_input.keys()) - set(all_members_id)

        if invalid:
            raise HTTPException(
                status_code=400, detail=f"These users are not group members: {invalid}"
            )

        total = sum(splits_input.values())

        if round(total, 2) != round(total_amount, 2):
            raise HTTPException(
                status_code=400,
                detail=f"Exact amounts {total} must sum to {total_amount}",
            )

        return splits_input

    elif split_type == "percentage":
        if not splits_input:
            raise HTTPException(
                status_code=400,
                detail="Splits_input is required for percentage wise split",
            )

        invalid = set(splits_input.keys()) - set(all_members_id)

        if invalid:
            raise HTTPException(
                status_code=400, detail=f"These users are not group members: {invalid}"
            )

        total_pc = sum(splits_input.values())
        if round(total_pc, 2) != Decimal("100"):
            raise HTTPException(
                status_code=400, detail=f"Percentages {total_pc} must sum to 100"
            )

        return {
            uid: round(total_amount * pct / Decimal("100"), 2)
            for uid, pct in splits_input.items()
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid split type '{split_type}'. Must be equal, exact and percentage",
        )
