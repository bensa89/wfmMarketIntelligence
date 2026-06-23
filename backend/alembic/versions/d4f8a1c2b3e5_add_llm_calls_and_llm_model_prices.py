"""add llm_calls and llm_model_prices tables

Revision ID: d4f8a1c2b3e5
Revises: bc9bbf2a2b8b
Create Date: 2026-06-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4f8a1c2b3e5'
down_revision: Union[str, Sequence[str], None] = 'bc9bbf2a2b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('caller', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('estimated', sa.Boolean(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_calls_created_at', 'llm_calls', ['created_at'])
    op.create_index('ix_llm_calls_caller', 'llm_calls', ['caller'])
    op.create_index('ix_llm_calls_provider', 'llm_calls', ['provider'])
    op.create_index('ix_llm_calls_model', 'llm_calls', ['model'])

    op.create_table(
        'llm_model_prices',
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('input_price_per_1m', sa.Float(), nullable=False),
        sa.Column('output_price_per_1m', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('model'),
    )


def downgrade() -> None:
    op.drop_table('llm_model_prices')
    op.drop_index('ix_llm_calls_model', table_name='llm_calls')
    op.drop_index('ix_llm_calls_provider', table_name='llm_calls')
    op.drop_index('ix_llm_calls_caller', table_name='llm_calls')
    op.drop_index('ix_llm_calls_created_at', table_name='llm_calls')
    op.drop_table('llm_calls')
