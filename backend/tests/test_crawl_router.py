import json
import pytest
from unittest.mock import patch
from sqlalchemy.orm import sessionmaker
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType


@pytest.fixture
def seed_source(db_session):
    company = Company(name="ATOSS", slug="atoss-crawl", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/crawl-test",
        source_type=SourceType.news,
        is_active=True,
    )
    db_session.add(source)
    db_session.commit()
    return source


def test_crawl_all_sources(client, seed_source):
    mock_result = {
        "source_id": seed_source.id,
        "new_documents": 1,
        "skipped": 0,
        "errors": 0,
    }
    with patch("app.routers.crawl.run_crawl_source", return_value=mock_result):
        response = client.post("/api/crawl/run")
    assert response.status_code == 200
    data = response.json()
    assert data["sources_processed"] == 1
    assert data["results"][0]["new_documents"] == 1


def test_crawl_single_source(client, seed_source):
    mock_result = {
        "source_id": seed_source.id,
        "new_documents": 2,
        "skipped": 0,
        "errors": 0,
    }
    with patch("app.routers.crawl.run_crawl_source", return_value=mock_result):
        response = client.post(f"/api/crawl/run/{seed_source.id}")
    assert response.status_code == 200
    assert response.json()["new_documents"] == 2


def test_crawl_nonexistent_source(client):
    response = client.post("/api/crawl/run/nonexistent-id")
    assert response.status_code == 404


def test_crawl_skips_inactive_sources(client, db_session, seed_source):
    seed_source.is_active = False
    db_session.commit()
    with patch("app.routers.crawl.run_crawl_source") as mock_crawl:
        response = client.post("/api/crawl/run")
    mock_crawl.assert_not_called()
    assert response.json()["sources_processed"] == 0


def test_stream_all_sources_returns_events(client, seed_source, db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_run(source, db, analyse=True, progress_callback=None):
        if progress_callback:
            progress_callback({"type": "step", "source_id": source.id, "step": "fetching"})
            progress_callback({"type": "step", "source_id": source.id, "step": "extracting"})
        return {"source_id": source.id, "new_documents": 1, "skipped": 0, "errors": 0, "discovery": {}}

    with patch("app.routers.crawl.SessionLocal", TestSessionLocal), \
         patch("app.routers.crawl.run_crawl_source", side_effect=mock_run):
        response = client.get("/api/crawl/stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert event_types[0] == "crawl_start"
    assert "source_start" in event_types
    assert "step" in event_types
    assert "source_done" in event_types
    assert event_types[-1] == "crawl_done"

    done = next(e for e in events if e["type"] == "crawl_done")
    assert done["sources_processed"] == 1
    assert done["total_new"] == 1


def test_stream_single_source_returns_events(client, seed_source, db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_run(source, db, analyse=True, progress_callback=None):
        if progress_callback:
            progress_callback({"type": "step", "source_id": source.id, "step": "fetching"})
        return {"source_id": source.id, "new_documents": 0, "skipped": 1, "errors": 0, "discovery": {}}

    with patch("app.routers.crawl.SessionLocal", TestSessionLocal), \
         patch("app.routers.crawl.run_crawl_source", side_effect=mock_run):
        response = client.get(f"/api/crawl/stream/{seed_source.id}")

    assert response.status_code == 200
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert "crawl_start" in event_types
    assert "crawl_done" in event_types


def test_stream_nonexistent_source_returns_404(client):
    response = client.get("/api/crawl/stream/nonexistent-id")
    assert response.status_code == 404
