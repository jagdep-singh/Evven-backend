"""fix payment_method enum to lowercase values

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'UPI' TO 'upi'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'CASH' TO 'cash'")


def downgrade() -> None:
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'upi' TO 'UPI'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'cash' TO 'CASH'")
