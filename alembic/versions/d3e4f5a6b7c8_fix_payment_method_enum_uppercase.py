"""fix payment_method enum to uppercase values

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-21 00:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'upi' TO 'UPI'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'cash' TO 'CASH'")


def downgrade() -> None:
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'UPI' TO 'upi'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'CASH' TO 'cash'")
