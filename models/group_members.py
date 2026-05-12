import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Role(Enum):
    ADMIN = "admin"
    MEMBER = "member"


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(
        SQLEnum(Role), nullable=False, default=Role.MEMBER
    )  # "admin" or "member"
    joined_at = Column(DateTime, server_default=func.now())

    # relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")
