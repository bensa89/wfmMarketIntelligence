import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from bs4 import BeautifulSoup
from markdownify import markdownify


@dataclass
class ExtractionResult:
    title: Optional[str]
    markdown: str
    content_hash: str
    published_at: Optional[datetime] = None


def _parse_date_str(s: str) -> Optional[datetime]:
    """Parse an ISO-8601 date string into a naive UTC datetime."""
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _extract_published_at(soup: BeautifulSoup) -> Optional[datetime]:
    # 1. JSON-LD datePublished
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    date_str = item.get("datePublished")
                    if date_str:
                        dt = _parse_date_str(str(date_str))
                        if dt:
                            return dt
        except (json.JSONDecodeError, AttributeError):
            pass

    # 2. Open Graph article:published_time
    meta = soup.find("meta", attrs={"property": "article:published_time"})
    if meta and meta.get("content"):
        dt = _parse_date_str(meta["content"])
        if dt:
            return dt

    # 3. pubdate / date / DC.date meta
    for name in ("pubdate", "date", "DC.date"):
        meta = soup.find("meta", attrs={"name": name})
        if meta and meta.get("content"):
            dt = _parse_date_str(meta["content"])
            if dt:
                return dt

    # 4. First <time datetime="...">
    time_el = soup.find("time", attrs={"datetime": True})
    if time_el and time_el.get("datetime"):
        dt = _parse_date_str(time_el["datetime"])
        if dt:
            return dt

    return None


def extract_content(html: str, url: str = "") -> ExtractionResult:
    html = html.replace("\x00", "")
    soup = BeautifulSoup(html, "html.parser")

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    published_at = _extract_published_at(soup)

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("body") or soup

    markdown = markdownify(str(main), heading_style="ATX", strip=["a"]).strip()
    markdown = "\n".join(line for line in markdown.splitlines() if line.strip())

    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    return ExtractionResult(
        title=title,
        markdown=markdown,
        content_hash=content_hash,
        published_at=published_at,
    )


_DATE_RE = re.compile(
    r"\b\d{1,2}\.\s*(?:januar|februar|märz|april|mai|juni|juli|august|"
    r"september|oktober|november|dezember|january|february|march|"
    r"april|may|june|july|august|september|october|november|december)"
    r"\s+\d{4}\b"
    r"|\b\d{1,2}\.\d{1,2}\.\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)

_MONTH_MAP = {
    "januar": "01", "februar": "02", "märz": "03", "april": "04",
    "mai": "05", "juni": "06", "juli": "07", "august": "08",
    "september": "09", "oktober": "10", "november": "11", "dezember": "12",
    "january": "01", "february": "02", "march": "03",
    "may": "05", "june": "06", "july": "07",
    "october": "10",
}


def _parse_date_from_text(text: str) -> Optional[datetime]:
    m = _DATE_RE.search(text)
    if not m:
        return None
    raw = m.group(0).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    parts = re.split(r"[\.\s]+", raw.lower())
    parts = [p for p in parts if p]
    if len(parts) == 3:
        day, month_name, year = parts
        month_num = _MONTH_MAP.get(month_name)
        if month_num:
            try:
                return datetime.strptime(f"{day}.{month_num}.{year}", "%d.%m.%Y")
            except ValueError:
                pass
    return None


def split_event_sections(html: str, base_url: str) -> list:
    """
    Parse an HTML events listing page and return one dict per event section.
    Each dict has: html (str), title (str), date_str (str|None), parsed_date (datetime|None).
    Returns [] if fewer than 2 qualifying sections are found.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    main = soup.find("main") or soup.find("body") or soup

    for tag_name in ("article", "section", "li"):
        containers = main.find_all(tag_name)
        qualifying = []
        for c in containers:
            text = c.get_text(" ", strip=True)
            if len(text.split()) < 10:
                continue
            if not _DATE_RE.search(text):
                continue
            heading = c.find(["h1", "h2", "h3", "h4"])
            if not heading:
                continue
            title = heading.get_text(" ", strip=True)
            date_match = _DATE_RE.search(text)
            date_str = date_match.group(0) if date_match else None
            parsed_date = _parse_date_from_text(text)
            qualifying.append({
                "html": f"<html><body><main>{c}</main></body></html>",
                "title": title,
                "date_str": date_str,
                "parsed_date": parsed_date,
            })
        if len(qualifying) >= 2:
            return qualifying

    return []
