"""add_momentum_delta_to_benchmark

Revision ID: 1a3dc0384956
Revises: 22f127a149f8
Create Date: 2026-05-25 08:52:29.943151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1a3dc0384956'
down_revision: Union[str, Sequence[str], None] = '22f127a149f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('competitor_capability_benchmarks', sa.Column('prev_period_momentum_score', sa.SmallInteger(), nullable=True))
    op.add_column('competitor_capability_benchmarks', sa.Column('momentum_delta', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('competitor_capability_benchmarks', 'momentum_delta')
    op.drop_column('competitor_capability_benchmarks', 'prev_period_momentum_score')
