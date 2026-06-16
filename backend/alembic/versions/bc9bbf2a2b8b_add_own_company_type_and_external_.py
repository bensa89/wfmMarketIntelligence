"""add_own_company_type_and_external_company_view

Revision ID: bc9bbf2a2b8b
Revises: ce52950e1e40
Create Date: 2026-06-16 20:36:16.379238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'bc9bbf2a2b8b'
down_revision: Union[str, Sequence[str], None] = 'ce52950e1e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires AUTOCOMMIT to add a value to an existing enum
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE companytype ADD VALUE IF NOT EXISTS 'own_company'"))

    op.create_table(
        'external_company_view',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_messages', sa.JSON(), nullable=True),
        sa.Column('observed_capabilities', sa.JSON(), nullable=True),
        sa.Column('observed_differentiators', sa.JSON(), nullable=True),
        sa.Column('observed_target_markets', sa.JSON(), nullable=True),
        sa.Column('tone_and_positioning', sa.Text(), nullable=True),
        sa.Column('signal_count_used', sa.Integer(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('external_company_view')
    # Note: PostgreSQL does not support removing enum values; own_company stays in the enum
