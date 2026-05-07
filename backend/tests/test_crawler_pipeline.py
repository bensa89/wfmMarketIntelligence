import time
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


def test_analyse_doc_worker_success(db_session):
    """Worker returns (doc_id, True) on success."""
    from app.crawler.pipeline import _analyse_doc_worker
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from datetime import datetime, timezone

    company = Company(name="TestCo", slug="testco-w", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://test.com", source_type=SourceType.news, is_active=True)
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://test.com/art1",
        content_markdown="word " * 60,
        content_hash="h1",
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.commit()
    doc_id = doc.id

    with patch("app.analyser.pipeline.call_llm", return_value="{}"), patch(
        "app.analyser.pipeline.parse_llm_response", return_value=None
    ), patch("app.crawler.pipeline.SessionLocal", side_effect=lambda: MagicMock(wraps=db_session, close=MagicMock())):
        result_id, success = _analyse_doc_worker(doc_id, company.id, {})

    assert result_id == doc_id
    assert success is True


def test_analyse_doc_worker_exception_returns_false(db_session):
    """Worker returns (doc_id, False) when analyse_document raises."""
    from app.crawler.pipeline import _analyse_doc_worker
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from datetime import datetime, timezone

    company = Company(name="TestCo2", slug="testco-w2", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://test2.com", source_type=SourceType.news, is_active=True)
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://test2.com/art1",
        content_markdown="word " * 60,
        content_hash="h2",
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.commit()
    doc_id = doc.id

    with patch("app.analyser.pipeline.call_llm", side_effect=RuntimeError("LLM down")), patch(
        "app.crawler.pipeline.SessionLocal", return_value=db_session
    ):
        result_id, success = _analyse_doc_worker(doc_id, company.id, {})

    assert result_id == doc_id
    assert success is False


def test_parallel_analysis_faster_than_sequential():
    """With concurrency=3, 6 docs taking 0.3s each should finish in ~0.6s not ~1.8s."""
    import concurrent.futures
    import threading

    call_times = []
    lock = threading.Lock()

    def slow_worker(doc_id, company_id, context):
        time.sleep(0.3)
        with lock:
            call_times.append(time.monotonic())
        return doc_id, True

    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(slow_worker, f"doc-{i}", "co", {}) for i in range(6)]
        concurrent.futures.wait(futures)
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, f"Expected < 1.0s with concurrency=3, got {elapsed:.2f}s"
    assert len(call_times) == 6
