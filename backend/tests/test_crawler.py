import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.crawler.fetcher import fetch_url, FetchResult
from app.crawler.extractor import (
    extract_content,
    ExtractionResult,
    _extract_published_at,
)
from bs4 import BeautifulSoup


def _assessment_json(**overrides) -> str:
    import json

    base = {
        "capability_primary": "ai_copilot",
        "capability_secondary": [],
        "signal_class": "weak_signal",
        "evidence_strength": 2,
        "visibility_impact": "low",
        "strategic_intent_guess": "Unclear.",
        "gameplay_tags": [],
        "assessment_summary": "Minor update.",
        "implication_for_us": "Low impact.",
        "watch_items": [],
        "confidence": 0.5,
    }
    base.update(overrides)
    return json.dumps(base)


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


from app.crawler.pipeline import run_crawl_source


def test_run_crawl_source_saves_new_document(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document

    company = Company(name="ATOSS", slug="atoss-pipe", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/pipe", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    mock_fetch = MagicMock(
        return_value=FetchResult(
            html="<html><head><title>Test</title></head><body><p>"
            + "New content for the pipe source. " * 10
            + "</p></body></html>",
            final_url="https://atoss.com/pipe",
            status_code=200,
        )
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch(
            "app.crawler.pipeline.discover_and_crawl",
            return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0},
        ),
    ):
        result = run_crawl_source(source, db_session, analyse=False)

    assert result["new_documents"] == 1
    doc = db_session.query(Document).first()
    assert doc is not None
    assert doc.content_markdown is not None
    assert doc.source_id == source.id


def test_run_crawl_source_skips_duplicate(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document

    company = Company(name="ATOSS", slug="atoss-dup2", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/dup2", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    html = (
        "<html><head><title>Same</title></head><body><p>"
        + "Same content for the dup2 source. " * 10
        + "</p></body></html>"
    )
    mock_fetch = MagicMock(
        return_value=FetchResult(
            html=html, final_url="https://atoss.com/dup2", status_code=200
        )
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch(
            "app.crawler.pipeline.discover_and_crawl",
            return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0},
        ),
    ):
        run_crawl_source(source, db_session, analyse=False)
        result = run_crawl_source(source, db_session, analyse=False)

    assert result["new_documents"] == 0
    assert db_session.query(Document).count() == 1


def test_run_crawl_source_calls_discovery(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType

    company = Company(name="ATOSS", slug="atoss-disc-pipe", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/disc", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    mock_html = (
        "<html><head><title>Test</title></head><body><p>New content</p></body></html>"
    )
    mock_fetch = MagicMock(
        return_value=FetchResult(
            html=mock_html, final_url="https://atoss.com/disc", status_code=200
        )
    )
    mock_discover = MagicMock(
        return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0}
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch("app.crawler.pipeline.discover_and_crawl", mock_discover),
    ):
        run_crawl_source(source, db_session, analyse=False)

    mock_discover.assert_called_once()
    call_kwargs = mock_discover.call_args
    assert call_kwargs[0][0] == source
    assert call_kwargs[0][2] == db_session


def test_run_crawl_source_calls_progress_callback(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType

    company = Company(name="ATOSS", slug="atoss-cb", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/cb", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    mock_fetch = MagicMock(
        return_value=FetchResult(
            html="<html><head><title>T</title></head><body><p>New content</p></body></html>",
            final_url="https://atoss.com/cb",
            status_code=200,
        )
    )

    events = []

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch(
            "app.crawler.pipeline.discover_and_crawl",
            return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0},
        ),
    ):
        run_crawl_source(
            source,
            db_session,
            analyse=False,
            progress_callback=lambda e: events.append(e),
        )

    steps = [e["step"] for e in events if e.get("type") == "step"]
    assert "fetching" in steps
    assert "extracting" in steps
    assert "discovering" in steps
    assert all(e.get("source_id") == source.id for e in events)


