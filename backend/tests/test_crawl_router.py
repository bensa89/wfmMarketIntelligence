import json
import pytest
from unittest.mock import patch
from sqlalchemy.orm import sessionmaker
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.crawl_run import (
    CrawlRun,
    CrawlRunStatus,
    CrawlRunSource,
    CrawlRunSourceStatus,
    CrawlRunStep,
)


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
            progress_callback(
                {"type": "step", "source_id": source.id, "step": "fetching"}
            )
            progress_callback(
                {"type": "step", "source_id": source.id, "step": "extracting"}
            )
        return {
            "source_id": source.id,
            "new_documents": 1,
            "skipped": 0,
            "errors": 0,
            "discovery": {},
        }

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run),
    ):
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

    start = next(e for e in events if e["type"] == "crawl_start")
    assert "crawl_run_id" in start
    assert start["total"] == 1

    done = next(e for e in events if e["type"] == "crawl_done")
    assert done["sources_processed"] == 1
    assert done["total_new"] == 1
    assert "crawl_run_id" in done

    for e in events:
        if e["type"] not in ("crawl_start",):
            assert "crawl_run_id" in e


def test_stream_single_source_returns_events(client, seed_source, db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_run(source, db, analyse=True, progress_callback=None):
        if progress_callback:
            progress_callback(
                {"type": "step", "source_id": source.id, "step": "fetching"}
            )
        return {
            "source_id": source.id,
            "new_documents": 0,
            "skipped": 1,
            "errors": 0,
            "discovery": {},
        }

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run),
    ):
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


def test_stream_creates_crawl_run_in_db(client, seed_source, db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_run(source, db, analyse=True, progress_callback=None):
        return {
            "source_id": source.id,
            "new_documents": 1,
            "skipped": 0,
            "errors": 0,
            "discovery": {},
        }

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run),
    ):
        response = client.get("/api/crawl/stream")
    assert response.status_code == 200

    verify_db = TestSessionLocal()
    try:
        runs = verify_db.query(CrawlRun).all()
        assert len(runs) == 1
        assert runs[0].status == CrawlRunStatus.completed
        assert runs[0].total_sources == 1
        assert runs[0].total_new == 1

        sources = verify_db.query(CrawlRunSource).all()
        assert len(sources) == 1
        assert sources[0].status == CrawlRunSourceStatus.completed
    finally:
        verify_db.close()


def test_stream_cancels_previous_running_crawl(client, seed_source, db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    stale_db = TestSessionLocal()
    try:
        stale_run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        stale_db.add(stale_run)
        stale_db.flush()
        crs = CrawlRunSource(
            crawl_run_id=stale_run.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.pending,
        )
        stale_db.add(crs)
        stale_db.commit()
        stale_run_id = stale_run.id
    finally:
        stale_db.close()

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch(
            "app.routers.crawl.run_crawl_source",
            return_value={
                "source_id": seed_source.id,
                "new_documents": 1,
                "skipped": 0,
                "errors": 0,
                "discovery": {},
            },
        ),
    ):
        response = client.get("/api/crawl/stream")
    assert response.status_code == 200

    verify_db = TestSessionLocal()
    try:
        runs = verify_db.query(CrawlRun).all()
        assert len(runs) == 2
        old_run = next(r for r in runs if r.id == stale_run_id)
        assert old_run.status == CrawlRunStatus.cancelled
        assert old_run.finished_at is not None
        new_run = next(r for r in runs if r.id != stale_run_id)
        assert new_run.status == CrawlRunStatus.completed
    finally:
        verify_db.close()


def test_reconnect_no_active_run(client):
    response = client.get("/api/crawl/reconnect")
    assert response.status_code == 200
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert len(events) == 1
    assert events[0]["type"] == "no_active_run"


def test_reconnect_with_active_run(client, seed_source, db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_run_hangs(source, db, analyse=True, progress_callback=None):
        import time

        time.sleep(2)
        return {
            "source_id": source.id,
            "new_documents": 1,
            "skipped": 0,
            "errors": 0,
            "discovery": {},
        }

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run_hangs),
    ):
        pass

    verify_db = TestSessionLocal()
    try:
        crawl_run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        verify_db.add(crawl_run)
        verify_db.flush()
        crs = CrawlRunSource(
            crawl_run_id=crawl_run.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.running,
            current_step=CrawlRunStep.fetching,
        )
        verify_db.add(crs)
        verify_db.commit()
    finally:
        verify_db.close()

    response = client.get("/api/crawl/reconnect")
    assert response.status_code == 200
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events[0]["type"] == "initial_state"
    assert events[0]["total"] == 1
    assert len(events[0]["sources"]) == 1
    assert events[0]["sources"][0]["status"] == "running"
    assert events[0]["sources"][0]["current_step"] == "fetching"
    assert events[1]["type"] == "reconnect_complete"
