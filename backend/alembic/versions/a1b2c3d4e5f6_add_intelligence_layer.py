"""add_intelligence_layer

Revision ID: a1b2c3d4e5f6
Revises: c85a4338b763
Create Date: 2026-04-22 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c85a4338b763"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signal_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signal_id", sa.String(36), sa.ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("capability_primary", sa.String(100), nullable=True),
        sa.Column("capability_secondary", sa.JSON, nullable=True),
        sa.Column("signal_class", sa.String(50), nullable=True),
        sa.Column("evidence_strength", sa.SmallInteger, nullable=True),
        sa.Column("visibility_impact", sa.String(20), nullable=True),
        sa.Column("strategic_weight", sa.SmallInteger, nullable=True),
        sa.Column("movement_score", sa.SmallInteger, nullable=True),
        sa.Column("movement_strength", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("strategic_intent_guess", sa.Text, nullable=True),
        sa.Column("gameplay_tags", sa.JSON, nullable=True),
        sa.Column("assessment_summary", sa.Text, nullable=True),
        sa.Column("implication_for_us", sa.Text, nullable=True),
        sa.Column("watch_items", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "competitor_summaries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("period_type", sa.String(20), nullable=False, index=True),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("strategic_posture", sa.String(200), nullable=True),
        sa.Column("positioning_summary", sa.Text, nullable=True),
        sa.Column("top_capabilities", sa.JSON, nullable=True),
        sa.Column("capability_assessment", sa.JSON, nullable=True),
        sa.Column("top_risks", sa.JSON, nullable=True),
        sa.Column("top_opportunities", sa.JSON, nullable=True),
        sa.Column("watchpoints", sa.JSON, nullable=True),
        sa.Column("avg_movement_score", sa.Float, nullable=True),
        sa.Column("signal_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("signal_assessments")
    op.drop_table("competitor_summaries")
