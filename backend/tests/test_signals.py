import pytest
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType


@pytest.fixture
def seed_signals(db_session):
    company = Company(name="ATOSS", slug="atoss-sig", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/sigs", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id, url="https://atoss.com/sigs/1", content_hash="h1"
    )
    db_session.add(doc)
    db_session.commit()
    s1 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="AI Feature",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    s2 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="Partnership",
        signal_type=SignalType.partnership,
        relevance_score=0.5,
    )
    db_session.add_all([s1, s2])
    db_session.commit()
    return company, s1, s2


def test_list_signals(client, seed_signals):
    response = client.get("/api/signals")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_by_company(client, seed_signals):
    company, _, _ = seed_signals
    response = client.get(f"/api/signals?company_id={company.id}")
    assert response.status_code == 200
    assert all(s["company_id"] == company.id for s in response.json())


def test_filter_by_signal_type(client, seed_signals):
    response = client.get("/api/signals?signal_type=ai_announcement")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["signal_type"] == "ai_announcement"


def test_filter_by_min_relevance(client, seed_signals):
    response = client.get("/api/signals?min_relevance=0.8")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["relevance_score"] >= 0.8


def test_get_signal_by_id(client, seed_signals):
    _, s1, _ = seed_signals
    response = client.get(f"/api/signals/{s1.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "AI Feature"


def test_signal_has_source_url(client, seed_signals):
    _, s1, _ = seed_signals
    response = client.get(f"/api/signals/{s1.id}")
    assert response.status_code == 200
    data = response.json()
    assert "source_url" in data
    assert data["source_url"] == "https://atoss.com/sigs/1"


def test_list_signals_have_source_url(client, seed_signals):
    response = client.get("/api/signals")
    assert response.status_code == 200
    for sig in response.json():
        assert "source_url" in sig
