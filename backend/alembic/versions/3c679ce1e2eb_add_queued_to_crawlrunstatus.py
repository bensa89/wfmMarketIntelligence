"""add_queued_to_crawlrunstatus

Revision ID: 3c679ce1e2eb
Revises: 7c1829582bbd
Create Date: 2026-05-06
"""
from typing import Sequence, Union
from alembic import op

revision: str = '3c679ce1e2eb'
down_revision: Union[str, Sequence[str], None] = '7c1829582bbd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE crawlrunstatus ADD VALUE IF NOT EXISTS 'queued'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type
    pass
