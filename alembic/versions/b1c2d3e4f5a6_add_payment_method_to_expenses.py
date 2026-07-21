"""add payment_method to expenses

Revision ID: b1c2d3e4f5a6
Revises: 39cd22944d16
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '39cd22944d16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

paymentmethodenum = sa.Enum('UPI', 'CASH', name='paymentmethod')


def upgrade() -> None:
    """Upgrade schema."""
    paymentmethodenum.create(op.get_bind(), checkfirst=True)
    op.add_column('group_expenses', sa.Column('payment_method', paymentmethodenum, nullable=True))
    op.add_column('personal_expenses', sa.Column('payment_method', paymentmethodenum, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('personal_expenses', 'payment_method')
    op.drop_column('group_expenses', 'payment_method')
    paymentmethodenum.drop(op.get_bind(), checkfirst=True)
