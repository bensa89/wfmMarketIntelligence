"""add_sections_to_weekly_digests

Revision ID: 41e3b165e6e7
Revises: 8c0cc77aaacc
Create Date: 2026-05-07 19:35:05.611133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41e3b165e6e7'
down_revision: Union[str, Sequence[str], None] = '8c0cc77aaacc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('weekly_digests', sa.Column('sections', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('weekly_digests', 'sections')
