"""add_crawl_run_source_timing

Revision ID: add_crawl_source_timing
Revises: f222e9e6adc7
Create Date: 2026-05-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_crawl_source_timing"
down_revision: Union[str, Sequence[str], None] = "f222e9e6adc7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crawl_run_sources", sa.Column("fetch_ms", sa.Integer(), nullable=True)
    )
    op.add_column(
        "crawl_run_sources", sa.Column("extract_ms", sa.Integer(), nullable=True)
    )
    op.add_column(
        "crawl_run_sources", sa.Column("analyse_ms", sa.Integer(), nullable=True)
    )
    op.add_column(
        "crawl_run_sources", sa.Column("discover_ms", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("crawl_run_sources", "discover_ms")
    op.drop_column("crawl_run_sources", "analyse_ms")
    op.drop_column("crawl_run_sources", "extract_ms")
    op.drop_column("crawl_run_sources", "fetch_ms")
