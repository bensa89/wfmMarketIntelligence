"""add_discover_pages_crawled_found_to_crawl_run_source

Revision ID: 7c1829582bbd
Revises: add_respect_robots_txt
Create Date: 2026-05-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '7c1829582bbd'
down_revision: Union[str, Sequence[str], None] = 'add_respect_robots_txt'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('crawl_run_sources', sa.Column('discover_pages_crawled', sa.Integer(), nullable=True))
    op.add_column('crawl_run_sources', sa.Column('discover_pages_found', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('crawl_run_sources', 'discover_pages_found')
    op.drop_column('crawl_run_sources', 'discover_pages_crawled')
