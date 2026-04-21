import logging
import re
import time
from typing import List, Set, Dict
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.source import Source
from app.models.document import Document
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.models.signal import Signal
from app.crawler.fetcher import fetch_url
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
        return
    signals = db.query(Signal).filter(Signal.document_id == doc.id).all()
    if not signals:
        return
    scores = [s.relevance_score or 0 for s in signals]
    page.last_signal_relevance = max(scores)
    if all(score < 0.3 for score in scores):
        page.is_active = False
        page.status = DiscoveredPageStatus.ignored
    db.commit()


def discover_and_crawl(
    source: Source, seed_html: str, db: Session, analyse: bool = True
) -> Dict:
    if settings.discovery_depth == 0:
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

    child_links: List[tuple] = []
    other_links: List[tuple] = []
    for url in _extract_internal_links(seed_html, source.url):
        if not _is_article_url(url, seed_url=source.url) or url in known_inactive:
            continue
        if _is_child_path(url, source.url):
            child_links.append((url, 1))
        else:
            other_links.append((url, 1))

    queue = child_links + other_links
    visited: Set[str] = set()
    pages_crawled = 0

    while queue and pages_crawled < _MAX_PAGES_PER_RUN:
        url, depth = queue.pop(0)
        if url in visited or depth > settings.discovery_depth:
            continue
        visited.add(url)

        if not robot_parser.can_fetch("*", url):
            continue

        if url in known_inactive:
            continue

        time.sleep(1)
        fetch_result = fetch_url(url)
        if fetch_result is None:
            continue

        pages_crawled += 1

        if not _is_article_content(fetch_result.html):
            continue

        extraction = extract_content(fetch_result.html, url=fetch_result.final_url)
        now = datetime.now(timezone.utc)
        final_url = fetch_result.final_url

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

                if analyse:
                    _save_and_analyse(source, fetch_result, extraction, now, db)
                    _update_page_relevance(page, final_url, db)

            elif not existing.is_active:
                existing.status = DiscoveredPageStatus.ignored
                existing.last_crawled_at = now
                db.commit()

            elif existing.content_hash != extraction.content_hash:
                existing.status = DiscoveredPageStatus.changed
                existing.content_hash = extraction.content_hash
                existing.last_crawled_at = now
                existing.last_changed_at = now
                db.commit()
                result["changed"] += 1

                if analyse:
                    _save_and_analyse(source, fetch_result, extraction, now, db)
                    _update_page_relevance(existing, final_url, db)

            else:
                existing.status = DiscoveredPageStatus.known
                existing.last_crawled_at = now
                db.commit()
                result["known"] += 1
        except Exception:
            db.rollback()
            logger.exception("Error processing discovered page %s", final_url)

        if depth < settings.discovery_depth:
            for next_url in _extract_internal_links(fetch_result.html, final_url):
                if (
                    next_url not in visited
                    and next_url not in known_inactive
                    and _is_article_url(next_url, seed_url=source.url)
                ):
                    queue.append((next_url, depth + 1))

    return result


def _save_and_analyse(source, fetch_result, extraction, now, db):
    from app.analyser.pipeline import analyse_document

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
        db.refresh(existing_doc)
        analyse_document(existing_doc, source.company_id, db)
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
        db.refresh(doc)
        analyse_document(doc, source.company_id, db)
