import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from app.database import SessionLocal
from app.models.context import InternalCompanyContext
from app.analyser.pipeline import _build_context_dict

logger = logging.getLogger(__name__)

_JS_RENDER_LINK_THRESHOLD = 5
_MIN_CONTENT_WORDS = 20

# Date field names used across event platforms (lowercase)
_EVENT_DATE_KEYS = frozenset({
    "startdate", "start_date", "date", "starttime", "start",
    "eventdate", "event_date", "begindate", "begin_date",
    "startdateutc", "enddateutc", "startdatetime", "enddatetime",
    "start_date_utc", "end_date_utc",
})
_EVENT_TITLE_KEYS = frozenset({"title", "name", "subject", "eventtitle", "event_title"})


def _parse_event_date(ev: dict) -> Optional[datetime]:
    for k in ev:
        if k.lower() in _EVENT_DATE_KEYS and ev[k]:
            try:
                val = str(ev[k]).replace("Z", "+00:00")
                dt = datetime.fromisoformat(val)
                if dt.tzinfo:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except Exception:
                pass
    return None


def _event_to_html(ev: dict) -> str:
    import html as html_module
    title = next(
        (str(ev[k]) for k in ev if k.lower() in _EVENT_TITLE_KEYS and ev[k]),
        "Event",
    )
    parts = [f"<html><body><main><h1>{html_module.escape(title)}</h1><ul>"]
    for k, v in ev.items():
        if k.lower() in _EVENT_TITLE_KEYS:
            continue
        if isinstance(v, (str, int, float)) and v != "" and v is not False:
            parts.append(f"<li><strong>{html_module.escape(k)}:</strong> {html_module.escape(str(v))}</li>")
        elif isinstance(v, dict):
            label = v.get("name") or v.get("city") or v.get("value")
            if label:
                parts.append(f"<li><strong>{html_module.escape(k)}:</strong> {html_module.escape(str(label))}</li>")
    parts.append("</ul></main></body></html>")
    return "".join(parts)


def _save_event_documents(source: Source, fetch_result, db: Session) -> int:
    """Create or update one Document per intercepted event. Returns count of new/changed docs."""
    new = 0
    changed = 0
    now = datetime.now(timezone.utc)

    for i, ev in enumerate(fetch_result.events):
        event_id = ev.get("id") or str(i)
        event_url = f"{fetch_result.final_url}#event-{event_id}"
        event_html = _event_to_html(ev)
        extraction = extract_content(event_html, url=event_url)

        if len(extraction.markdown.split()) < _MIN_CONTENT_WORDS:
            logger.debug("Skipping event %s: too short (%d words)", event_id, len(extraction.markdown.split()))
            continue

        published_at = _parse_event_date(ev)
        title = next(
            (str(ev[k]) for k in ev if k.lower() in _EVENT_TITLE_KEYS and ev[k]),
            extraction.title or "Event",
        )

        try:
            existing = db.query(Document).filter(Document.url == event_url).first()
            if existing:
                if existing.content_hash == extraction.content_hash:
                    logger.debug("Event unchanged: %s", title)
                    continue
                existing.title = title
                existing.content_markdown = extraction.markdown
                existing.content_raw_html = event_html
                existing.content_hash = extraction.content_hash
                existing.crawled_at = now
                existing.is_analysed = False
                if published_at and not existing.published_at:
                    existing.published_at = published_at
                db.commit()
                changed += 1
                logger.info("Updated event document: %s", title)
            else:
                doc = Document(
                    source_id=source.id,
                    url=event_url,
                    title=title,
                    content_markdown=extraction.markdown,
                    content_raw_html=event_html,
                    content_hash=extraction.content_hash,
                    crawled_at=now,
                    published_at=published_at,
                )
                db.add(doc)
                db.commit()
                new += 1
                logger.info(
                    "New event document: %s (date=%s)",
                    title,
                    published_at.date() if published_at else "unknown",
                )
        except Exception:
            db.rollback()
            logger.exception("Failed to save event document for %s", event_url)

    logger.info(
        "Event documents for %s: %d new, %d changed, %d total events",
        source.url,
        new,
        changed,
        len(fetch_result.events),
    )
    return new + changed


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


def _analyse_doc_worker(
    doc_id: str,
    company_id: str,
    context: dict,
    db_factory: Optional[Callable] = None,
) -> tuple[str, bool]:
    factory = db_factory if db_factory is not None else SessionLocal
    db = factory()
    try:
        from app.analyser.pipeline import analyse_document
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            analyse_document(doc, company_id, db, preloaded_context=context)
        return doc_id, True
    except Exception as e:
        logger.exception("Analysis worker failed for doc %s: %s", doc_id, e)
        db.rollback()
        return doc_id, False
    finally:
        db.close()


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

    if fetch_result.events:
        # Event page: create one document per intercepted event so each signal gets its own event_date
        n = _save_event_documents(source, fetch_result, db)
        result["new_documents"] += n
        if n > 0:
            source.crawl_status = CrawlStatus.new
            source.analysis_status = AnalysisStatus.pending
        else:
            source.crawl_status = CrawlStatus.known
        db.commit()
    else:
        word_count = len(extraction.markdown.split())
        if word_count < _MIN_CONTENT_WORDS:
            logger.info(
                "Skipping document for %s: only %d words after extraction",
                fetch_result.final_url,
                word_count,
            )
            result["skipped"] += 1
        else:
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
                    result["new_documents"] += 1
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

    result["new_documents"] += result["discovery"].get("new", 0) + result[
        "discovery"
    ].get("changed", 0)

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

    for page in (
        db.query(DiscoveredPage)
        .filter(
            DiscoveredPage.source_id == source.id,
            DiscoveredPage.analysis_status == "pending",
        )
        .all()
    ):
        page.analysis_status = "analysing"
    db.commit()

    total = len(unanalysed)
    t0 = time.monotonic()

    ctx_record = db.query(InternalCompanyContext).first()
    context = _build_context_dict(ctx_record)

    completed_count = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=settings.analysis_concurrency) as executor:
        futures = {
            executor.submit(_analyse_doc_worker, doc.id, source.company_id, context): doc
            for doc in unanalysed
        }
        for future in as_completed(futures):
            doc_id, success = future.result()
            completed_doc = futures[future]
            with lock:
                completed_count += 1
                current = completed_count
            if success:
                result["analysed"] += 1
            else:
                result["errors"] += 1
            emit(
                {
                    "type": "analysis_progress",
                    "source_id": source.id,
                    "current": current,
                    "total": total,
                    "url": completed_doc.url,
                }
            )

    result["analyse_ms"] = int((time.monotonic() - t0) * 1000)

    # Post-pool: update DiscoveredPage statuses in main thread
    for doc in unanalysed:
        page = db.query(DiscoveredPage).filter(DiscoveredPage.url == doc.url).first()
        if page:
            try:
                _update_page_relevance(page, doc.url, db)
                page.analysis_status = "analysed"
            except Exception as e:
                logger.warning("DiscoveredPage update failed for %s: %s", doc.url, e)
                page.analysis_status = "analysis_failed"
    db.commit()

    source.analysis_status = (
        AnalysisStatus.analysed
        if result["errors"] == 0
        else AnalysisStatus.analysis_failed
    )
    db.commit()

    return result
