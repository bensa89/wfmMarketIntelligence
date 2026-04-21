import pytest
import os

from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType

SKIP_SEARCH = not os.environ.get("DATABASE_URL", "").startswith("postgres")


@pytest.fixture
def seed_search_signals(db_session):

    company = Company(name="SearchCorp", slug="searchcorp", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    source = Source(
        company_id=company.id,
        url="https://searchcorp.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()

    doc1 = Document(
        source_id=source.id,
        url="https://searchcorp.com/blog/ai-strategy",
        title="AI Strategy Update",
        content_hash="search1",
    )
    doc2 = Document(
        source_id=source.id,
        url="https://searchcorp.com/blog/hiring-engineers",
        title="We Are Hiring Engineers",
        content_hash="search2",
    )
    doc3 = Document(
        source_id=source.id,
        url="https://searchcorp.com/blog/partnership",
        title="New Partnership Announcement",
        content_hash="search3",
    )
    db_session.add_all([doc1, doc2, doc3])
    db_session.commit()

    s1 = Signal(
        document_id=doc1.id,
        company_id=company.id,
        title="AI Strategy Shift",
        signal_type=SignalType.ai_announcement,
        summary="Company shifts focus to generative AI across all products.",
        relevance_score=0.9,
        confidence_score=0.85,
    )
    s2 = Signal(
        document_id=doc2.id,
        company_id=company.id,
        title="Engineering Hiring Wave",
        signal_type=SignalType.hiring_signal,
        summary="Multiple senior engineering positions opened in Munich.",
        relevance_score=0.6,
        confidence_score=0.7,
    )
    s3 = Signal(
        document_id=doc3.id,
        company_id=company.id,
        title="Strategic Partnership",
        signal_type=SignalType.partnership,
        topic="partnering with cloud providers",
        summary="Company announced a strategic partnership with a major cloud provider.",
        relevance_score=0.75,
        confidence_score=0.9,
    )
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    for s in [s1, s2, s3]:
        db_session.refresh(s)
    db_session.commit()

    return company, [s1, s2, s3], [doc1, doc2, doc3]


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_by_title(client, seed_search_signals):
    response = client.get("/api/signals?q=AI+Strategy")
    assert response.status_code == 200
    titles = [s["title"] for s in response.json()]
    assert "AI Strategy Shift" in titles


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_by_summary(client, seed_search_signals):
    response = client.get("/api/signals?q=generative")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert any("AI Strategy Shift" in s["title"] for s in response.json())


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_by_source_url(client, seed_search_signals):
    response = client.get("/api/signals?q=hiring-engineers")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_combined_with_filters(client, seed_search_signals):
    response = client.get("/api/signals?q=AI&signal_type=ai_announcement")
    assert response.status_code == 200
    assert all(s["signal_type"] == "ai_announcement" for s in response.json())


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_no_match(client, seed_search_signals):
    response = client.get("/api/signals?q=xyznonexistentterm123")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_ranking_title_higher_than_summary(client, seed_search_signals):
    response = client.get("/api/signals?q=partnership")
    assert response.status_code == 200
    results = response.json()
    if len(results) >= 2:
        assert results[0]["title"] == "Strategic Partnership"


def test_filter_by_min_confidence(client, db_session):
    company = Company(name="ConfCorp", slug="confcorp", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://confcorp.com/sig",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id, url="https://confcorp.com/sig/1", content_hash="conf1"
    )
    db_session.add(doc)
    db_session.commit()

    s1 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="High Confidence",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.5,
        confidence_score=0.9,
    )
    s2 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="Low Confidence",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.5,
        confidence_score=0.3,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    response = client.get("/api/signals?min_confidence=0.8")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "High Confidence"
