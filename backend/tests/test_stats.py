from datetime import datetime, timedelta, timezone

import pytest
from app.models.signal import Signal, SignalType
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.crawl_run import CrawlRun, CrawlRunStatus


def test_signals_over_time_empty(client):
    response = client.get("/api/stats/signals/over-time")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_signals_over_time_with_days(client):
    response = client.get("/api/stats/signals/over-time?days=30")
    assert response.status_code == 200


def test_signal_distribution_empty(client):
    response = client.get("/api/stats/signals/distribution")
    assert response.status_code == 200
    data = response.json()
    assert "by_type" in data
    assert "by_company_and_type" in data


def test_discovered_pages_stats(client):
    response = client.get("/api/discovered-pages/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "new" in data
    assert "changed" in data
    assert "known" in data


def _make_company_and_source(db_session):
    company = Company(name="Acme", slug="acme", type=CompanyType.competitor)
    db_session.add(company)
    db_session.flush()
    source = Source(company_id=company.id, url="https://acme.example/news", source_type=SourceType.news)
    db_session.add(source)
    db_session.flush()
    return company, source


def test_last_crawl_summary_no_crawl_runs(client):
    response = client.get("/api/stats/last-crawl-summary")
    assert response.status_code == 200
    data = response.json()
    assert data["crawl_run"] is None
    assert data["new_signals"] == 0
    assert data["new_documents"] == 0
    assert data["high_relevance_signals"] == 0
    assert data["unanalysed_backlog"] == 0


def test_last_crawl_summary_ignores_single_source_runs(client, db_session):
    db_session.add(CrawlRun(status=CrawlRunStatus.completed, total_sources=1, total_errors=0))
    db_session.commit()

    response = client.get("/api/stats/last-crawl-summary")
    assert response.status_code == 200
    assert response.json()["crawl_run"] is None


def test_last_crawl_summary_with_global_run(client, db_session):
    company, source = _make_company_and_source(db_session)

    window_start = datetime.now(timezone.utc) - timedelta(hours=2)
    window_end = datetime.now(timezone.utc) - timedelta(hours=1)
    crawl_run = CrawlRun(
        status=CrawlRunStatus.completed,
        started_at=window_start,
        finished_at=window_end,
        total_sources=2,
        total_errors=3,
    )
    db_session.add(crawl_run)
    db_session.flush()

    in_window = window_start + timedelta(minutes=30)
    before_window = window_start - timedelta(hours=5)

    doc_in_window = Document(
        source_id=source.id, url="https://acme.example/a", crawled_at=in_window, is_analysed=True
    )
    doc_before_window = Document(
        source_id=source.id, url="https://acme.example/b", crawled_at=before_window, is_analysed=True
    )
    doc_unanalysed = Document(
        source_id=source.id, url="https://acme.example/c", crawled_at=in_window, is_analysed=False
    )
    db_session.add_all([doc_in_window, doc_before_window, doc_unanalysed])
    db_session.flush()

    signal_high_relevance = Signal(
        document_id=doc_in_window.id,
        company_id=company.id,
        title="High relevance",
        signal_type=SignalType.product_update,
        relevance_score=0.9,
        created_at=in_window,
    )
    signal_low_relevance = Signal(
        document_id=doc_in_window.id,
        company_id=company.id,
        title="Low relevance",
        signal_type=SignalType.other,
        relevance_score=0.2,
        created_at=in_window,
    )
    signal_outside_window = Signal(
        document_id=doc_before_window.id,
        company_id=company.id,
        title="Outside window",
        signal_type=SignalType.other,
        relevance_score=0.9,
        created_at=before_window,
    )
    db_session.add_all([signal_high_relevance, signal_low_relevance, signal_outside_window])
    db_session.commit()

    response = client.get("/api/stats/last-crawl-summary")
    assert response.status_code == 200
    data = response.json()
    assert data["crawl_run"]["id"] == crawl_run.id
    assert data["crawl_run"]["total_errors"] == 3
    assert data["new_documents"] == 2
    assert data["new_signals"] == 2
    assert data["high_relevance_signals"] == 1
    assert data["unanalysed_backlog"] == 1
