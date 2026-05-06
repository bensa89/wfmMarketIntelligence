import pytest
from unittest.mock import patch, MagicMock
from app.crawler.discovery import (
    _is_article_url,
    _is_article_content,
    _is_child_path,
    _extract_internal_links,
    discover_and_crawl,
)
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from datetime import datetime, timezone


def test_is_article_url_date_segment():
    assert _is_article_url("https://example.com/blog/2024/04/my-article") is True


def test_is_article_url_date_year_only():
    assert _is_article_url("https://example.com/news/2023/release") is True


def test_is_article_url_content_prefix_news():
    assert _is_article_url("https://example.com/news/breaking-story") is True


def test_is_article_url_content_prefix_blog():
    assert _is_article_url("https://example.com/blog/my-post") is True


def test_is_article_url_content_prefix_press():
    assert _is_article_url("https://example.com/press/announcement") is True


def test_is_article_url_deep_path():
    assert _is_article_url("https://example.com/section/category/article-slug") is True


def test_is_article_url_rejects_root():
    assert _is_article_url("https://example.com/") is False


def test_is_article_url_rejects_shallow():
    assert _is_article_url("https://example.com/about") is False


def test_is_article_url_rejects_two_segments():
    assert _is_article_url("https://example.com/company/about") is False


def test_is_article_url_locale_prefix_ignored():
    assert _is_article_url("https://example.com/de/warum-atoss/consulting") is False


def test_is_article_url_locale_prefix_with_deep_path():
    assert (
        _is_article_url("https://example.com/de/warum-atoss/consulting/team-lead")
        is True
    )


def test_is_article_url_child_path_of_seed():
    assert (
        _is_article_url(
            "https://example.com/de/unternehmen/news-presse/article-slug",
            seed_url="https://example.com/de/unternehmen/news-presse",
        )
        is True
    )


def test_is_article_url_child_path_requires_depth():
    assert (
        _is_article_url(
            "https://example.com/de/unternehmen",
            seed_url="https://example.com/de/unternehmen/news-presse",
        )
        is False
    )


def test_is_child_path_direct_child():
    assert (
        _is_child_path(
            "https://example.com/news/article-1",
            "https://example.com/news",
        )
        is True
    )


def test_is_child_path_not_child():
    assert (
        _is_child_path(
            "https://example.com/about/team",
            "https://example.com/news",
        )
        is False
    )


def test_is_child_path_deeper_child():
    assert (
        _is_child_path(
            "https://example.com/news/2024/article-1",
            "https://example.com/news",
        )
        is True
    )


def test_is_article_content_with_article_tag():
    html = "<html><body><article><p>Some content here.</p></article></body></html>"
    assert _is_article_content(html) is True


def test_is_article_content_high_word_count():
    words = " ".join(["word"] * 201)
    html = f"<html><body><main><p>{words}</p></main></body></html>"
    assert _is_article_content(html) is True


def test_is_article_content_rejects_low_word_count():
    html = "<html><body><p>Short page.</p></body></html>"
    assert _is_article_content(html) is False


def test_is_article_content_rejects_empty():
    html = "<html><body></body></html>"
    assert _is_article_content(html) is False


def test_is_article_content_rejects_nav_heavy_page():
    nav_links = " ".join(["Link"] * 150)
    body_text = " ".join(["Content word"] * 100)
    html = f"<html><body><nav><a>{nav_links}</a></nav><main><p>{body_text}</p></main></body></html>"
    assert _is_article_content(html) is False


def test_extract_internal_links_absolute():
    html = """
    <html><body>
      <a href="https://example.com/news/article-1">Article</a>
      <a href="https://external.com/page">External</a>
    </body></html>
    """
    links = _extract_internal_links(html, "https://example.com")
    assert "https://example.com/news/article-1" in links
    assert "https://external.com/page" not in links


def test_extract_internal_links_relative():
    html = '<html><body><a href="/blog/post-1">Post</a></body></html>'
    links = _extract_internal_links(html, "https://example.com")
    assert "https://example.com/blog/post-1" in links


def test_extract_internal_links_strips_fragment():
    html = '<html><body><a href="/news/article#section">Article</a></body></html>'
    links = _extract_internal_links(html, "https://example.com")
    assert "https://example.com/news/article" in links
    assert "https://example.com/news/article#section" not in links


def test_extract_internal_links_ignores_mailto():
    html = '<html><body><a href="mailto:info@example.com">Email</a></body></html>'
    links = _extract_internal_links(html, "https://example.com")
    assert not any("mailto" in l for l in links)


