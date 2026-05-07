"""add analysis_status to discovered_page

Revision ID: 0d83d3a0303b
Revises: 97058cb503e3
Create Date: 2026-05-06 17:05:01.986955

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0d83d3a0303b"
down_revision: Union[str, Sequence[str], None] = "97058cb503e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "discovered_pages",
        sa.Column("analysis_status", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("discovered_pages", "analysis_status")
