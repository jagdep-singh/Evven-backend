import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class SplitType(Enum):
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"


class GroupExpense(Base):
    __tablename__ = "group_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    title = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    paid_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    split_type = Column(
        SQLEnum(SplitType), nullable=False, default=SplitType.EQUAL
    )  # "equal" / "exact" / "percentage"
    created_at = Column(DateTime, server_default=func.now())

    # relationships
    group = relationship("Group", back_populates="expenses")
    payer = relationship("User", foreign_keys=[paid_by], back_populates="expenses_paid")
    splits = relationship("ExpenseSplit", back_populates="expense")

    personal_expenses = relationship("PersonalExpense", back_populates="group_expense")
