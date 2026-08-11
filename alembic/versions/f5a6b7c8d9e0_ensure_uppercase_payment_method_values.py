"""ensure uppercase payment_method enum values

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-21 16:55:00.000000
"""

from typing import Sequence, Union
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
        -- Rename upi -> UPI if it exists
        IF EXISTS (
            SELECT 1
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'paymentmethod'
              AND e.enumlabel = 'upi'
        ) THEN
            ALTER TYPE paymentmethod RENAME VALUE 'upi' TO 'UPI';
        END IF;

        -- Rename cash -> CASH if it exists
        IF EXISTS (
            SELECT 1
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'paymentmethod'
              AND e.enumlabel = 'cash'
        ) THEN
            ALTER TYPE paymentmethod RENAME VALUE 'cash' TO 'CASH';
        END IF;
    END $$;
    """)


def downgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
        -- Rename UPI -> upi if it exists
        IF EXISTS (
            SELECT 1
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'paymentmethod'
              AND e.enumlabel = 'UPI'
        ) THEN
            ALTER TYPE paymentmethod RENAME VALUE 'UPI' TO 'upi';
        END IF;

        -- Rename CASH -> cash if it exists
        IF EXISTS (
            SELECT 1
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'paymentmethod'
              AND e.enumlabel = 'CASH'
        ) THEN
            ALTER TYPE paymentmethod RENAME VALUE 'CASH' TO 'cash';
        END IF;
    END $$;
    """)