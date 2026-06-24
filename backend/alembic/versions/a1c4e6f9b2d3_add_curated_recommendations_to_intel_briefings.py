"""add_curated_recommendations_to_intelligence_briefings

Revision ID: a1c4e6f9b2d3
Revises: bc9bbf2a2b8b
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c4e6f9b2d3'
down_revision: Union[str, Sequence[str], None] = 'bc9bbf2a2b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('intelligence_briefings', sa.Column('curated_recommendations', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('intelligence_briefings', 'curated_recommendations')
