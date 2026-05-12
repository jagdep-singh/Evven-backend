import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class PersonalExpense(Base):
    __tablename__ = "personal_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True
    )  # nullable — only set if synced from a group
    group_expense_id = Column(
        UUID(as_uuid=True), ForeignKey("group_expenses.id"), nullable=True
    )  # nullable — tracks source expense
    title = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(String, nullable=True)
    date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # relationships
    user = relationship("User", back_populates="personal_expenses")
    group = relationship("Group", back_populates="personal_expenses")
    group_expense = relationship("GroupExpense", back_populates="personal_expenses")
