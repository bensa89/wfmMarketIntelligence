"""add_intelligence_briefings

Revision ID: dc69a22e64c3
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23 17:55:26.895419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc69a22e64c3'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('intelligence_briefings',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('signal_count', sa.Integer(), nullable=False),
    sa.Column('assessment_count', sa.Integer(), nullable=False),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('intelligence_briefings')
