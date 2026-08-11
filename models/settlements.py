import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base
from models.group_expenses import PaymentMethod


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    payer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # relationships
    group = relationship("Group", back_populates="settlements")
    payer = relationship(
        "User", foreign_keys=[payer_id], back_populates="payments_made"
    )
    receiver = relationship(
        "User", foreign_keys=[receiver_id], back_populates="payments_received"
    )
