"""add_events_source_type

Revision ID: 0099979dff60
Revises: a8f3c1e92d47
Create Date: 2026-06-14 21:09:54.234008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0099979dff60'
down_revision: Union[str, Sequence[str], None] = 'a8f3c1e92d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD VALUE cannot run inside a transaction in PostgreSQL
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'events'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op
    pass
