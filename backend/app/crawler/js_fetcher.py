import html as html_module
import json
import logging
from typing import Optional

from app.crawler.fetcher import FetchResult

logger = logging.getLogger(__name__)

_playwright_available: Optional[bool] = None

_EVENT_TITLE_KEYS = frozenset({"title", "name", "subject", "eventtitle", "event_title"})
_EVENT_DATE_KEYS = frozenset({
    "startdate", "start_date", "date", "starttime", "start",
    "eventdate", "event_date", "begindate", "begin_date",
    # UTC variants used by Cvent and similar platforms
    "startdateutc", "enddateutc", "startdatetime", "enddatetime",
    "start_date_utc", "end_date_utc",
})
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB


def _check_playwright() -> bool:
    global _playwright_available
    if _playwright_available is not None:
        return _playwright_available
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        _playwright_available = True
        logger.info("Playwright available — JS rendering enabled")
    except ImportError:
        _playwright_available = False
        logger.warning("playwright not installed; JS rendering disabled")
    return _playwright_available


def _looks_like_event(obj: dict) -> bool:
    keys = {k.lower() for k in obj}
    return bool(keys & _EVENT_TITLE_KEYS) and bool(keys & _EVENT_DATE_KEYS)


def _collect_events(data, depth: int = 0) -> list:
    """Recursively find event-like dicts in arbitrary JSON."""
    if depth > 4:
        return []
    if isinstance(data, list):
        events = []
        for item in data:
            if isinstance(item, dict) and _looks_like_event(item):
                events.append(item)
            elif isinstance(item, (dict, list)):
                events.extend(_collect_events(item, depth + 1))
        return events
    if isinstance(data, dict):
        if _looks_like_event(data):
            return [data]
        events = []
        for value in data.values():
            if isinstance(value, (dict, list)):
                events.extend(_collect_events(value, depth + 1))
        return events
    return []


def _format_field(v) -> Optional[str]:
    if isinstance(v, (str, int, float)) and v != "" and v is not False:
        return str(v)
    if isinstance(v, dict):
        return v.get("name") or v.get("city") or v.get("value") or None
    return None


def _events_to_html(events: list) -> str:
    seen: set = set()
    parts = ["<html><body><main><h1>Events</h1>"]

    for ev in events:
        title = next(
            (str(ev[k]) for k in ev if k.lower() in _EVENT_TITLE_KEYS and ev[k]),
            "Event",
        )
        date = next(
            (str(ev[k]) for k in ev if k.lower() in _EVENT_DATE_KEYS and ev[k]),
            "",
        )
        dedup_key = (title.lower().strip(), date)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        parts.append(f"<article><h2>{html_module.escape(title)}</h2><ul>")
        for k, v in ev.items():
            if k.lower() in _EVENT_TITLE_KEYS:
                continue
            formatted = _format_field(v)
            if formatted:
                parts.append(
                    f"<li><strong>{html_module.escape(k)}:</strong> "
                    f"{html_module.escape(formatted)}</li>"
                )
        parts.append("</ul></article>")

    parts.append("</main></body></html>")
    return "".join(parts)


def fetch_url_js(url: str, timeout: int = 30) -> Optional[FetchResult]:
    if not _check_playwright():
        return None

    from playwright.sync_api import sync_playwright

    logger.info("JS rendering started for %s", url)
    captured_responses: list = []

    def handle_response(response):
        if "json" not in response.headers.get("content-type", ""):
            return
        captured_responses.append(response)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.on("response", handle_response)
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            page.wait_for_timeout(1000)
            html = page.content()
            final_url = page.url

            logger.info(
                "JS rendering complete for %s — %d JSON responses intercepted",
                url,
                len(captured_responses),
            )

            # Process responses while browser is still open
            all_events: list = []
            for response in captured_responses:
                try:
                    body = response.body()
                    if len(body) > _MAX_RESPONSE_BYTES:
                        logger.debug("Skipping oversized response (%d bytes) from %s", len(body), response.url)
                        continue
                    data = json.loads(body)
                    found = _collect_events(data)
                    if found:
                        logger.debug("Found %d events in response from %s", len(found), response.url[:80])
                    all_events.extend(found)
                except Exception as e:
                    logger.debug("Could not parse response from %s: %s", response.url[:80], e)

            context.close()
            browser.close()

        if all_events:
            logger.info(
                "Network interception found %d events for %s — creating per-event documents",
                len(all_events),
                url,
            )
        else:
            logger.info("No events found via interception for %s — using rendered DOM", url)

        result = FetchResult(html=html, final_url=final_url, status_code=200)
        if all_events:
            result.events = all_events
        return result
    except Exception:
        logger.exception("JS fetch failed for %s", url)
        return None
