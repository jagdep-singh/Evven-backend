from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str


class GroupUpdate(BaseModel):
    name: Optional[str] = None


class GroupResponse(BaseModel):
    id: UUID
    name: str
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class GroupMemberResponse(BaseModel):
    id: UUID
    group_id: UUID
    user_id: UUID
    joined_at: datetime

    model_config = {"from_attributes": True}
