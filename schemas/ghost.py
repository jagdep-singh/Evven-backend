from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from schemas.personal_expenses import PersonalExpenseResponse


class GhostCreate(BaseModel):
    name: str


class GhostResponse(BaseModel):
    id: UUID
    name: str
    user_code: str
    shadow_group_id: UUID

    model_config = {"from_attributes": True}


class GhostBalanceResponse(BaseModel):
    ghost_id: UUID
    name: str
    group_id: UUID
    net_balance: Decimal
    status: str


class GhostDetailResponse(GhostBalanceResponse):
    expenses: list[PersonalExpenseResponse]
