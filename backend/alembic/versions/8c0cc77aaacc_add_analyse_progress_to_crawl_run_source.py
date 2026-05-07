"""add_analyse_progress_to_crawl_run_source

Revision ID: 8c0cc77aaacc
Revises: add_discovery_depth_to_sources
Create Date: 2026-05-07 10:38:22.135093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c0cc77aaacc'
down_revision: Union[str, Sequence[str], None] = 'add_discovery_depth_to_sources'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('crawl_run_sources', sa.Column('analyse_docs_done', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('crawl_run_sources', sa.Column('analyse_docs_total', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('crawl_run_sources', sa.Column('analyse_current_url', sa.String(length=2000), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crawl_run_sources', 'analyse_current_url')
    op.drop_column('crawl_run_sources', 'analyse_docs_total')
    op.drop_column('crawl_run_sources', 'analyse_docs_done')
