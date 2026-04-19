from unittest.mock import patch, MagicMock
from app.searcher.client import search_tavily, TavilyResult


def test_search_tavily_returns_results():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Quinyx launches AI features",
                "url": "https://techcrunch.com/quinyx-ai",
                "content": "Quinyx announced new AI scheduling features.",
                "score": 0.87,
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.searcher.client.httpx.post", return_value=mock_response):
        results = search_tavily("Quinyx AI scheduling 2025", api_key="fake-key")

    assert len(results) == 1
    assert results[0].title == "Quinyx launches AI features"
    assert results[0].url == "https://techcrunch.com/quinyx-ai"
    assert results[0].score == 0.87
    assert results[0].domain == "techcrunch.com"


def test_search_tavily_returns_empty_on_api_error():
    with patch(
        "app.searcher.client.httpx.post", side_effect=Exception("network error")
    ):
        results = search_tavily("any query", api_key="fake-key")
    assert results == []
