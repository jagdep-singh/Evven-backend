from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PersonalExpenseCreate(BaseModel):
    title: str
    amount: Decimal = Field(gt=0)
    category: str | None = None
    date: datetime | None = None
    notes: str | None = None


class PersonalExpenseUpdate(BaseModel):
    title: str | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    category: str | None = None
    date: datetime | None = None
    notes: str | None = None


class PersonalExpenseResponse(BaseModel):
    id: UUID
    user_id: UUID
    group_id: UUID | None = None
    group_expense_id: UUID | None = None
    title: str
    amount: Decimal
    category: str | None = None
    date: datetime | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
