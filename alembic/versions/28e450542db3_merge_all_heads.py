"""merge all heads

Revision ID: 28e450542db3
Revises: 0a1b2c3d4e5f, b4c5d6e7f8a9, b7e8f0a1c2d3
Create Date: 2026-08-19 20:18:54.723350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28e450542db3'
down_revision: Union[str, Sequence[str], None] = ('0a1b2c3d4e5f', 'b4c5d6e7f8a9', 'b7e8f0a1c2d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
