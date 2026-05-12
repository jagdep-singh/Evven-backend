from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field  # type: ignore


class SettlementCreate(BaseModel):
    # group_id : UUID
    # payer_id : UUID ...........  these 2 not needed
    receiver_id: UUID
    amount: Decimal = Field(gt=0)


class SettlementResponse(BaseModel):
    id: UUID
    group_id: UUID
    payer_id: UUID
    receiver_id: UUID
    amount: Decimal


class SettlementUpdate(BaseModel):
    # we only need amount and to update reciver we delete the settlement and create new one
    amount: Decimal | None = Field(default=None, gt=0)


class SettlementListResponse(BaseModel):
    settlements: list[SettlementResponse] = Field(
        default_factory=list
    )  # this makes frontend easier to handle when there are no settlements, instead of getting null we get empty list
    total_count: int = 0


# Basic schema, needed to be updated later
