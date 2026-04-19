from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse
import httpx


@dataclass
class TavilyResult:
    title: str
    url: str
    domain: str
    snippet: str
    score: float


def search_tavily(
    query: str, api_key: str, max_results: int = 10
) -> List[TavilyResult]:
    try:
        response = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("results", []):
            parsed = urlparse(item.get("url", ""))
            domain = parsed.netloc.lstrip("www.")
            results.append(
                TavilyResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    domain=domain,
                    snippet=item.get("content") or "",
                    score=float(item.get("score", 0.0)),
                )
            )
        return results
    except Exception:
        return []
