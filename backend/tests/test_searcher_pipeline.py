import os

os.environ["AUTH_USERNAME"] = "testuser"
os.environ["AUTH_PASSWORD"] = "testpass"
os.environ["DATABASE_URL"] = "sqlite:///./test_search_pipeline.db"

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.company import Company, CompanyType
from app.models.search_run import SearchRunStatus
from app.models.search_result import SearchResultStatus
from app.models.source_candidate import SourceCandidateStatus
from app.searcher.pipeline import run_search_for_company
from app.searcher.client import TavilyResult
from app.searcher.query_generator import QuerySpec

TEST_DB = "./test_search_pipeline.db"


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os as _os

    if _os.path.exists(TEST_DB):
        _os.remove(TEST_DB)


@pytest.fixture
def company(db_session):
    c = Company(name="Quinyx", slug="quinyx", type=CompanyType.competitor)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def test_run_search_creates_search_run_and_results(db_session, company):
    fake_queries = [
        QuerySpec(query_text="Quinyx AI 2025", search_intent="ai_announcement")
    ]
    fake_results = [
        TavilyResult(
            title="Quinyx AI news",
            url="https://techcrunch.com/quinyx-ai",
            domain="techcrunch.com",
            snippet="Quinyx launched AI features.",
            score=0.9,
        )
    ]

    with (
        patch(
            "app.searcher.pipeline.generate_queries_for_company",
            return_value=fake_queries,
        ),
        patch("app.searcher.pipeline.search_tavily", return_value=fake_results),
        patch("app.searcher.pipeline.fetch_url") as mock_fetch,
        patch("app.searcher.pipeline.extract_content") as mock_extract,
        patch("app.searcher.pipeline.analyse_document"),
    ):
        mock_fetch.return_value = MagicMock(
            html="<p>content</p>",
            final_url="https://techcrunch.com/quinyx-ai",
            status_code=200,
        )
        mock_extract.return_value = MagicMock(
            title="Quinyx AI news", markdown="# Quinyx AI", content_hash="abc123"
        )

        result = run_search_for_company(company, db_session)

    assert result["queries_generated"] == 1
    assert result["results_found"] == 1
    assert result["documents_created"] >= 1

    from app.models.search_run import SearchRun

    run = db_session.query(SearchRun).first()
    assert run is not None
    assert run.status == SearchRunStatus.done

    from app.models.search_result import SearchResult

    sr = db_session.query(SearchResult).first()
    assert sr is not None
    assert sr.processing_status == SearchResultStatus.fetched


def test_run_search_skips_low_relevance_result(db_session, company):
    fake_queries = [QuerySpec(query_text="Quinyx pricing", search_intent="pricing")]
    fake_results = [
        TavilyResult(
            title="Old news",
            url="https://example.com/old",
            domain="example.com",
            snippet="Nothing relevant.",
            score=0.2,  # below default threshold of 0.5
        )
    ]

    with (
        patch(
            "app.searcher.pipeline.generate_queries_for_company",
            return_value=fake_queries,
        ),
        patch("app.searcher.pipeline.search_tavily", return_value=fake_results),
        patch("app.searcher.pipeline.analyse_document") as mock_analyse,
    ):
        result = run_search_for_company(company, db_session)

    mock_analyse.assert_not_called()

    from app.models.search_result import SearchResult

    sr = db_session.query(SearchResult).first()
    assert sr.processing_status == SearchResultStatus.skipped


def test_run_search_creates_source_candidate_for_new_domain(db_session, company):
    fake_queries = [QuerySpec(query_text="Quinyx partner", search_intent="partnership")]
    fake_results = [
        TavilyResult(
            title="News about Quinyx",
            url="https://newsite.com/quinyx-partner",
            domain="newsite.com",
            snippet="Quinyx partners with X.",
            score=0.8,
        )
    ]

    with (
        patch(
            "app.searcher.pipeline.generate_queries_for_company",
            return_value=fake_queries,
        ),
        patch("app.searcher.pipeline.search_tavily", return_value=fake_results),
        patch("app.searcher.pipeline.fetch_url") as mock_fetch,
        patch("app.searcher.pipeline.extract_content") as mock_extract,
        patch("app.searcher.pipeline.analyse_document"),
    ):
        mock_fetch.return_value = MagicMock(
            html="<p>content</p>",
            final_url="https://newsite.com/quinyx-partner",
            status_code=200,
        )
        mock_extract.return_value = MagicMock(
            title="News", markdown="# News", content_hash="xyz789"
        )

        run_search_for_company(company, db_session)

    from app.models.source_candidate import SourceCandidate

    candidate = (
        db_session.query(SourceCandidate).filter_by(domain="newsite.com").first()
    )
    assert candidate is not None
    assert candidate.status == SourceCandidateStatus.candidate
    assert candidate.company_id == company.id
