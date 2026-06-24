"""merge heads

Revision ID: 264ff58963f3
Revises: a1c4e6f9b2d3, e6a9c3f7d1b8
Create Date: 2026-06-24 10:20:00.412542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '264ff58963f3'
down_revision: Union[str, Sequence[str], None] = ('a1c4e6f9b2d3', 'e6a9c3f7d1b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
