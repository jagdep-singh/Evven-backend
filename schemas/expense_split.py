from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, model_validator


class ExpenseCreate(BaseModel):
    title: str
    amount: Decimal
    category: str | None = None
    split_type: str
    splits_input: Optional[dict[UUID, Decimal]] = None
    participant_ids: Optional[list[UUID]] = None
    payment_method: str | None = None

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
    category: Optional[str] = None
    split_type: Optional[str] = None
    splits_input: Optional[dict[UUID, Decimal]] = None
    participant_ids: Optional[list[UUID]] = None
    payment_method: Optional[str] = None

    @model_validator(mode="after")
    def validate_splits(self) -> "ExpenseUpdate":
        if self.split_type in ("exact", "percentage") and not self.splits_input:
            raise ValueError(f"splits_input is required for {self.split_type} split")

        if self.split_type and self.split_type not in ("equal", "exact", "percentage"):
            raise ValueError("split_type must be equal, exact and percentage")

        return self


class ExpenseSplitResponse(BaseModel):
    id: UUID
    expense_id: UUID
    user_id: UUID
    amount: Decimal
    category: str | None = None

    model_config = {"from_attributes": True}


class ExpenseResponse(BaseModel):
    id: UUID
    group_id: UUID
    paid_by: UUID
    title: str
    amount: Decimal
    category: str | None = None
    split_type: str
    payment_method: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpensePaidResponse(BaseModel):
    id: UUID
    group_id: UUID
    paid_by: UUID
    title: str
    amount: Decimal

    model_config = {"from_attributes": True}


class ExpenseOweResponse(BaseModel):
    id: UUID
    expense_id: UUID
    owed: UUID
    amount: Decimal

    model_config = {"from_attributes": True}
