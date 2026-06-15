import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.source import Source, CrawlStatus, AnalysisStatus, SourceType
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


def _save_html_event_sections(source: Source, fetch_result, sections: list, db: Session) -> int:
    """Create or update one Document per HTML event section. Returns count of new/changed docs."""
    new = 0
    changed = 0
    now = datetime.now(timezone.utc)

    for i, section in enumerate(sections):
        section_url = f"{fetch_result.final_url}#section-{i}"
        extraction = extract_content(section["html"], url=section_url)

        if len(extraction.markdown.split()) < _MIN_CONTENT_WORDS:
            logger.debug("Skipping HTML event section %d: too short", i)
            continue

        title = section["title"] or extraction.title or "Event"
        published_at = section.get("parsed_date")

        try:
            existing = db.query(Document).filter(Document.url == section_url).first()
            if existing:
                if existing.content_hash == extraction.content_hash:
                    logger.debug("HTML event section unchanged: %s", title)
                    continue
                existing.title = title
                existing.content_markdown = extraction.markdown
                existing.content_raw_html = section["html"]
                existing.content_hash = extraction.content_hash
                existing.crawled_at = now
                existing.is_analysed = False
                if published_at and not existing.published_at:
                    existing.published_at = published_at
                db.commit()
                changed += 1
                logger.info("Updated HTML event section: %s", title)
            else:
                doc = Document(
                    source_id=source.id,
                    url=section_url,
                    title=title,
                    content_markdown=extraction.markdown,
                    content_raw_html=section["html"],
                    content_hash=extraction.content_hash,
                    crawled_at=now,
                    published_at=published_at,
                )
                db.add(doc)
                db.commit()
                new += 1
                logger.info(
                    "New HTML event section: %s (date=%s)",
                    title,
                    published_at.date() if published_at else "unknown",
                )
        except Exception:
            db.rollback()
            logger.exception("Failed to save HTML event section %d for %s", i, section_url)

    logger.info(
        "HTML event sections for %s: %d new, %d changed out of %d sections",
        source.url, new, changed, len(sections),
    )
    return new + changed


def _extract_events_with_llm(
    markdown: str,
    page_url: str,
    linked_urls: List[str] = None,
    known_titles: List[str] = None,
) -> List[dict]:
    """Ask the LLM to extract inline events from a listing page (those without a dedicated linked page)."""
    from app.analyser.client import call_llm

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    linked_note = ""
    if linked_urls:
        urls_str = "\n".join(f"- {u}" for u in linked_urls[:30])
        linked_note = (
            f"\n\nIMPORTANT: The following URLs are already linked from this page and will be "
            f"crawled as separate documents. Do NOT extract events that correspond to these URLs — "
            f"only extract events that appear inline on this page without their own dedicated page:\n{urls_str}\n"
        )

    known_note = ""
    if known_titles:
        titles_str = "\n".join(f"- {t}" for t in known_titles[:50])
        known_note = (
            f"\n\nThe following events have already been recorded and must NOT be returned again:\n{titles_str}\n"
        )

    prompt = f"""You are extracting event data from a competitor's events listing page.

PAGE URL: {page_url}
TODAY: {today}
{linked_note}{known_note}
CONTENT:
{markdown[:5000]}

Extract ONLY events that:
1. Do NOT have a dedicated linked page (inline-only events)
2. Have NOT already been recorded (see list above)

For each new event return a JSON object with exactly these keys:
- "title": official event name (string)
- "date_iso": start date YYYY-MM-DD — infer the year from context or from TODAY if not stated (string or null)
- "date_end_iso": end date YYYY-MM-DD for multi-day events (string or null)
- "location": city/venue or "Online" (string or null)
- "description": 1-2 sentences about the event and the company's role or presence there (string)

Return ONLY a valid JSON array. If no new inline events are found, return [].
"""
    try:
        raw = call_llm(prompt, max_tokens=1500, caller="crawler:event-extraction")
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return []
        events = json.loads(match.group(0))
        return events if isinstance(events, list) else []
    except Exception:
        logger.exception("LLM event extraction failed for %s", page_url)
        return []


