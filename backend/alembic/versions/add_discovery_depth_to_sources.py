"""add discovery_depth to sources

Revision ID: add_discovery_depth_to_sources
Revises: 0d83d3a0303b
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_discovery_depth_to_sources'
down_revision: Union[str, Sequence[str], None] = '0d83d3a0303b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sources',
        sa.Column('discovery_depth', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('sources', 'discovery_depth')
