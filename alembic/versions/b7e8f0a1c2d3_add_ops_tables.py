"""add client_errors and deploy_logs tables

Revision ID: b7e8f0a1c2d3
Revises: 5dd72d4f2aeb
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7e8f0a1c2d3"
down_revision: Union[str, Sequence[str], None] = "5dd72d4f2aeb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "client_errors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("error_type", sa.String(100), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("route", sa.String(500), nullable=True),
        sa.Column("method", sa.String(20), nullable=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("app", sa.String(20), nullable=False, server_default="web"),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("stack_hash", sa.String(64), nullable=False),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_errors")),
    )
    op.create_index(
        op.f("idx_client_errors_created_at"),
        "client_errors",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("idx_client_errors_stack_hash_created_at"),
        "client_errors",
        ["stack_hash", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("idx_client_errors_error_type"),
        "client_errors",
        ["error_type"],
        unique=False,
    )
    op.create_index(
        op.f("idx_client_errors_resolved_at"),
        "client_errors",
        ["resolved_at"],
        unique=False,
    )
    op.create_index(
        op.f("idx_client_errors_user_id"),
        "client_errors",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("idx_client_errors_stack_hash"),
        "client_errors",
        ["stack_hash"],
        unique=False,
    )

    op.create_table(
        "deploy_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("app", sa.String(20), nullable=False),
        sa.Column(
            "environment",
            sa.String(20),
            nullable=False,
            server_default="production",
        ),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("commit_message", sa.String(500), nullable=True),
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default="github_actions",
        ),
        sa.Column("run_id", sa.String(100), nullable=True),
        sa.Column(
            "pushed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deploy_logs")),
    )
    op.create_index(
        op.f("idx_deploy_logs_pushed_at"),
        "deploy_logs",
        ["pushed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("idx_deploy_logs_pushed_at"), table_name="deploy_logs")
    op.drop_table("deploy_logs")
    op.drop_index(op.f("idx_client_errors_stack_hash"), table_name="client_errors")
    op.drop_index(op.f("idx_client_errors_user_id"), table_name="client_errors")
    op.drop_index(
        op.f("idx_client_errors_resolved_at"), table_name="client_errors"
    )
    op.drop_index(
        op.f("idx_client_errors_error_type"), table_name="client_errors"
    )
    op.drop_index(
        op.f("idx_client_errors_stack_hash_created_at"),
        table_name="client_errors",
    )
    op.drop_index(
        op.f("idx_client_errors_created_at"), table_name="client_errors"
    )
    op.drop_table("client_errors")
