"""add user_note to signal_assessments

Revision ID: f4be6d0416f6
Revises: 264ff58963f3
Create Date: 2026-06-24 20:22:30.910422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f4be6d0416f6'
down_revision: Union[str, Sequence[str], None] = '264ff58963f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('signal_assessments', sa.Column('user_note', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('signal_assessments', 'user_note')
