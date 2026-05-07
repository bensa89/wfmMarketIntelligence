import pytest
from datetime import date
from app.models.digest import WeeklyDigest
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType


@pytest.fixture
def seed_company_and_signals(db_session):
    company = Company(name="TestCo", slug="testco", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://testco.com/news",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://testco.com/news/article-1",
        content_hash="hash1",
    )
    db_session.add(doc)
    db_session.commit()
    s1 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="AI Feature Launch",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    s2 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="New Partnership",
        signal_type=SignalType.partnership,
        relevance_score=0.5,
    )
    db_session.add_all([s1, s2])
    db_session.commit()
    return company, doc, s1, s2


@pytest.fixture
def seed_digest(db_session, seed_company_and_signals):
    _, _, s1, s2 = seed_company_and_signals
    d = WeeklyDigest(
        week_start=date(2026, 4, 14),
        week_end=date(2026, 4, 20),
        summary="Big week in AI WFM.",
        key_signals=[s1.id, s2.id],
        is_published=True,
    )
    db_session.add(d)
    db_session.commit()
    return d


def test_list_digests(client, seed_digest):
    response = client.get("/api/digests")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_digest_by_id(client, seed_digest, seed_company_and_signals):
    _, _, s1, s2 = seed_company_and_signals
    response = client.get(f"/api/digests/{seed_digest.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Big week in AI WFM."
    assert len(data["key_signals"]) == 2
    assert data["key_signals"][0]["id"] == s1.id
    assert data["key_signals"][0]["title"] == "AI Feature Launch"
    assert data["key_signals"][0]["signal_type"] == "ai_announcement"
    assert data["key_signals"][0]["source_url"] == "https://testco.com/news/article-1"
    assert data["key_signals"][0]["company_name"] == "TestCo"


def test_digest_key_signals_have_source_url(client, seed_digest):
    response = client.get(f"/api/digests/{seed_digest.id}")
    data = response.json()
    for sig in data["key_signals"]:
        assert "source_url" in sig
        assert sig["source_url"] is not None


def test_generate_digest(client):
    response = client.post("/api/digests/generate")
    assert response.status_code == 201
    data = response.json()
    assert "week_start" in data
    assert "week_end" in data
    assert isinstance(data["key_signals"], list)


def test_digest_read_has_sections_field(client, seed_digest):
    response = client.get(f"/api/digests/{seed_digest.id}")
    assert response.status_code == 200
    data = response.json()
    assert "sections" in data
    assert isinstance(data["sections"], list)
