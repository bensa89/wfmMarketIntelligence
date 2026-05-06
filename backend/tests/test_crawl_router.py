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


def test_crawl_run_status_has_queued():
    assert CrawlRunStatus.queued == "queued"


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
    assert events[0]["type"] == "no_active_run"
    assert events[-1]["type"] == "reconnect_complete"


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


def test_enqueue_creates_queued_run(client, seed_source, db_engine):
    """Enqueue a source when no queued run exists — creates one."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    # Create a running run first so enqueue is valid
    setup_db = TestSessionLocal()
    try:
        running_run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running_run)
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.post(f"/api/crawl/enqueue/{seed_source.id}")
    assert response.status_code == 202
    data = response.json()
    assert data["queued"] is True
    assert data["position"] == 1

    verify_db = TestSessionLocal()
    try:
        queued = (
            verify_db.query(CrawlRun)
            .filter(CrawlRun.status == CrawlRunStatus.queued)
            .first()
        )
        assert queued is not None
        assert len(queued.sources) == 1
        assert queued.sources[0].source_id == seed_source.id
    finally:
        verify_db.close()


def test_enqueue_appends_to_existing_queued_run(client, db_session, db_engine):
    """Enqueueing a second source appends to the existing queued run."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    company = Company(name="Co2", slug="co2-enqueue", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    source_a = Source(
        company_id=company.id,
        url="https://a.com",
        source_type=SourceType.news,
        is_active=True,
    )
    source_b = Source(
        company_id=company.id,
        url="https://b.com",
        source_type=SourceType.news,
        is_active=True,
    )
    db_session.add_all([source_a, source_b])
    db_session.commit()

    # Seed a running run + queued run with source_a already in it
    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(
            CrawlRunSource(
                crawl_run_id=queued.id,
                source_id=source_a.id,
                url=source_a.url,
                status=CrawlRunSourceStatus.pending,
            )
        )
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.post(f"/api/crawl/enqueue/{source_b.id}")
    assert response.status_code == 202
    data = response.json()
    assert data["position"] == 2

    verify_db = TestSessionLocal()
    try:
        queued_runs = (
            verify_db.query(CrawlRun)
            .filter(CrawlRun.status == CrawlRunStatus.queued)
            .all()
        )
        assert len(queued_runs) == 1  # still only one queued run
        assert len(queued_runs[0].sources) == 2
    finally:
        verify_db.close()


def test_enqueue_noop_for_duplicate_source(client, db_session, db_engine):
    """Enqueueing a source already in the queue returns current position."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    company = Company(name="Co3", slug="co3-enqueue", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://dup.com",
        source_type=SourceType.news,
        is_active=True,
    )
    db_session.add(source)
    db_session.commit()

    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(
            CrawlRunSource(
                crawl_run_id=queued.id,
                source_id=source.id,
                url=source.url,
                status=CrawlRunSourceStatus.pending,
            )
        )
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.post(f"/api/crawl/enqueue/{source.id}")
    assert response.status_code == 202
    assert response.json()["position"] == 1  # still 1, not added twice

    verify_db = TestSessionLocal()
    try:
        queued = (
            verify_db.query(CrawlRun)
            .filter(CrawlRun.status == CrawlRunStatus.queued)
            .first()
        )
        assert len(queued.sources) == 1
    finally:
        verify_db.close()


def test_enqueue_nonexistent_source_returns_404(client):
    response = client.post("/api/crawl/enqueue/nonexistent-id")
    assert response.status_code == 404


def test_stream_queued_returns_404_when_no_queue(client):
    response = client.get("/api/crawl/stream/queued")
    assert response.status_code == 404


def test_stream_queued_runs_queued_sources(client, seed_source, db_engine):
    """Starting stream/queued transitions the queued run to running and streams events."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    setup_db = TestSessionLocal()
    try:
        queued_run = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued_run)
        setup_db.flush()
        setup_db.add(
            CrawlRunSource(
                crawl_run_id=queued_run.id,
                source_id=seed_source.id,
                url=seed_source.url,
                status=CrawlRunSourceStatus.pending,
            )
        )
        setup_db.commit()
        queued_run_id = queued_run.id
    finally:
        setup_db.close()

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
        response = client.get("/api/crawl/stream/queued")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert "crawl_start" in event_types
    assert "crawl_done" in event_types

    # Verify the queued run is now completed in DB
    verify_db = TestSessionLocal()
    try:
        run = verify_db.query(CrawlRun).filter(CrawlRun.id == queued_run_id).first()
        assert run.status == CrawlRunStatus.completed
    finally:
        verify_db.close()