def _save_llm_extracted_events(source: Source, fetch_result, llm_events: List[dict], db: Session) -> int:
    """Persist LLM-extracted events as Documents. Returns count of new/changed docs."""
    import html as html_module
    new = 0
    changed = 0
    now = datetime.now(timezone.utc)

    for i, ev in enumerate(llm_events):
        title = ev.get("title") or f"Event {i}"
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        event_url = f"{fetch_result.final_url}#llm-event-{slug}"

        date_iso = ev.get("date_iso")
        published_at = None
        if date_iso:
            try:
                published_at = datetime.strptime(date_iso[:10], "%Y-%m-%d")
            except ValueError:
                pass

        parts = [f"<html><body><main><h1>{html_module.escape(title)}</h1><ul>"]
        if ev.get("date_iso"):
            end = ev.get("date_end_iso")
            date_str = ev["date_iso"] + (f" – {end}" if end else "")
            parts.append(f"<li><strong>Datum:</strong> {html_module.escape(date_str)}</li>")
        if ev.get("location"):
            parts.append(f"<li><strong>Ort:</strong> {html_module.escape(str(ev['location']))}</li>")
        if ev.get("description"):
            parts.append(f"<li><strong>Beschreibung:</strong> {html_module.escape(str(ev['description']))}</li>")
        parts.append("</ul></main></body></html>")
        event_html = "".join(parts)

        extraction = extract_content(event_html, url=event_url)
        if len(extraction.markdown.split()) < _MIN_CONTENT_WORDS:
            continue

        try:
            existing = db.query(Document).filter(Document.url == event_url).first()
            if existing:
                if existing.content_hash == extraction.content_hash:
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
                logger.info("Updated LLM event: %s", title)
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
                logger.info("New LLM event: %s (date=%s)", title, date_iso or "unknown")
        except Exception:
            db.rollback()
            logger.exception("Failed to save LLM event: %s", title)

    logger.info("LLM events for %s: %d new, %d changed out of %d extracted", source.url, new, changed, len(llm_events))
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

    js_rendered = False
    if settings.js_rendering_enabled and _needs_js_rendering(
        fetch_result.html, fetch_result.final_url
    ):
        emit({"type": "step", "source_id": source.id, "step": "js_rendering"})
        js_result = fetch_url_js(fetch_result.final_url)
        if js_result is not None:
            fetch_result = js_result
            js_rendered = True
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
    elif source.source_type == SourceType.events:
        from app.crawler.extractor import split_event_sections
        sections = split_event_sections(fetch_result.html, fetch_result.final_url)
        if not sections and not js_rendered and settings.js_rendering_enabled:
            word_count = len(extraction.markdown.split())
            if word_count < _MIN_CONTENT_WORDS * 3:
                logger.info(
                    "Events source %s: sparse content (%d words) and no HTML sections — retrying with JS rendering",
                    source.url, word_count,
                )
                emit({"type": "step", "source_id": source.id, "step": "js_rendering"})
                js_result = fetch_url_js(fetch_result.final_url)
                if js_result is not None:
                    fetch_result = js_result
                    extraction = extract_content(fetch_result.html, url=fetch_result.final_url)
                    sections = split_event_sections(fetch_result.html, fetch_result.final_url)
                else:
                    logger.warning("JS rendering retry failed for events source %s", source.url)
        if sections:
            logger.info(
                "Events source %s: found %d HTML sections — creating per-section documents",
                source.url, len(sections),
            )
            n = _save_html_event_sections(source, fetch_result, sections, db)
            result["new_documents"] += n
            if n > 0:
                source.crawl_status = CrawlStatus.new
                source.analysis_status = AnalysisStatus.pending
            else:
                source.crawl_status = CrawlStatus.known
            db.commit()
        else:
            if source.content_hash and source.content_hash == extraction.content_hash:
                logger.info("Events source %s: listing page unchanged, skipping LLM extraction", source.url)
                source.crawl_status = CrawlStatus.known
                db.commit()
            else:
                from app.crawler.discovery import _extract_content_area_links
                content_links = _extract_content_area_links(fetch_result.html, fetch_result.final_url)
                known_titles = [
                    doc.title for doc in
                    db.query(Document.title)
                    .filter(
                        Document.source_id == source.id,
                        Document.url.like(f"{fetch_result.final_url}#llm-event-%"),
                        Document.title.isnot(None),
                    )
                    .all()
                    if doc.title
                ]
                logger.info(
                    "Events source %s: no HTML sections — trying LLM extraction "
                    "(%d linked pages, %d known events to exclude)",
                    source.url, len(content_links), len(known_titles),
                )
                llm_events = _extract_events_with_llm(
                    extraction.markdown,
                    fetch_result.final_url,
                    linked_urls=content_links,
                    known_titles=known_titles,
                )
                if llm_events:
                    logger.info("Events source %s: LLM extracted %d inline events", source.url, len(llm_events))
                    n = _save_llm_extracted_events(source, fetch_result, llm_events, db)
                    result["new_documents"] += n
                    source.content_hash = extraction.content_hash
                    if n > 0:
                        source.crawl_status = CrawlStatus.new
                        source.analysis_status = AnalysisStatus.pending
                    else:
                        source.crawl_status = CrawlStatus.known
                    db.commit()
                else:
                    logger.info(
                        "Events source %s: no inline events found via LLM — falling back to single document",
                        source.url,
                    )
            word_count = len(extraction.markdown.split())
            if word_count < _MIN_CONTENT_WORDS:
                logger.info(
                    "Skipping document for %s: only %d words after extraction",
                    fetch_result.final_url, word_count,
                )
                result["skipped"] += 1
            else:
                existing_by_url = db.query(Document).filter(Document.url == fetch_result.final_url).first()
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
