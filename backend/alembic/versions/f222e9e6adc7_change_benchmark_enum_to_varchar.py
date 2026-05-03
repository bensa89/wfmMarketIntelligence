"""change_benchmark_enum_to_varchar

Revision ID: f222e9e6adc7
Revises: f7e236d29e3f
Create Date: 2026-05-03 21:24:49.160558

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f222e9e6adc7"
down_revision: Union[str, Sequence[str], None] = "f7e236d29e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "competitor_capability_benchmarks",
        "period_type",
        existing_type=postgresql.ENUM("30d", "90d", "180d", name="periodtypeenum"),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
    op.alter_column(
        "competitor_capability_benchmarks",
        "tier",
        existing_type=postgresql.ENUM(
            "leader",
            "strong",
            "emerging",
            "weakly_evidenced",
            name="benchmarktiereneum",
        ),
        type_=sa.String(length=20),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "competitor_capability_benchmarks",
        "tier",
        existing_type=sa.String(length=20),
        type_=postgresql.ENUM(
            "leader",
            "strong",
            "emerging",
            "weakly_evidenced",
            name="benchmarktiereneum",
        ),
        existing_nullable=False,
    )
    op.alter_column(
        "competitor_capability_benchmarks",
        "period_type",
        existing_type=sa.String(length=10),
        type_=postgresql.ENUM("30d", "90d", "180d", name="periodtypeenum"),
        existing_nullable=False,
    )
