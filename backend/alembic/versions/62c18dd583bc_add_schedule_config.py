"""add_schedule_config

Revision ID: 62c18dd583bc
Revises: 1a3dc0384956
Create Date: 2026-06-11 19:58:21.652333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62c18dd583bc'
down_revision: Union[str, Sequence[str], None] = '1a3dc0384956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('schedule_config',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('crawl_enabled', sa.Boolean(), nullable=False),
    sa.Column('crawl_day_of_week', sa.Integer(), nullable=False),
    sa.Column('crawl_time', sa.String(length=5), nullable=False),
    sa.Column('crawl_timezone', sa.String(length=50), nullable=False),
    sa.Column('digest_after_crawl', sa.Boolean(), nullable=False),
    sa.Column('digest_enabled', sa.Boolean(), nullable=False),
    sa.Column('digest_day_of_week', sa.Integer(), nullable=False),
    sa.Column('digest_time', sa.String(length=5), nullable=False),
    sa.Column('email_enabled', sa.Boolean(), nullable=False),
    sa.Column('email_recipients', sa.JSON(), nullable=False),
    sa.Column('smtp_host', sa.String(length=255), nullable=False),
    sa.Column('smtp_port', sa.Integer(), nullable=False),
    sa.Column('smtp_user', sa.String(length=255), nullable=False),
    sa.Column('smtp_password', sa.String(length=255), nullable=False),
    sa.Column('smtp_from', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('schedule_config')