def test_run_crawl_source_callback_on_fetch_failure(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType

    company = Company(name="ATOSS", slug="atoss-cb-fail", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/cb-fail",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    events = []

    with patch("app.crawler.pipeline.fetch_url", return_value=None):
        result = run_crawl_source(
            source,
            db_session,
            analyse=False,
            progress_callback=lambda e: events.append(e),
        )

    assert result["errors"] == 1
    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) == 1
    assert error_events[0]["source_id"] == source.id
    assert "message" in error_events[0]


def test_run_crawl_source_sets_crawl_status_new(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, CrawlStatus

    company = Company(
        name="ATOSS", slug="atoss-status-new", type=CompanyType.competitor
    )
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/status-new",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    mock_fetch = MagicMock(
        return_value=FetchResult(
            html="<html><head><title>New</title></head><body><p>"
            + "Fresh content for the status-new source. " * 10
            + "</p></body></html>",
            final_url="https://atoss.com/status-new",
            status_code=200,
        )
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch(
            "app.crawler.pipeline.discover_and_crawl",
            return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0},
        ),
    ):
        run_crawl_source(source, db_session, analyse=False)

    db_session.refresh(source)
    assert source.crawl_status == CrawlStatus.new
    assert source.content_hash is not None


def test_run_crawl_source_sets_crawl_status_known_on_same_content(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, CrawlStatus

    company = Company(
        name="ATOSS", slug="atoss-status-known", type=CompanyType.competitor
    )
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/status-known",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    html = (
        "<html><head><title>Same</title></head><body><p>"
        + "Same content for the status-known source. " * 10
        + "</p></body></html>"
    )
    mock_fetch = MagicMock(
        return_value=FetchResult(
            html=html, final_url="https://atoss.com/status-known", status_code=200
        )
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch(
            "app.crawler.pipeline.discover_and_crawl",
            return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0},
        ),
    ):
        run_crawl_source(source, db_session, analyse=False)
        run_crawl_source(source, db_session, analyse=False)

    db_session.refresh(source)
    assert source.crawl_status == CrawlStatus.known


