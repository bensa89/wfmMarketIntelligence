"""add risks and opportunities to weekly_digests

Revision ID: e9d3c7f1b5a2
Revises: f7e236d29e3f
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'e9d3c7f1b5a2'
down_revision = 'f7e236d29e3f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('weekly_digests', sa.Column('risks', sa.JSON(), nullable=True))
    op.add_column('weekly_digests', sa.Column('opportunities', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('weekly_digests', 'opportunities')
    op.drop_column('weekly_digests', 'risks')
