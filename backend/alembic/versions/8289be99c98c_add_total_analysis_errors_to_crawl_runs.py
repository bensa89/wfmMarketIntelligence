"""add total_analysis_errors to crawl_runs

Revision ID: 8289be99c98c
Revises: 1b89e979ba6c
Create Date: 2026-07-03 08:08:37.217940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8289be99c98c'
down_revision: Union[str, Sequence[str], None] = '1b89e979ba6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('crawl_runs', sa.Column('total_analysis_errors', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('crawl_runs', 'total_analysis_errors')