def test_run_crawl_source_sets_crawl_status_changed_on_content_change(db_session):
    """Test that crawl_status is set to 'changed' (and the document content updated)
    when a second crawl of the same source returns different content."""
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, CrawlStatus
    from app.models.document import Document

    company = Company(
        name="ATOSS", slug="atoss-status-chg", type=CompanyType.competitor
    )
    db_session.add(company)
    db_session.commit()

    source = Source(
        company_id=company.id,
        url="https://atoss.com/status-chg",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    html_v1 = (
        "<html><head><title>Test</title></head><body><p>"
        + "Content for testing the status-chg source. " * 10
        + "</p></body></html>"
    )
    html_v2 = (
        "<html><head><title>Test</title></head><body><p>"
        + "Different content now for the status-chg source. " * 10
        + "</p></body></html>"
    )

    no_discovery = {"discovered": 0, "new": 0, "changed": 0, "known": 0}

    with (
        patch(
            "app.crawler.pipeline.fetch_url",
            return_value=FetchResult(
                html=html_v1, final_url="https://atoss.com/status-chg", status_code=200
            ),
        ),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch("app.crawler.pipeline.discover_and_crawl", return_value=no_discovery),
    ):
        run_crawl_source(source, db_session, analyse=False)

    db_session.refresh(source)
    assert source.crawl_status == CrawlStatus.new
    first_hash = source.content_hash
    assert first_hash is not None

    with (
        patch(
            "app.crawler.pipeline.fetch_url",
            return_value=FetchResult(
                html=html_v2, final_url="https://atoss.com/status-chg", status_code=200
            ),
        ),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch("app.crawler.pipeline.discover_and_crawl", return_value=no_discovery),
    ):
        result = run_crawl_source(source, db_session, analyse=False)

    db_session.refresh(source)
    assert source.crawl_status == CrawlStatus.changed
    assert source.content_hash != first_hash
    assert result["new_documents"] == 1
    doc = db_session.query(Document).filter(Document.source_id == source.id).first()
    assert "Different content now" in doc.content_markdown


def test_run_crawl_source_skips_short_content(db_session):
    """Pages with too little extracted text (below _MIN_CONTENT_WORDS) are skipped
    entirely — no Document is created and the source is not marked changed."""
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.crawler.pipeline import run_crawl_source

    company = Company(name="ATOSS", slug="atoss-noart", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/noart",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    nav_html = """<html><head><title>Overview</title></head><body>
        <nav><a href="/link1">Link1</a><a href="/link2">Link2</a></nav>
        <main><p>Short teaser</p></main>
    </body></html>"""

    mock_fetch = MagicMock(
        return_value=FetchResult(
            html=nav_html, final_url="https://atoss.com/noart", status_code=200
        )
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch(
            "app.crawler.pipeline.discover_and_crawl",
            return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0},
        ),
    ):
        result = run_crawl_source(source, db_session, analyse=True)

    assert result["new_documents"] == 0
    assert result["skipped"] == 1
    assert db_session.query(Document).count() == 0


def test_run_crawl_source_sets_analysis_pending(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, AnalysisStatus
    from app.crawler.pipeline import run_crawl_source

    company = Company(name="ATOSS", slug="atoss-art", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/art",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    article_html = """<html><head><title>Article</title></head><body>
        <main><p>This is a real article with enough content to be considered substantive
        for analysis purposes and contains detailed information about the topic at hand,
        with several additional sentences to comfortably clear the minimum word count.</p></main>
    </body></html>"""

    mock_fetch = MagicMock(
        return_value=FetchResult(
            html=article_html, final_url="https://atoss.com/art", status_code=200
        )
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.fetch_url_js", return_value=None),
        patch(
            "app.crawler.pipeline.discover_and_crawl",
            return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0},
        ),
    ):
        result = run_crawl_source(source, db_session, analyse=True)

    assert result["new_documents"] == 1
    db_session.refresh(source)
    assert source.analysis_status == AnalysisStatus.pending


def test_extract_published_at_from_json_ld():
    html = """<html><head>
    <script type="application/ld+json">
    {"@type": "Article", "datePublished": "2024-03-15T10:00:00+01:00"}
    </script>
    </head><body><p>content</p></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result == datetime(2024, 3, 15, 9, 0, 0)  # UTC, naive


def test_extract_published_at_from_og_meta():
    html = """<html><head>
    <meta property="article:published_time" content="2024-06-01T08:30:00Z"/>
    </head><body><p>content</p></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result == datetime(2024, 6, 1, 8, 30, 0)


def test_extract_published_at_from_time_element():
    html = """<html><body>
    <article><time datetime="2024-09-20">September 20</time><p>body text</p></article>
    </body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result == datetime(2024, 9, 20)


def test_extract_published_at_returns_none_when_no_date():
    html = "<html><body><p>No date here</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result is None


def test_extract_content_sets_published_at():
    html = """<html><head>
    <meta property="article:published_time" content="2025-01-10"/>
    <title>Test Article</title>
    </head><body><main><p>Article body text here</p></main></body></html>"""
    result = extract_content(html, url="https://example.com/article")
    assert result.published_at == datetime(2025, 1, 10)


def test_extract_content_published_at_none_when_missing():
    html = "<html><head><title>T</title></head><body><p>text</p></body></html>"
    result = extract_content(html)
    assert result.published_at is None


def test_analyse_unanalysed_for_source_creates_signals(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, AnalysisStatus
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.crawler.pipeline import analyse_unanalysed_for_source

    company = Company(name="ATOSS", slug="atoss-anl1", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/anl1",
        source_type=SourceType.news,
        analysis_status=AnalysisStatus.pending,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/anl1/page1",
        content_markdown="## Big AI Feature\n"
        + "ATOSS launches new AI scheduling feature for enterprise. " * 20,
        content_hash="h_anl1",
    )
    db_session.add(doc)
    db_session.commit()

    with (
        patch(
            "app.analyser.pipeline.call_llm",
            return_value='{"title":"AI Feature","signal_type":"ai_announcement","topic":"AI","summary":"New AI feature.","why_it_matters":"Competes with us.","relevance_score":0.9,"confidence_score":0.85}',
        ),
        patch("app.assessor.pipeline.call_llm", return_value=_assessment_json()),
        patch("app.crawler.pipeline.SessionLocal", side_effect=lambda: MagicMock(wraps=db_session, close=MagicMock())),
    ):
        result = analyse_unanalysed_for_source(source, db_session)

    assert result["analysed"] == 1
    assert result["errors"] == 0
    db_session.refresh(doc)
    assert doc.is_analysed is True
    db_session.refresh(source)
    assert source.analysis_status == AnalysisStatus.analysed
    signal = db_session.query(Signal).first()
    assert signal is not None
    assert signal.document_id == doc.id
    assert signal.company_id == company.id


def test_analyse_unanalysed_for_source_handles_errors(db_session, db_engine):
    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, AnalysisStatus
    from app.models.document import Document
    from app.models.signal import Signal
    from app.crawler.pipeline import analyse_unanalysed_for_source

    company = Company(name="ATOSS", slug="atoss-anl-err", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/anl-err",
        source_type=SourceType.news,
        analysis_status=AnalysisStatus.pending,
    )
    db_session.add(source)
    db_session.commit()
    doc1 = Document(
        source_id=source.id,
        url="https://atoss.com/anl-err/p1",
        content_markdown="## Article one\n" + "Content for the first article. " * 20,
        content_hash="h_anl_err1",
    )
    doc2 = Document(
        source_id=source.id,
        url="https://atoss.com/anl-err/p2",
        content_markdown="## Article two\n" + "Content for the second article. " * 20,
        content_hash="h_anl_err2",
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Use a real session factory from the test engine so each worker gets its own
    # independent session (needed when one worker rollbacks on error).
    TestSessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_llm(prompt, max_tokens=1024, caller=""):
        # Tie the failure to doc1's content rather than call order: the two
        # documents are analysed concurrently, so call order is not deterministic.
        if "Article one" in prompt:
            raise RuntimeError("LLM service unavailable")
        return '{"title":"OK","signal_type":"other","topic":"OK","summary":"Fine.","why_it_matters":"OK","relevance_score":0.5,"confidence_score":0.5}'

    with (
        patch("app.analyser.pipeline.call_llm", side_effect=mock_llm),
        patch("app.assessor.pipeline.call_llm", return_value=_assessment_json()),
        patch("app.crawler.pipeline.SessionLocal", side_effect=TestSessionFactory),
    ):
        result = analyse_unanalysed_for_source(source, db_session)

    assert result["errors"] == 1
    assert result["analysed"] == 1
    db_session.refresh(source)
    assert source.analysis_status == AnalysisStatus.analysis_failed

    # Query fresh from database instead of relying on cached object
    # This ensures we see committed changes from worker sessions
    doc2_fresh = db_session.query(Document).filter(Document.id == doc2.id).first()
    assert doc2_fresh is not None
    assert doc2_fresh.is_analysed is True


def test_analyse_unanalysed_for_source_skips_analysed_docs(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, AnalysisStatus
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.crawler.pipeline import analyse_unanalysed_for_source

    company = Company(name="ATOSS", slug="atoss-anl-skip", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/anl-skip",
        source_type=SourceType.news,
        analysis_status=AnalysisStatus.pending,
    )
    db_session.add(source)
    db_session.commit()

    analysed_doc = Document(
        source_id=source.id,
        url="https://atoss.com/anl-skip/old",
        content_markdown="## Already done\n" + "Previously analysed content. " * 20,
        content_hash="h_anl_skip_old",
        is_analysed=True,
    )
    unanalysed_doc = Document(
        source_id=source.id,
        url="https://atoss.com/anl-skip/new",
        content_markdown="## New stuff\n" + "New content to analyse. " * 20,
        content_hash="h_anl_skip_new",
        is_analysed=False,
    )
    db_session.add_all([analysed_doc, unanalysed_doc])
    db_session.commit()

    with (
        patch(
            "app.analyser.pipeline.call_llm",
            return_value='{"title":"New Signal","signal_type":"other","topic":"New","summary":"New stuff.","why_it_matters":"OK","relevance_score":0.6,"confidence_score":0.7}',
        ) as mock_llm,
        patch("app.assessor.pipeline.call_llm", return_value=_assessment_json()),
        patch("app.crawler.pipeline.SessionLocal", side_effect=lambda: MagicMock(wraps=db_session, close=MagicMock())),
    ):
        result = analyse_unanalysed_for_source(source, db_session)

    assert result["analysed"] == 1
    assert mock_llm.call_count == 1
    db_session.refresh(source)
    assert source.analysis_status == AnalysisStatus.analysed


def test_analyse_unanalysed_for_source_no_unanalysed_docs(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, AnalysisStatus
    from app.models.document import Document
    from app.crawler.pipeline import analyse_unanalysed_for_source

    company = Company(name="ATOSS", slug="atoss-anl-none", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/anl-none",
        source_type=SourceType.news,
        analysis_status=AnalysisStatus.pending,
    )
    db_session.add(source)
    db_session.commit()

    doc = Document(
        source_id=source.id,
        url="https://atoss.com/anl-none/done",
        content_markdown="## Done\n" + "Already analysed. " * 20,
        content_hash="h_anl_none",
        is_analysed=True,
    )
    db_session.add(doc)
    db_session.commit()

    with patch("app.analyser.pipeline.call_llm") as mock_llm, patch(
        "app.crawler.pipeline.SessionLocal", side_effect=lambda: MagicMock(wraps=db_session, close=MagicMock())
    ):
        result = analyse_unanalysed_for_source(source, db_session)

    assert result["analysed"] == 0
    mock_llm.assert_not_called()
    db_session.refresh(source)
    assert source.analysis_status == AnalysisStatus.analysed


def test_analyse_unanalysed_for_source_emits_progress(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, AnalysisStatus
    from app.models.document import Document
    from app.crawler.pipeline import analyse_unanalysed_for_source

    company = Company(name="ATOSS", slug="atoss-anl-prog", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/anl-prog",
        source_type=SourceType.news,
        analysis_status=AnalysisStatus.pending,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/anl-prog/p1",
        content_markdown="## Progress test\n" + "Content for progress callback. " * 20,
        content_hash="h_anl_prog",
        is_analysed=False,
    )
    db_session.add(doc)
    db_session.commit()

    events = []

    with (
        patch(
            "app.analyser.pipeline.call_llm",
            return_value='{"title":"Prog","signal_type":"other","topic":"Prog","summary":"OK.","why_it_matters":"OK","relevance_score":0.5,"confidence_score":0.5}',
        ),
        patch("app.assessor.pipeline.call_llm", return_value=_assessment_json()),
        patch("app.crawler.pipeline.SessionLocal", side_effect=lambda: MagicMock(wraps=db_session, close=MagicMock())),
    ):
        result = analyse_unanalysed_for_source(
            source, db_session, progress_callback=lambda e: events.append(e)
        )

    progress_events = [e for e in events if e.get("type") == "analysis_progress"]
    assert len(progress_events) == 1
    assert progress_events[0]["source_id"] == source.id
    assert progress_events[0]["current"] == 1
    assert progress_events[0]["total"] == 1


def test_source_type_events_exists():
    from app.models.source import SourceType
    assert SourceType.events == "events"


def test_split_event_sections_finds_articles_with_dates():
    from app.crawler.extractor import split_event_sections
    html = """
    <html><body><main>
      <article>
        <h2>Brain Snacks</h2>
        <p>22. Januar 2026 – Workshop im TOPGOLF Oberhausen zum Thema Workforce Management.</p>
      </article>
      <article>
        <h2>HR Summit Berlin</h2>
        <p>15. März 2026 – Jahreskonferenz für HR-Entscheider in Berlin. Drei Tracks, 20 Speaker.</p>
      </article>
    </main></body></html>
    """
    sections = split_event_sections(html, "https://example.com/events/")
    assert len(sections) == 2
    assert sections[0]["title"] == "Brain Snacks"
    assert sections[0]["date_str"] is not None
    assert sections[1]["title"] == "HR Summit Berlin"


def test_split_event_sections_returns_empty_when_no_dates():
    from app.crawler.extractor import split_event_sections
    html = """
    <html><body><main>
      <article><h2>About us</h2><p>We are a software company.</p></article>
      <article><h2>Contact</h2><p>Reach us at info@example.com.</p></article>
    </main></body></html>
    """
    sections = split_event_sections(html, "https://example.com/")
    assert sections == []


def test_split_event_sections_falls_back_when_no_containers():
    from app.crawler.extractor import split_event_sections
    html = "<html><body><p>22. Januar 2026 – Just one paragraph with a date.</p></body></html>"
    sections = split_event_sections(html, "https://example.com/events/")
    assert sections == []
