import logging
import re

from typing import Callable, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.source import Source, AnalysisStatus
from app.models.document import Document
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.models.signal import Signal
from app.crawler.fetcher import fetch_url
from app.crawler.js_fetcher import fetch_url_js
from app.crawler.extractor import extract_content
from app.config import settings

logger = logging.getLogger(__name__)

_CONTENT_PREFIXES = (
    "/news/",
    "/blog/",
    "/press/",
    "/insights/",
    "/resources/",
    "/product/",
)
_CONTENT_SEGMENTS = {"news", "blog", "press", "insights", "resources", "product"}
_NAVIGATION_SEGMENTS = {
    "de",
    "en",
    "fr",
    "es",
    "it",
    "nl",
    "pt",
    "ru",
    "ja",
    "zh",
    "ko",
    "about",
    "contact",
    "imprint",
    "privacy",
    "legal",
    "terms",
    "search",
    "login",
    "signup",
    "cart",
    "checkout",
}
_DATE_PATTERN = re.compile(r"/\d{4}(/\d{2})?/")
_MAX_PAGES_PER_RUN = 50


def _is_child_path(child_url: str, parent_url: str) -> bool:
    child_path = urlparse(child_url).path.rstrip("/")
    parent_path = urlparse(parent_url).path.rstrip("/")
    if not parent_path:
        return True
    return child_path.startswith(parent_path + "/")


def _is_article_url(url: str, seed_url: str = "") -> bool:
    path = urlparse(url).path
    segments = [s for s in path.split("/") if s]
    if _DATE_PATTERN.search(path):
        return True
    if any(path.startswith(p) for p in _CONTENT_PREFIXES):
        return True
    if any(seg in _CONTENT_SEGMENTS for seg in segments):
        return True
    if seed_url:
        return _is_child_path(url, seed_url) and len(segments) >= 2
    clean_segments = [s for s in segments if s not in _NAVIGATION_SEGMENTS]
    if len(clean_segments) >= 3:
        return True
    return False


