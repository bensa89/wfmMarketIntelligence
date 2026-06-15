"""merge_heads

Revision ID: ce52950e1e40
Revises: b3f1a9c2d8e7, e9d3c7f1b5a2
Create Date: 2026-06-15 22:03:32.941595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce52950e1e40'
down_revision: Union[str, Sequence[str], None] = ('b3f1a9c2d8e7', 'e9d3c7f1b5a2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
