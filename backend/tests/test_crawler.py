import pytest
from unittest.mock import patch, MagicMock
from app.crawler.fetcher import fetch_url, FetchResult
from app.crawler.extractor import extract_content, ExtractionResult


def test_fetch_url_returns_html_on_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = (
        "<html><head><title>Test Page</title></head><body><p>Hello</p></body></html>"
    )
    mock_response.url = "https://example.com/page"

    with patch("app.crawler.fetcher.httpx.get", return_value=mock_response):
        result = fetch_url("https://example.com/page")

    assert isinstance(result, FetchResult)
    assert result.html == mock_response.text
    assert result.final_url == "https://example.com/page"
    assert result.status_code == 200


def test_fetch_url_returns_none_on_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = Exception("404")

    with patch(
        "app.crawler.fetcher.httpx.get", side_effect=Exception("Connection error")
    ):
        result = fetch_url("https://example.com/broken")

    assert result is None


def test_extract_content_from_html():
    html = """
    <html>
      <head><title>ATOSS News</title></head>
      <body>
        <nav>Navigation</nav>
        <main>
          <h1>New AI Feature Released</h1>
          <p>ATOSS released a new AI-powered scheduling module today.</p>
        </main>
        <footer>Footer</footer>
      </body>
    </html>
    """
    result = extract_content(html, url="https://atoss.com/news/ai")
    assert isinstance(result, ExtractionResult)
    assert result.title == "ATOSS News"
    assert "AI-powered scheduling" in result.markdown
    assert len(result.content_hash) == 64


def test_extract_sets_hash_based_on_content():
    html1 = "<html><body><p>Content A</p></body></html>"
    html2 = "<html><body><p>Content B</p></body></html>"
    r1 = extract_content(html1, url="https://example.com/1")
    r2 = extract_content(html2, url="https://example.com/2")
    assert r1.content_hash != r2.content_hash


def test_extract_same_content_same_hash():
    html = "<html><body><p>Same content</p></body></html>"
    r1 = extract_content(html, url="https://example.com/a")
    r2 = extract_content(html, url="https://example.com/b")
    assert r1.content_hash == r2.content_hash
