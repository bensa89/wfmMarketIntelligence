"""add_curated_fields_to_intelligence_briefings

Revision ID: b3f1a9c2d8e7
Revises: e022ae1dcfab
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3f1a9c2d8e7'
down_revision: Union[str, Sequence[str], None] = 'e022ae1dcfab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('intelligence_briefings', sa.Column('curated_risks', sa.JSON(), nullable=True))
    op.add_column('intelligence_briefings', sa.Column('curated_opportunities', sa.JSON(), nullable=True))
    op.add_column('intelligence_briefings', sa.Column('curated_watchpoints', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('intelligence_briefings', 'curated_watchpoints')
    op.drop_column('intelligence_briefings', 'curated_opportunities')
    op.drop_column('intelligence_briefings', 'curated_risks')