def test_reconnect_returns_queued_state(client, seed_source, db_engine):
    """Reconnect includes queued_state event when a queued run exists."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        setup_db.flush()
        setup_db.add(
            CrawlRunSource(
                crawl_run_id=running.id,
                source_id=seed_source.id,
                url=seed_source.url,
                status=CrawlRunSourceStatus.running,
            )
        )
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(
            CrawlRunSource(
                crawl_run_id=queued.id,
                source_id=seed_source.id,
                url=seed_source.url,
                status=CrawlRunSourceStatus.pending,
            )
        )
        setup_db.commit()
        queued_id = queued.id
    finally:
        setup_db.close()

    response = client.get("/api/crawl/reconnect")
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    types = [e["type"] for e in events]
    assert "initial_state" in types
    assert "queued_state" in types

    qs = next(e for e in events if e["type"] == "queued_state")
    assert qs["crawl_run_id"] == queued_id
    assert len(qs["sources"]) == 1
    assert qs["sources"][0]["source_id"] == seed_source.id


def test_crawl_run_source_status_has_analysing():
    assert CrawlRunSourceStatus.analysing == "analysing"
    assert CrawlRunStep.analysing == "analysing"


def test_stream_all_sources_includes_analysis_events(client, seed_source, db_engine):
    from app.models.source import AnalysisStatus

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

    def mock_analyse(source, db, progress_callback=None):
        events_out = []
        if progress_callback:
            events_out.append(
                {
                    "type": "analysis_progress",
                    "source_id": source.id,
                    "current": 1,
                    "total": 1,
                    "url": source.url,
                }
            )
        return {"source_id": source.id, "analysed": 1, "errors": 0, "analyse_ms": 50}

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run),
        patch(
            "app.routers.crawl.analyse_unanalysed_for_source", side_effect=mock_analyse
        ),
    ):
        response = client.get("/api/crawl/stream")

    assert response.status_code == 200
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert "analysis_phase_start" in event_types
    assert "analysis_start" in event_types
    assert "analysis_done" in event_types
    assert "analysis_phase_done" in event_types

    phase_start = next(e for e in events if e["type"] == "analysis_phase_start")
    assert "crawl_run_id" in phase_start

    analysis_start = next(e for e in events if e["type"] == "analysis_start")
    assert analysis_start["source_id"] == seed_source.id
    assert "crawl_run_id" in analysis_start

    analysis_done = next(e for e in events if e["type"] == "analysis_done")
    assert analysis_done["source_id"] == seed_source.id
    assert analysis_done["analysed"] == 1

    phase_done = next(e for e in events if e["type"] == "analysis_phase_done")
    assert "crawl_run_id" in phase_done


def test_stream_skips_analysis_when_no_new_documents(client, seed_source, db_engine):
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
        patch("app.routers.crawl.analyse_unanalysed_for_source") as mock_analyse,
    ):
        response = client.get("/api/crawl/stream")

    assert response.status_code == 200
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert "analysis_phase_start" not in event_types
    assert "analysis_start" not in event_types
    assert "analysis_done" not in event_types
    mock_analyse.assert_not_called()


def test_crawl_all_sources_calls_analyse_unanalysed(client, seed_source):
    from app.models.source import AnalysisStatus

    mock_result = {
        "source_id": seed_source.id,
        "new_documents": 1,
        "skipped": 0,
        "errors": 0,
    }
    mock_analysis = {
        "source_id": seed_source.id,
        "analysed": 1,
        "errors": 0,
        "analyse_ms": 42,
    }
    with (
        patch("app.routers.crawl.run_crawl_source", return_value=mock_result),
        patch(
            "app.routers.crawl.analyse_unanalysed_for_source",
            return_value=mock_analysis,
        ) as mock_analyse,
    ):
        response = client.post("/api/crawl/run")
    assert response.status_code == 200
    mock_analyse.assert_called_once()


def test_crawl_single_source_calls_analyse_unanalysed(client, seed_source):
    mock_result = {
        "source_id": seed_source.id,
        "new_documents": 1,
        "skipped": 0,
        "errors": 0,
    }
    mock_analysis = {
        "source_id": seed_source.id,
        "analysed": 1,
        "errors": 0,
        "analyse_ms": 30,
    }
    with (
        patch("app.routers.crawl.run_crawl_source", return_value=mock_result),
        patch(
            "app.routers.crawl.analyse_unanalysed_for_source",
            return_value=mock_analysis,
        ) as mock_analyse,
    ):
        response = client.post(f"/api/crawl/run/{seed_source.id}")
    assert response.status_code == 200
    mock_analyse.assert_called_once()


def test_reconnect_queued_state_only_when_no_running_run(
    client, seed_source, db_engine
):
    """When no running run exists but a queued one does, only queued_state is sent."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    setup_db = TestSessionLocal()
    try:
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(
            CrawlRunSource(
                crawl_run_id=queued.id,
                source_id=seed_source.id,
                url=seed_source.url,
                status=CrawlRunSourceStatus.pending,
            )
        )
        setup_db.commit()
        queued_id = queued.id
    finally:
        setup_db.close()

    response = client.get("/api/crawl/reconnect")
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    types = [e["type"] for e in events]
    assert "initial_state" not in types
    assert "no_active_run" not in types
    assert "queued_state" in types
    assert types[-1] == "reconnect_complete"
