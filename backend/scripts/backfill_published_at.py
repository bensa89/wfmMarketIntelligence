"""
One-off backfill: extract published_at from stored HTML for all Documents,
then propagate to their Signals.

Run inside the backend container:
  docker compose -f docker-compose.dev.yml exec backend python scripts/backfill_published_at.py
"""
import logging
from bs4 import BeautifulSoup

from app.database import SessionLocal
from app.models.document import Document
from app.models.signal import Signal
from app.crawler.extractor import _extract_published_at

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.published_at.is_(None))
            .filter(Document.content_raw_html.isnot(None))
            .all()
        )
        logger.info("Documents to process: %d", len(docs))

        docs_updated = 0
        signals_updated = 0

        for doc in docs:
            soup = BeautifulSoup(doc.content_raw_html, "html.parser")
            published_at = _extract_published_at(soup)
            if not published_at:
                continue

            doc.published_at = published_at
            docs_updated += 1

            for signal in doc.signals:
                if signal.published_at is None:
                    signal.published_at = published_at
                    signals_updated += 1

        db.commit()
        logger.info(
            "Done. Documents updated: %d, Signals updated: %d",
            docs_updated,
            signals_updated,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
