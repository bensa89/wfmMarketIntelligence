"""add_event_date_location_to_signals

Revision ID: a8f3c1e92d47
Revises: 62c18dd583bc
Create Date: 2026-06-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f3c1e92d47"
down_revision: Union[str, None] = "62c18dd583bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("event_date", sa.DateTime(), nullable=True))
    op.add_column("signals", sa.Column("event_location", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("signals", "event_location")
    op.drop_column("signals", "event_date")
