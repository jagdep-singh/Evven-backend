import uuid

from sqlalchemy import Column, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class ClientError(Base):
    __tablename__ = "client_errors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message = Column(String(500), nullable=False)
    error_type = Column(String(100), nullable=True)
    stack_trace = Column(Text, nullable=True)
    route = Column(String(500), nullable=True)
    method = Column(String(20), nullable=True)
    user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )
    app = Column(String(20), nullable=False, default="web")
    version = Column(String(50), nullable=True)
    user_agent = Column(String(300), nullable=True)
    stack_hash = Column(String(64), nullable=False)
    client_timestamp = Column("client_timestamp", nullable=True)
    created_at = Column("created_at", server_default=func.now(), nullable=False)
    resolved_at = Column("resolved_at", nullable=True)

    __table_args__ = (
        Index("idx_client_errors_created_at", "created_at"),
        Index(
            "idx_client_errors_stack_hash_created_at",
            "stack_hash",
            "created_at",
        ),
        Index("idx_client_errors_error_type", "error_type"),
        Index("idx_client_errors_resolved_at", "resolved_at"),
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        primaryjoin="ClientError.user_id == User.id",
        lazy="selectin",
    )


class DeployLog(Base):
    __tablename__ = "deploy_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app = Column(String(20), nullable=False)
    environment = Column(String(20), nullable=False, default="production")
    commit_sha = Column(String(64), nullable=False)
    branch = Column(String(100), nullable=True)
    actor = Column(String(200), nullable=False)
    commit_message = Column(String(500), nullable=True)
    source = Column(String(20), nullable=False, default="github_actions")
    run_id = Column(String(100), nullable=True)
    pushed_at = Column("pushed_at", server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_deploy_logs_pushed_at", "pushed_at"),)
