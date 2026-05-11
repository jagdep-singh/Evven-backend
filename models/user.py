from sqlalchemy import Column, String, TIMESTAMP , Boolean , Enum as SQLEnum 
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.sql import func

from database import Base
from enum import Enum

import uuid


class AuthProvider(Enum):
    LOCAL = 'local'
    GOOGLE = 'google'
    
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    auth_provider = Column(SQLEnum(AuthProvider), nullable=False, default=AuthProvider.LOCAL) 
    profile_picture = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)