import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class GroupType(Enum):
    NORMAL = "NORMAL"
    FRIEND = "FRIEND"


class GroupStatus(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class Group(Base):
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Friend Feature
    group_type = Column(SQLEnum(GroupType), nullable=False, default=GroupType.NORMAL)
    status = Column(SQLEnum(GroupStatus), nullable=False, default=GroupStatus.ACTIVE)

    # relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="groups")
    members = relationship("GroupMember", back_populates="group")
    expenses = relationship("GroupExpense", back_populates="group")

    personal_expenses = relationship("PersonalExpense", back_populates="group")
    settlements = relationship("Settlement", back_populates="group")
