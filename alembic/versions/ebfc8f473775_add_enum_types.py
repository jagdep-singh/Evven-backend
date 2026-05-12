"""add enum types

Revision ID: ebfc8f473775
Revises: d6ecfd59fc59
Create Date: 2026-05-12 10:35:55.034583

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ebfc8f473775"
down_revision: Union[str, Sequence[str], None] = "d6ecfd59fc59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    split_type_enum = sa.Enum("EQUAL", "EXACT", "PERCENTAGE", name="splittype")

    role_enum = sa.Enum("ADMIN", "MEMBER", name="role")

    split_type_enum.create(op.get_bind(), checkfirst=True)

    role_enum.create(op.get_bind(), checkfirst=True)

    op.alter_column(
        "group_expenses",
        "split_type",
        existing_type=sa.VARCHAR(),
        type_=split_type_enum,
        existing_nullable=False,
        postgresql_using="split_type::splittype",
    )

    op.alter_column(
        "group_members",
        "role",
        existing_type=sa.VARCHAR(),
        type_=role_enum,
        existing_nullable=False,
        postgresql_using="role::role",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column(
        "group_members",
        "role",
        existing_type=sa.Enum("ADMIN", "MEMBER", name="role"),
        type_=sa.VARCHAR(),
        existing_nullable=False,
        postgresql_using="role::text",
    )

    op.alter_column(
        "group_expenses",
        "split_type",
        existing_type=sa.Enum("EQUAL", "EXACT", "PERCENTAGE", name="splittype"),
        type_=sa.VARCHAR(),
        existing_nullable=False,
        postgresql_using="split_type::text",
    )

    role_enum = sa.Enum("ADMIN", "MEMBER", name="role")

    split_type_enum = sa.Enum("EQUAL", "EXACT", "PERCENTAGE", name="splittype")

    role_enum.drop(op.get_bind(), checkfirst=True)

    split_type_enum.drop(op.get_bind(), checkfirst=True)
