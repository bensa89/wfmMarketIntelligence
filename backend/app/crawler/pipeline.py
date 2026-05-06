import logging
import time
from typing import Callable, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.source import Source, CrawlStatus, AnalysisStatus
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
            source.analysis_status = AnalysisStatus.pending
            db.commit()
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
            published_at=extraction.published_at,
        )
        db.add(doc)
        source.crawl_status = CrawlStatus.new
        source.content_hash = extraction.content_hash
        source.analysis_status = AnalysisStatus.pending
        db.commit()
        result["new_documents"] += 1

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


def analyse_unanalysed_for_source(
    source: Source,
    db: Session,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> Dict:
    from app.analyser.pipeline import analyse_document
    from app.models.discovered_page import DiscoveredPage
    from app.crawler.discovery import _update_page_relevance

    def emit(event: dict):
        if progress_callback:
            progress_callback(event)

    result = {"source_id": source.id, "analysed": 0, "errors": 0, "analyse_ms": 0}

    source.analysis_status = AnalysisStatus.analysing
    db.commit()

    unanalysed = (
        db.query(Document)
        .filter(
            Document.source_id == source.id,
            Document.is_analysed == False,
        )
        .order_by(Document.crawled_at.asc())
        .all()
    )

    if not unanalysed:
        source.analysis_status = AnalysisStatus.analysed
        db.commit()
        return result

    total = len(unanalysed)
    t0 = time.monotonic()

    for i, doc in enumerate(unanalysed):
        emit(
            {
                "type": "analysis_progress",
                "source_id": source.id,
                "current": i + 1,
                "total": total,
                "url": doc.url,
            }
        )
        try:
            analyse_document(doc, source.company_id, db)
            result["analysed"] += 1

            page = (
                db.query(DiscoveredPage).filter(DiscoveredPage.url == doc.url).first()
            )
            if page:
                _update_page_relevance(page, doc.url, db)
        except Exception as e:
            result["errors"] += 1
            logger.exception("Analysis failed for doc %s: %s", doc.id, e)
            db.rollback()

    result["analyse_ms"] = int((time.monotonic() - t0) * 1000)

    source.analysis_status = (
        AnalysisStatus.analysed
        if result["errors"] == 0
        else AnalysisStatus.analysis_failed
    )
    db.commit()

    return result
