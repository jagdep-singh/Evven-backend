from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, model_validator


class ExpenseCreate(BaseModel):
    title: str
    amount: Decimal
    split_type: str
    splits_input: Optional[dict[UUID, Decimal]] = None
    equal_member_ids: Optional[list[UUID]] = None

    @model_validator(mode="after")
    def validate_splits(self) -> "ExpenseCreate":
        if self.split_type == "equal":
            pass

        elif self.split_type in ("exact", "percentage"):
            if not self.splits_input:
                raise ValueError(
                    f"splits_input is required for {self.split_type} split"
                )

        else:
            raise ValueError("split_type must be equal, exact and percentage")

        return self


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[Decimal] = None


class ExpenseSplitResponse(BaseModel):
    id: UUID
    expense_id: UUID
    user_id: UUID
    amount: Decimal

    model_config = {"from_attributes": True}


class ExpenseResponse(BaseModel):
    id: UUID
    group_id: UUID
    paid_by: UUID
    title: str
    amount: Decimal
    split_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
