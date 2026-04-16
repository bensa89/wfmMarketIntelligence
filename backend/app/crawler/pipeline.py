from typing import Dict
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.source import Source
from app.models.document import Document
from app.crawler.fetcher import fetch_url
from app.crawler.extractor import extract_content


def run_crawl_source(source: Source, db: Session, analyse: bool = True) -> Dict:
    result = {"source_id": source.id, "new_documents": 0, "skipped": 0, "errors": 0}

    fetch_result = fetch_url(source.url)
    if fetch_result is None:
        result["errors"] += 1
        return result

    extraction = extract_content(fetch_result.html, url=fetch_result.final_url)

    existing = (
        db.query(Document)
        .filter(Document.content_hash == extraction.content_hash)
        .first()
    )
    if existing:
        result["skipped"] += 1
    else:
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        db.commit()
        result["new_documents"] += 1

        if analyse:
            from app.analyser.pipeline import analyse_document

            db.refresh(doc)
            analyse_document(doc, source.company_id, db)

    source.last_crawled_at = datetime.now(timezone.utc)
    db.commit()

    return result
