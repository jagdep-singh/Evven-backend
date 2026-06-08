import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, String  # type: ignore
from sqlalchemy.dialects.postgresql import UUID  # type: ignore

from core.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password-reset-table"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expire_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
