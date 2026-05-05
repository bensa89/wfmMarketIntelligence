import logging
import time
from typing import Callable, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.source import Source, CrawlStatus
from app.models.document import Document
from app.crawler.fetcher import fetch_url
from app.crawler.js_fetcher import fetch_url_js
from app.crawler.extractor import extract_content
from app.crawler.discovery import (
    discover_and_crawl,
    _extract_internal_links,
    _is_article_content,
)
from app.config import settings

logger = logging.getLogger(__name__)

_JS_RENDER_LINK_THRESHOLD = 5


def _looks_like_js_app(html: str) -> bool:
    js_indicators = [
        '<div id="root"',
        '<div id="__next"',
        '<div id="app"',
        "ng-app",
        "data-reactroot",
        "data-reactid",
        '<script id="__NEXT_DATA__"',
        "___gatsby",
        "/gatsby.js",
        "/gatsby-static/",
        "window.___GATSBY",
    ]
    lower = html.lower()
    return any(ind.lower() in lower for ind in js_indicators)


def _needs_js_rendering(html: str, url: str) -> bool:
    links = _extract_internal_links(html, url)
    if len(links) < _JS_RENDER_LINK_THRESHOLD:
        return True
    return _looks_like_js_app(html)


def run_crawl_source(
    source: Source,
    db: Session,
    analyse: bool = True,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> Dict:
    def emit(event: dict):
        if progress_callback:
            progress_callback(event)

    result = {
        "source_id": source.id,
        "new_documents": 0,
        "skipped": 0,
        "errors": 0,
        "discovery": {},
    }

    fetch_ms = 0
    extract_ms = 0
    analyse_ms = 0
    discover_ms = 0

    emit({"type": "step", "source_id": source.id, "step": "fetching"})
    t0 = time.monotonic()
    fetch_result = fetch_url(source.url)
    fetch_ms = int((time.monotonic() - t0) * 1000)
    emit(
        {
            "type": "step_timing",
            "source_id": source.id,
            "step": "fetching",
            "duration_ms": fetch_ms,
        }
    )
    if fetch_result is None:
        result["errors"] += 1
        emit({"type": "error", "source_id": source.id, "message": "Fetch failed"})
        return result

    if settings.js_rendering_enabled and _needs_js_rendering(
        fetch_result.html, fetch_result.final_url
    ):
        emit({"type": "step", "source_id": source.id, "step": "js_rendering"})
        js_result = fetch_url_js(fetch_result.final_url)
        if js_result is not None:
            fetch_result = js_result
        else:
            logger.warning("JS rendering failed for %s, using static HTML", source.url)

    emit({"type": "step", "source_id": source.id, "step": "extracting"})
    t0 = time.monotonic()
    extraction = extract_content(fetch_result.html, url=fetch_result.final_url)
    extract_ms = int((time.monotonic() - t0) * 1000)
    emit(
        {
            "type": "step_timing",
            "source_id": source.id,
            "step": "extracting",
            "duration_ms": extract_ms,
        }
    )

    existing_by_url = (
        db.query(Document).filter(Document.url == fetch_result.final_url).first()
    )
    if existing_by_url:
        if existing_by_url.content_hash == extraction.content_hash:
            source.crawl_status = CrawlStatus.known
            result["skipped"] += 1
        else:
            existing_by_url.title = extraction.title
            existing_by_url.content_markdown = extraction.markdown
            existing_by_url.content_raw_html = fetch_result.html.replace("\x00", "")
            existing_by_url.content_hash = extraction.content_hash
            existing_by_url.crawled_at = datetime.now(timezone.utc)
            existing_by_url.is_analysed = False
            if extraction.published_at and not existing_by_url.published_at:
                existing_by_url.published_at = extraction.published_at
            source.crawl_status = CrawlStatus.changed
            source.content_hash = extraction.content_hash
            source.last_changed_at = datetime.now(timezone.utc)
            db.commit()
            result["skipped"] += 1

            if analyse and _is_article_content(fetch_result.html):
                from app.analyser.pipeline import analyse_document

                db.refresh(existing_by_url)
                emit({"type": "step", "source_id": source.id, "step": "analysing"})
                t0 = time.monotonic()
                try:
                    analyse_document(existing_by_url, source.company_id, db)
                except Exception as e:
                    result["errors"] += 1
                    emit(
                        {
                            "type": "error",
                            "source_id": source.id,
                            "message": f"Analysis failed: {e}",
                        }
                    )
                    db.rollback()
                analyse_ms = int((time.monotonic() - t0) * 1000)
                emit(
                    {
                        "type": "step_timing",
                        "source_id": source.id,
                        "step": "analysing",
                        "duration_ms": analyse_ms,
                    }
                )
    else:
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=datetime.now(timezone.utc),
            published_at=extraction.published_at,
        )
        db.add(doc)
        source.crawl_status = CrawlStatus.new
        source.content_hash = extraction.content_hash
        db.commit()
        result["new_documents"] += 1

        if analyse and _is_article_content(fetch_result.html):
            from app.analyser.pipeline import analyse_document

            db.refresh(doc)
            emit({"type": "step", "source_id": source.id, "step": "analysing"})
            t0 = time.monotonic()
            try:
                analyse_document(doc, source.company_id, db)
            except Exception as e:
                result["errors"] += 1
                emit(
                    {
                        "type": "error",
                        "source_id": source.id,
                        "message": f"Analysis failed: {e}",
                    }
                )
                db.rollback()
            analyse_ms = int((time.monotonic() - t0) * 1000)
            emit(
                {
                    "type": "step_timing",
                    "source_id": source.id,
                    "step": "analysing",
                    "duration_ms": analyse_ms,
                }
            )

    emit({"type": "step", "source_id": source.id, "step": "discovering"})
    t0 = time.monotonic()
    result["discovery"] = discover_and_crawl(
        source, fetch_result.html, db, analyse=analyse, progress_callback=emit
    )
    discover_ms = int((time.monotonic() - t0) * 1000)
    emit(
        {
            "type": "step_timing",
            "source_id": source.id,
            "step": "discovering",
            "duration_ms": discover_ms,
        }
    )

    source.last_crawled_at = datetime.now(timezone.utc)
    db.commit()

    result["timings"] = {
        "fetch_ms": fetch_ms,
        "extract_ms": extract_ms,
        "analyse_ms": analyse_ms,
        "discover_ms": discover_ms,
    }

    return result