def _is_article_content(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("article"):
        return True
    body = soup.find("body") or soup
    main = soup.find("main") or body
    text = main.get_text(" ", strip=True)
    total_words = len(text.split())
    if total_words < 200:
        return False
    nav = soup.find("nav")
    if nav and total_words < 600:
        nav_text = nav.get_text(" ", strip=True)
        body_text = body.get_text(" ", strip=True)
        if len(nav_text.split()) / max(len(body_text.split()), 1) > 0.3:
            return False
    return True


def _extract_internal_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    base_netloc = urlparse(base_url).netloc
    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != base_netloc:
            continue
        links.add(abs_url.split("#")[0])
    return list(links)


def _get_robot_parser(base_url: str) -> RobotFileParser:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        pass
    return rp


def _update_page_relevance(page: DiscoveredPage, url: str, db: Session) -> None:
    doc = db.query(Document).filter(Document.url == url).first()
    if not doc:
        logger.debug("No document found for relevance update: %s", url)
        return
    signals = db.query(Signal).filter(Signal.document_id == doc.id).all()
    if not signals:
        logger.info("No signals found for document %s, skipping relevance update", url)
        return
    scores = [s.relevance_score or 0 for s in signals]
    page.last_signal_relevance = max(scores)
    logger.info(
        "Page relevance for %s: scores=%s, max=%.2f",
        url,
        [round(s, 2) for s in scores],
        max(scores),
    )
    if all(score < 0.3 for score in scores):
        page.is_active = False
        page.status = DiscoveredPageStatus.ignored
        logger.warning(
            "Deactivating page %s — all relevance scores below 0.3: %s",
            url,
            [round(s, 2) for s in scores],
        )
    db.commit()


def discover_and_crawl(
    source: Source,
    seed_html: str,
    db: Session,
    analyse: bool = True,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> Dict:
    if settings.discovery_depth == 0:
        logger.info(
            "Discovery disabled (discovery_depth=0), skipping for source %s", source.url
        )
        return {"discovered": 0, "new": 0, "changed": 0, "known": 0}

    result = {"discovered": 0, "new": 0, "changed": 0, "known": 0}
    robot_parser = _get_robot_parser(source.url)

    known_inactive: Set[str] = {
        p.url
        for p in db.query(DiscoveredPage)
        .filter(
            DiscoveredPage.source_id == source.id, DiscoveredPage.is_active.is_(False)
        )
        .all()
    }
    logger.info(
        "Discovery for source %s: %d known inactive pages, discovery_depth=%d",
        source.url,
        len(known_inactive),
        settings.discovery_depth,
    )
    if known_inactive:
        logger.debug("Known inactive URLs: %s", known_inactive)

    all_links = _extract_internal_links(seed_html, source.url)
    logger.info(
        "Discovery for source %s: %d internal links found in seed HTML",
        source.url,
        len(all_links),
    )

    child_links: List[tuple] = []
    other_links: List[tuple] = []
    skipped_not_article = 0
    skipped_inactive = 0
    for url in all_links:
        is_article = _is_article_url(url, seed_url=source.url)
        if url in known_inactive:
            skipped_inactive += 1
            logger.debug("Skipping inactive URL: %s", url)
            continue
        if not is_article:
            skipped_not_article += 1
            continue
        if _is_child_path(url, source.url):
            child_links.append((url, 1))
        else:
            other_links.append((url, 1))

    logger.info(
        "Discovery for source %s: %d child links, %d other links queued "
        "(%d skipped as non-article, %d skipped as inactive)",
        source.url,
        len(child_links),
        len(other_links),
        skipped_not_article,
        skipped_inactive,
    )

    queue = child_links + other_links
    visited: Set[str] = set()
    pages_crawled = 0

    while queue and pages_crawled < _MAX_PAGES_PER_RUN:
        url, depth = queue.pop(0)
        if url in visited:
            logger.debug("Skipping already visited URL: %s", url)
            continue
        if depth > settings.discovery_depth:
            logger.debug(
                "Skipping URL (depth %d > discovery_depth %d): %s",
                depth,
                settings.discovery_depth,
                url,
            )
            continue
        visited.add(url)

        if source.respect_robots_txt and not robot_parser.can_fetch("*", url):
            logger.info("Blocked by robots.txt: %s", url)
            continue

        if url in known_inactive:
            logger.debug("Skipping inactive URL (second check): %s", url)
            continue

        logger.info(
            "Fetching discovered page [depth=%d, crawled=%d/%d]: %s",
            depth,
            pages_crawled + 1,
            _MAX_PAGES_PER_RUN,
            url,
        )
        fetch_result = fetch_url(url)
        if fetch_result is None:
            logger.warning("Fetch failed for discovered page: %s", url)
            continue

        if (
            settings.js_rendering_enabled
            and len(_extract_internal_links(fetch_result.html, url)) < 5
        ):
            logger.info("JS rendering fallback for discovered page: %s", url)
            js_result = fetch_url_js(url)
            if js_result is not None:
                fetch_result = js_result
            else:
                logger.warning(
                    "JS rendering fallback failed for %s, using static HTML", url
                )

        pages_crawled += 1
        if progress_callback:
            progress_callback(
                {
                    "type": "discovery_progress",
                    "source_id": source.id,
                    "pages_found": len(visited) + len(queue),
                    "pages_crawled": pages_crawled,
                    "max_pages": _MAX_PAGES_PER_RUN,
                    "current_url": url,
                }
            )

        if not _is_article_content(fetch_result.html):
            logger.info(
                "Skipping non-article content (too short or nav-heavy): %s", url
            )
            continue

        extraction = extract_content(fetch_result.html, url=fetch_result.final_url)
        now = datetime.now(timezone.utc)
        final_url = fetch_result.final_url
        logger.info(
            "Extracted content from %s: title='%s', words=%d, hash=%s",
            final_url,
            extraction.title[:80] if extraction.title else "(none)",
            len(extraction.markdown.split()) if extraction.markdown else 0,
            extraction.content_hash[:12] if extraction.content_hash else "(none)",
        )

        try:
            existing = (
                db.query(DiscoveredPage).filter(DiscoveredPage.url == final_url).first()
            )

            if existing is None:
                page = DiscoveredPage(
                    source_id=source.id,
                    url=final_url,
                    title=extraction.title,
                    depth=depth,
                    status=DiscoveredPageStatus.new,
                    content_hash=extraction.content_hash,
                    discovered_at=now,
                    last_crawled_at=now,
                )
                db.add(page)
                db.commit()
                result["new"] += 1
                result["discovered"] += 1
                logger.info("New discovered page: %s (depth=%d)", final_url, depth)

                if analyse:
                    _save_document_only(source, fetch_result, extraction, now, db)
                    source.analysis_status = AnalysisStatus.pending
                    db.commit()

            elif not existing.is_active:
                existing.status = DiscoveredPageStatus.ignored
                existing.last_crawled_at = now
                db.commit()
                logger.info("Skipping inactive page in DB: %s", final_url)

            elif existing.content_hash != extraction.content_hash:
                existing.status = DiscoveredPageStatus.changed
                existing.content_hash = extraction.content_hash
                existing.last_crawled_at = now
                existing.last_changed_at = now
                db.commit()
                result["changed"] += 1
                logger.info("Changed discovered page: %s", final_url)

                if analyse:
                    _save_document_only(source, fetch_result, extraction, now, db)
                    source.analysis_status = AnalysisStatus.pending
                    db.commit()

            else:
                existing.status = DiscoveredPageStatus.known
                existing.last_crawled_at = now
                db.commit()
                result["known"] += 1
                logger.info("Known (unchanged) discovered page: %s", final_url)
        except Exception:
            db.rollback()
            logger.exception("Error processing discovered page %s", final_url)

        if depth < settings.discovery_depth:
            sub_links = _extract_internal_links(fetch_result.html, final_url)
            new_enqueued = 0
            for next_url in sub_links:
                if next_url in visited:
                    continue
                if next_url in known_inactive:
                    continue
                if not _is_article_url(next_url, seed_url=source.url):
                    continue
                queue.append((next_url, depth + 1))
                new_enqueued += 1
            if new_enqueued:
                logger.info(
                    "Enqueued %d new sub-links from %s (depth %d→%d)",
                    new_enqueued,
                    final_url,
                    depth,
                    depth + 1,
                )

    logger.info(
        "Discovery complete for source %s: discovered=%d, new=%d, changed=%d, known=%d",
        source.url,
        result["discovered"],
        result["new"],
        result["changed"],
        result["known"],
    )
    return result


def _save_document_only(source, fetch_result, extraction, now, db):
    existing_doc = (
        db.query(Document).filter(Document.url == fetch_result.final_url).first()
    )
    if existing_doc:
        existing_doc.content_markdown = extraction.markdown
        existing_doc.content_hash = extraction.content_hash
        existing_doc.content_raw_html = fetch_result.html.replace("\x00", "")
        existing_doc.crawled_at = now
        existing_doc.is_analysed = False
        if extraction.published_at and not existing_doc.published_at:
            existing_doc.published_at = extraction.published_at
        db.commit()
    else:
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=now,
            published_at=extraction.published_at,
        )
        db.add(doc)
        db.commit()
