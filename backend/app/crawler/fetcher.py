from dataclasses import dataclass
from typing import Optional
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


@dataclass
class FetchResult:
    html: str
    final_url: str
    status_code: int


def fetch_url(url: str, timeout: int = 15) -> Optional[FetchResult]:
    try:
        response = httpx.get(
            url, headers=HEADERS, timeout=timeout, follow_redirects=True
        )
        response.raise_for_status()
        return FetchResult(
            html=response.text,
            final_url=str(response.url),
            status_code=response.status_code,
        )
    except Exception:
        return None
