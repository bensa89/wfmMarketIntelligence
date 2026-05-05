"""add cascade delete on all FK constraints

Revision ID: add_cascade_delete_source
Revises: add_crawl_source_timing
Create Date: 2026-05-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "add_cascade_delete_source"
down_revision: Union[str, Sequence[str], None] = "add_crawl_source_timing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_UPDATES = [
    (
        "crawl_run_sources",
        "crawl_run_sources_source_id_fkey",
        "source_id",
        "sources",
        "CASCADE",
    ),
    (
        "discovered_pages",
        "discovered_pages_source_id_fkey",
        "source_id",
        "sources",
        "CASCADE",
    ),
    ("documents", "documents_source_id_fkey", "source_id", "sources", "CASCADE"),
    ("signals", "signals_document_id_fkey", "document_id", "documents", "CASCADE"),
    (
        "signal_assessments",
        "signal_assessments_signal_id_fkey",
        "signal_id",
        "signals",
        "CASCADE",
    ),
    ("sources", "sources_company_id_fkey", "company_id", "companies", "CASCADE"),
]


def _fkey_name(table: str, col: str) -> str:
    return f"{table}_{col}_fkey"


def upgrade() -> None:
    for table, constraint_name, col, ref_table, ondelete in FK_UPDATES:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            ref_table,
            [col],
            ["id"],
            ondelete=ondelete,
        )

    op.drop_constraint(
        "search_results_linked_document_id_fkey", "search_results", type_="foreignkey"
    )
    op.create_foreign_key(
        "search_results_linked_document_id_fkey",
        "search_results",
        "documents",
        ["linked_document_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "search_results_linked_document_id_fkey", "search_results", type_="foreignkey"
    )
    op.create_foreign_key(
        "search_results_linked_document_id_fkey",
        "search_results",
        "documents",
        ["linked_document_id"],
        ["id"],
    )

    for table, constraint_name, col, ref_table, ondelete in FK_UPDATES:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            ref_table,
            [col],
            ["id"],
        )
