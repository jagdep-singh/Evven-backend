"""add payment_method to settlements

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-21 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

paymentmethodenum = sa.Enum('UPI', 'CASH', name='paymentmethod')


def upgrade() -> None:
    """Upgrade schema."""
    paymentmethodenum.create(op.get_bind(), checkfirst=True)
    op.add_column('settlements', sa.Column('payment_method', paymentmethodenum, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('settlements', 'payment_method')
