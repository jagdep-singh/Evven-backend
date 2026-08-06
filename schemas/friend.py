from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class FriendRequestCreate(BaseModel):
    user_code: str


class PendingRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    user_code: str
    profile_picture: Optional[str] = None
    created_at: datetime
    direction: str  # incoming or outgoing


class FriendRequestListResponse(BaseModel):
    incoming: list[PendingRequestResponse]
    outgoing: list[PendingRequestResponse]


class FriendResponse(BaseModel):
    id: UUID
    name: str
    user_code: str
    profile_picture: Optional[str] = None
    group_id: UUID
    balance: Decimal  # positive = they owe you, negative = you owe them


class FriendDetailResponse(FriendResponse):
    pass
