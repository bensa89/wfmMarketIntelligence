"""add event_name and event_type to signals

Revision ID: e022ae1dcfab
Revises: 0099979dff60
Create Date: 2026-06-14 21:20:38.631506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e022ae1dcfab'
down_revision: Union[str, Sequence[str], None] = '0099979dff60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('signals', sa.Column('event_name', sa.String(length=255), nullable=True))
    op.add_column('signals', sa.Column('event_type', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('signals', 'event_type')
    op.drop_column('signals', 'event_name')
