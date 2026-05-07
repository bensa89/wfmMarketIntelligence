import pytest
from datetime import datetime, timezone
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


def test_analysis_progress_callback_receives_doc_url(db_session, seed_source):
    from unittest.mock import patch
    from app.crawler.pipeline import analyse_unanalysed_for_source
    from app.models.document import Document

    doc = Document(
        source_id=seed_source.id,
        url="https://seed.example.com/article",
        title="Test",
        content_markdown="word " * 60,
        content_hash="abc123",
        is_analysed=False,
    )
    db_session.add(doc)
    db_session.commit()

    received_urls = []

    def cb(event):
        if event.get("type") == "analysis_progress":
            received_urls.append(event.get("url"))

    with patch("app.crawler.pipeline._analyse_doc_worker", return_value=(doc.id, True)):
        analyse_unanalysed_for_source(seed_source, db_session, progress_callback=cb)

    assert len(received_urls) == 1
    assert received_urls[0] == "https://seed.example.com/article"


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


def test_crawl_run_source_status_has_analysing():
    assert CrawlRunSourceStatus.analysing == "analysing"
    assert CrawlRunStep.analysing == "analysing"




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


def test_crawl_run_source_read_schema_has_analyse_progress(db_session, seed_source):
    from app.models.crawl_run import CrawlRun, CrawlRunSource, CrawlRunStatus, CrawlRunSourceStatus
    from app.schemas.crawl_run import CrawlRunSourceRead
    run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
    db_session.add(run)
    db_session.flush()
    crs = CrawlRunSource(
        crawl_run_id=run.id,
        source_id=seed_source.id,
        url=seed_source.url,
        status=CrawlRunSourceStatus.analysing,
        analyse_docs_done=3,
        analyse_docs_total=7,
        analyse_current_url="https://example.com/doc",
    )
    db_session.add(crs)
    db_session.commit()
    schema = CrawlRunSourceRead.model_validate(crs)
    assert schema.analyse_docs_done == 3
    assert schema.analyse_docs_total == 7
    assert schema.analyse_current_url == "https://example.com/doc"


def test_crawl_run_source_has_analyse_progress_fields(db_session, seed_source):
    from app.models.crawl_run import CrawlRun, CrawlRunSource, CrawlRunStatus, CrawlRunSourceStatus
    run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
    db_session.add(run)
    db_session.flush()
    crs = CrawlRunSource(
        crawl_run_id=run.id,
        source_id=seed_source.id,
        url=seed_source.url,
        status=CrawlRunSourceStatus.analysing,
        analyse_docs_done=2,
        analyse_docs_total=5,
        analyse_current_url="https://example.com/page",
    )
    db_session.add(crs)
    db_session.commit()
    db_session.expire_all()
    loaded = db_session.query(CrawlRunSource).filter(CrawlRunSource.id == crs.id).first()
    assert loaded.analyse_docs_done == 2
    assert loaded.analyse_docs_total == 5
    assert loaded.analyse_current_url == "https://example.com/page"


def test_crawl_status_no_active_run(client):
    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"] is None
    assert data["queued_run"] is None


def test_crawl_status_running_run(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    setup_db = TestSessionLocal()
    try:
        run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(run)
        setup_db.flush()
        crs = CrawlRunSource(
            crawl_run_id=run.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.analysing,
            analyse_docs_done=1,
            analyse_docs_total=3,
            analyse_current_url="https://example.com/p",
        )
        setup_db.add(crs)
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"] is not None
    assert data["active_run"]["status"] == "running"
    assert len(data["active_run"]["sources"]) == 1
    src = data["active_run"]["sources"][0]
    assert src["status"] == "analysing"
    assert src["analyse_docs_done"] == 1
    assert src["analyse_docs_total"] == 3
    assert src["analyse_current_url"] == "https://example.com/p"


def test_crawl_status_shows_queued_run(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=running.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.running,
        ))
        setup_db.add(CrawlRunSource(
            crawl_run_id=queued.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.pending,
        ))
        setup_db.commit()
        queued_id = queued.id
    finally:
        setup_db.close()

    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"]["status"] == "running"
    assert data["queued_run"] is not None
    assert data["queued_run"]["id"] == queued_id
    assert len(data["queued_run"]["sources"]) == 1


def test_crawl_status_returns_recent_completed_run(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    from datetime import timedelta
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    setup_db = TestSessionLocal()
    try:
        run = CrawlRun(
            status=CrawlRunStatus.completed,
            total_sources=1,
            total_new=2,
            finished_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        setup_db.add(run)
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"] is not None
    assert data["active_run"]["status"] == "completed"
    assert data["active_run"]["total_new"] == 2


def test_start_background_returns_202(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl._run_crawl_background"),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        response = client.post("/api/crawl/start")

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "running"
    assert data["crawl_run_id"] is not None
    assert data["total_sources"] == 1


def test_start_single_source_returns_202(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        response = client.post(f"/api/crawl/start/{seed_source.id}")

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "running"
    assert data["total_sources"] == 1


def test_start_creates_crawl_run_in_db(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        response = client.post("/api/crawl/start")

    assert response.status_code == 202
    verify_db = TestSessionLocal()
    try:
        runs = verify_db.query(CrawlRun).all()
        assert len(runs) == 1
        assert runs[0].status == CrawlRunStatus.running
        assert runs[0].total_sources == 1
    finally:
        verify_db.close()


def test_start_nonexistent_source_returns_404(client):
    response = client.post("/api/crawl/start/nonexistent-id")
    assert response.status_code == 404
