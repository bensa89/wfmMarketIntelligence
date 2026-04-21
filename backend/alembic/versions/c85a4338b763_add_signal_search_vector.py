"""add_signal_search_vector

Revision ID: c85a4338b763
Revises: 3d201074a3d3
Create Date: 2026-04-21 20:36:31.360385

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

revision: str = "c85a4338b763"
down_revision: Union[str, Sequence[str], None] = "3d201074a3d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    op.add_column("signals", sa.Column("search_vector", TSVECTOR, nullable=True))

    op.execute("""
    CREATE OR REPLACE FUNCTION signals_search_vector_update() RETURNS trigger AS $$
    DECLARE
        doc_url documents.url%TYPE;
        doc_title documents.title%TYPE;
    BEGIN
        SELECT url, title INTO doc_url, doc_title
        FROM documents WHERE id = NEW.document_id;

        NEW.search_vector :=
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.title, ''))), 'A') ||
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.topic, ''))), 'B') ||
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.summary, ''))), 'B') ||
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.why_it_matters, ''))), 'C') ||
            setweight(to_tsvector('german', unaccent(COALESCE(doc_url, ''))), 'D') ||
            setweight(to_tsvector('german', unaccent(COALESCE(doc_title, ''))), 'D');
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_signals_search_vector_update
    BEFORE INSERT OR UPDATE ON signals
    FOR EACH ROW EXECUTE FUNCTION signals_search_vector_update()
    """)

    op.execute("UPDATE signals SET title = title WHERE search_vector IS NULL")

    op.execute(
        "CREATE INDEX ix_signals_search_vector ON signals USING GIN (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_signals_search_vector")
    op.execute("DROP TRIGGER IF EXISTS trg_signals_search_vector_update ON signals")
    op.execute("DROP FUNCTION IF EXISTS signals_search_vector_update()")
    op.drop_column("signals", "search_vector")