def _make_source(db_session, slug="disc-test", url="https://example.com"):
    company = Company(name="Test Co", slug=slug, type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url=url, source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    return source


SEED_HTML = """
<html><body>
  <a href="/blog/2024/04/article-one">Article One</a>
  <a href="/about">About</a>
</body></html>
"""

ARTICLE_HTML = (
    "<html><body><article><p>"
    + " ".join(["word"] * 250)
    + "</p></article></body></html>"
)


def test_discover_skips_when_depth_zero(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 0)
    source = _make_source(db_session, slug="disc-depth0")
    result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)
    assert result["discovered"] == 0
    assert db_session.query(DiscoveredPage).count() == 0


def test_discover_saves_new_page(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-new")

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
    ):
        result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    assert result["new"] == 1
    assert result["discovered"] == 1
    page = db_session.query(DiscoveredPage).first()
    assert page is not None
    assert page.status == DiscoveredPageStatus.new
    assert page.source_id == source.id
    assert page.depth == 1


def test_discover_marks_unchanged_page_as_known(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-known")

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
    ):
        discover_and_crawl(source, SEED_HTML, db_session, analyse=False)
        result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    assert result["known"] == 1
    page = db_session.query(DiscoveredPage).first()
    assert page.status == DiscoveredPageStatus.known


def test_discover_marks_changed_page(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-changed")

    article_html_v2 = (
        "<html><body><article><p>"
        + " ".join(["different"] * 250)
        + "</p></article></body></html>"
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    fetch_v1 = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    fetch_v2 = MagicMock(
        return_value=MagicMock(
            html=article_html_v2,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )

    with (
        patch("app.crawler.discovery.fetch_url", fetch_v1),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
    ):
        discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    with (
        patch("app.crawler.discovery.fetch_url", fetch_v2),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
    ):
        result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    assert result["changed"] == 1
    page = db_session.query(DiscoveredPage).first()
    assert page.status == DiscoveredPageStatus.changed
    assert page.last_changed_at is not None


def test_discover_skips_robots_disallowed(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-robots")

    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = False

    with (
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
    ):
        result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    assert result["discovered"] == 0


def test_discover_ignores_robots_when_disabled(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-robots-off")
    source.respect_robots_txt = False
    db_session.commit()

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = False  # robots.txt blocks everything

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
    ):
        result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    assert result["discovered"] == 1


def test_discover_ignores_inactive_page(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-inactive")

    page = DiscoveredPage(
        source_id=source.id,
        url="https://example.com/blog/2024/04/article-one",
        depth=1,
        status=DiscoveredPageStatus.ignored,
        is_active=False,
        discovered_at=datetime.now(timezone.utc),
    )
    db_session.add(page)
    db_session.commit()

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
    ):
        result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    assert result["discovered"] == 0
    assert mock_fetch.call_count == 0


from app.models.signal import Signal, SignalType
from app.models.document import Document


def _make_signal(db_session, doc_id: str, company_id: str, relevance: float):
    signal = Signal(
        document_id=doc_id,
        company_id=company_id,
        title="Test Signal",
        signal_type=SignalType.other,
        relevance_score=relevance,
        confidence_score=0.8,
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def test_discover_auto_ignores_page_when_all_signals_low(db_session, monkeypatch):
    import app.config as cfg
    from app.models.source import AnalysisStatus

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-auteignore")

    def mock_save_document_only(src, fetch_result, extraction, now, db):
        doc = Document(
            source_id=src.id,
            url=fetch_result.final_url,
            title="Test Article",
            content_markdown="content",
            content_hash=extraction.content_hash,
            crawled_at=now,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
        patch(
            "app.crawler.discovery._save_document_only",
            side_effect=mock_save_document_only,
        ),
    ):
        discover_and_crawl(source, SEED_HTML, db_session, analyse=True)

    page = db_session.query(DiscoveredPage).first()
    assert page is not None
    assert page.status == DiscoveredPageStatus.new
    db_session.refresh(source)
    assert source.analysis_status == AnalysisStatus.pending


def test_discover_keeps_page_active_when_one_signal_relevant(db_session, monkeypatch):
    import app.config as cfg
    from app.models.source import AnalysisStatus

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-keep-active")

    def mock_save_document_only(src, fetch_result, extraction, now, db):
        doc = Document(
            source_id=src.id,
            url=fetch_result.final_url,
            title="Test Article",
            content_markdown="content",
            content_hash=extraction.content_hash,
            crawled_at=now,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery.fetch_url_js", return_value=None),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
        patch(
            "app.crawler.discovery._save_document_only",
            side_effect=mock_save_document_only,
        ),
    ):
        discover_and_crawl(source, SEED_HTML, db_session, analyse=True)

    page = db_session.query(DiscoveredPage).first()
    assert page.is_active is True
    db_session.refresh(source)
    assert source.analysis_status == AnalysisStatus.pending
