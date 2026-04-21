import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
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
