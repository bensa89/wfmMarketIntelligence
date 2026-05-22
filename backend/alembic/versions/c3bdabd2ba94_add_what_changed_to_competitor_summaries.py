"""add what_changed to competitor_summaries

Revision ID: c3bdabd2ba94
Revises: fdbc5faf122a
Create Date: 2026-05-22 07:24:03.687136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3bdabd2ba94'
down_revision: Union[str, Sequence[str], None] = 'fdbc5faf122a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('competitor_summaries', sa.Column('what_changed', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('competitor_summaries', 'what_changed')
