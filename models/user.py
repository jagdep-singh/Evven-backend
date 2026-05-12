import uuid
from enum import Enum

from sqlalchemy import TIMESTAMP, Boolean, Column, String  # type: ignore
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID  # type: ignore
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func  # type: ignore

from database import Base


class AuthProvider(Enum):
    LOCAL = "local"
    GOOGLE = "google"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    auth_provider = Column(
        SQLEnum(AuthProvider), nullable=False, default=AuthProvider.LOCAL
    )
    profile_picture = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # relationships

    personal_expenses = relationship("PersonalExpense", back_populates="user")

    """All groups created by this user
    Example: user.groups -> [Group1, Group2]"""
    groups = relationship("Group", back_populates="creator")
    """
    All group membership records of this user
    Used to know which groups the user joined
    Example: user.group_memberships -> [membership1, membership2]
    """
    group_memberships = relationship("GroupMember", back_populates="user")
    """
    All expenses paid by this user
    Connected using GroupExpense.paid_by foreign key
    Example: user.expenses_paid -> [expense1, expense2]
    """
    expenses_paid = relationship(
        "GroupExpense", foreign_keys="GroupExpense.paid_by", back_populates="payer"
    )
    """
    All expense split records assigned to this user
    Used to know how much this user owes in expenses
    Example: user.expense_splits -> [split1, split2]
    """
    expense_splits = relationship("ExpenseSplit", back_populates="user")
    """
    All settlement payments made by this user
    Connected using Settlement.payer_id foreign key
    Example: user.payments_made -> [payment1, payment2]
    """
    payments_made = relationship(
        "Settlement", foreign_keys="Settlement.payer_id", back_populates="payer"
    )
    """
    All settlement payments received by this user
    Connected using Settlement.receiver_id foreign key
    Example: user.payments_received -> [payment1, payment2]
    """
    payments_received = relationship(
        "Settlement", foreign_keys="Settlement.receiver_id", back_populates="receiver"
    )
