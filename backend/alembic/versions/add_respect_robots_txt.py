"""add_respect_robots_txt

Revision ID: add_respect_robots_txt
Revises: add_cascade_delete_source
Create Date: 2026-05-05 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_respect_robots_txt'
down_revision: Union[str, Sequence[str], None] = 'add_cascade_delete_source'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sources',
        sa.Column('respect_robots_txt', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    op.drop_column('sources', 'respect_robots_txt')
