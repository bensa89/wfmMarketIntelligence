"""add analysis phase fields

Revision ID: 97058cb503e3
Revises: 3c679ce1e2eb
Create Date: 2026-05-06 09:04:00.899471

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "97058cb503e3"
down_revision: Union[str, Sequence[str], None] = "3c679ce1e2eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE crawlrunsourcestatus ADD VALUE IF NOT EXISTS 'analysing'")
    op.add_column(
        "crawl_run_sources",
        sa.Column("analyse_started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "crawl_run_sources",
        sa.Column("analyse_finished_at", sa.DateTime(), nullable=True),
    )
    analysis_status = sa.Enum(
        "pending", "analysing", "analysed", "analysis_failed", name="analysisstatus"
    )
    analysis_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "sources", sa.Column("analysis_status", analysis_status, nullable=True)
    )

    op.execute(
        "UPDATE sources SET analysis_status = 'pending' "
        "WHERE analysis_status IS NULL "
        "AND EXISTS (SELECT 1 FROM documents d WHERE d.source_id = sources.id AND d.is_analysed = false AND d.content_markdown IS NOT NULL)"
    )
    op.execute(
        "UPDATE sources SET analysis_status = 'analysed' "
        "WHERE analysis_status IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.source_id = sources.id AND d.is_analysed = false) "
        "AND EXISTS (SELECT 1 FROM documents d WHERE d.source_id = sources.id)"
    )
    op.execute(
        "UPDATE crawl_run_sources SET status = 'completed', analyse_finished_at = NOW() "
        "WHERE status = 'analysing'"
    )


def downgrade() -> None:
    op.drop_column("sources", "analysis_status")
    op.drop_column("crawl_run_sources", "analyse_finished_at")
    op.drop_column("crawl_run_sources", "analyse_started_at")
    op.execute(
        "DELETE FROM pg_enum WHERE enumlabel = 'analysing' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'crawlrunsourcestatus')"
    )
    sa.Enum(name="analysisstatus").drop(op.get_bind(), checkfirst=True)
