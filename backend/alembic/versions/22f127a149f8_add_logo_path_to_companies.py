"""add_logo_path_to_companies

Revision ID: 22f127a149f8
Revises: c3bdabd2ba94
Create Date: 2026-05-22 12:28:08.971109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22f127a149f8'
down_revision: Union[str, Sequence[str], None] = 'c3bdabd2ba94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('logo_path', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('companies', 'logo_path')
