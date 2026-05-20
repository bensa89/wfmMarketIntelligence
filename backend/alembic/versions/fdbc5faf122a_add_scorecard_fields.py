"""add_scorecard_fields

Revision ID: fdbc5faf122a
Revises: 41e3b165e6e7
Create Date: 2026-05-20 20:01:51.355310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdbc5faf122a'
down_revision: Union[str, Sequence[str], None] = '41e3b165e6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns on signal_assessments
    op.add_column("signal_assessments", sa.Column("dimension_targets", sa.JSON(), nullable=True))
    op.add_column("signal_assessments", sa.Column("kpi_targets", sa.JSON(), nullable=True))
    op.add_column("signal_assessments", sa.Column("assessment_weight", sa.Float(), nullable=True, server_default="1.0"))
    op.add_column("signal_assessments", sa.Column("valid_from", sa.DateTime(), nullable=True))
    op.add_column("signal_assessments", sa.Column("valid_until", sa.DateTime(), nullable=True))
    op.add_column("signal_assessments", sa.Column("buyer_relevance", sa.SmallInteger(), nullable=True))
    op.add_column("signal_assessments", sa.Column("routing_version", sa.String(20), nullable=True))

    # New competitor_scorecards table
    op.create_table(
        "competitor_scorecards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("period_type", sa.String(10), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("overall_trend", sa.String(10), nullable=True),
        sa.Column("dimension_scores", sa.JSON(), nullable=True),
        sa.Column("top_capabilities", sa.JSON(), nullable=True),
        sa.Column("top_moves", sa.JSON(), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("watchpoints", sa.JSON(), nullable=True),
        sa.Column("benchmark_position", sa.JSON(), nullable=True),
        sa.Column("contributing_assessment_ids", sa.JSON(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("scorecard_version", sa.String(20), nullable=True),
        sa.Column("routing_version", sa.String(20), nullable=True),
        sa.UniqueConstraint("company_id", "period_type", "generated_at", name="uq_scorecard_snapshot"),
    )
    op.create_index("ix_scorecard_current", "competitor_scorecards", ["company_id", "period_type", "is_current"])


def downgrade() -> None:
    op.drop_index("ix_scorecard_current", table_name="competitor_scorecards")
    op.drop_table("competitor_scorecards")
    op.drop_column("signal_assessments", "routing_version")
    op.drop_column("signal_assessments", "buyer_relevance")
    op.drop_column("signal_assessments", "valid_until")
    op.drop_column("signal_assessments", "valid_from")
    op.drop_column("signal_assessments", "assessment_weight")
    op.drop_column("signal_assessments", "kpi_targets")
    op.drop_column("signal_assessments", "dimension_targets")
