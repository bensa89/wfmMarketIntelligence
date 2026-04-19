import logging
from typing import Optional

from app.crawler.fetcher import FetchResult

logger = logging.getLogger(__name__)

_playwright_available: Optional[bool] = None


def _check_playwright() -> bool:
    global _playwright_available
    if _playwright_available is not None:
        return _playwright_available
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        _playwright_available = True
    except ImportError:
        _playwright_available = False
        logger.warning("playwright not installed; JS rendering disabled")
    return _playwright_available


def fetch_url_js(url: str, timeout: int = 30) -> Optional[FetchResult]:
    if not _check_playwright():
        return None

    from playwright.sync_api import sync_playwright

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
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            page.wait_for_timeout(1000)
            html = page.content()
            final_url = page.url
            status_code = 200
            context.close()
            browser.close()
            return FetchResult(html=html, final_url=final_url, status_code=status_code)
    except Exception:
        logger.exception("JS fetch failed for %s", url)
        return None
