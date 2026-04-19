from unittest.mock import patch


def test_run_search_all_returns_results(client, db_session):
    mock_result = {"companies_searched": 0, "results": []}
    with patch("app.routers.search.run_search_all_companies", return_value=mock_result):
        resp = client.post("/api/search/run")
    assert resp.status_code == 200
    data = resp.json()
    assert "companies_searched" in data


def test_run_search_for_company_returns_404_if_not_found(client):
    resp = client.post("/api/search/run/nonexistent-id")
    assert resp.status_code == 404


def test_run_search_for_company_returns_result(client, db_session):
    from app.models.company import Company, CompanyType

    company = Company(name="TestCo", slug="testco", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    mock_result = {
        "company_id": company.id,
        "queries_generated": 2,
        "results_found": 5,
        "documents_created": 1,
    }
    with patch("app.routers.search.run_search_for_company", return_value=mock_result):
        resp = client.post(f"/api/search/run/{company.id}")
    assert resp.status_code == 200
    assert resp.json()["queries_generated"] == 2


def test_list_search_runs_returns_empty(client):
    resp = client.get("/api/search/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_search_results_returns_empty(client):
    resp = client.get("/api/search/results")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_source_candidates_returns_empty(client):
    resp = client.get("/api/source-candidates")
    assert resp.status_code == 200
    assert resp.json() == []


def test_approve_source_candidate(client, db_session):
    from app.models.company import Company, CompanyType
    from app.models.source_candidate import SourceCandidate, SourceCandidateStatus

    company = Company(name="TestCo2", slug="testco2", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    candidate = SourceCandidate(
        url="https://newssite.com/article",
        domain="newssite.com",
        title="News Site",
        snippet="A news site about WFM.",
        company_id=company.id,
        relevance_score=0.8,
        status=SourceCandidateStatus.candidate,
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    resp = client.post(
        f"/api/source-candidates/{candidate.id}/approve",
        json={"label": "News Site", "source_type": "news"},
    )
    assert resp.status_code == 200

    db_session.refresh(candidate)
    assert candidate.status == SourceCandidateStatus.monitored

    from app.models.source import Source

    source = (
        db_session.query(Source)
        .filter(Source.url == "https://newssite.com/article")
        .first()
    )
    assert source is not None
    assert source.label == "News Site"


def test_reject_source_candidate(client, db_session):
    from app.models.source_candidate import SourceCandidate, SourceCandidateStatus

    candidate = SourceCandidate(
        url="https://spam.com/article",
        domain="spam.com",
        title="Spam",
        snippet="Irrelevant.",
        relevance_score=0.3,
        status=SourceCandidateStatus.candidate,
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    resp = client.post(f"/api/source-candidates/{candidate.id}/reject")
    assert resp.status_code == 200

    db_session.refresh(candidate)
    assert candidate.status == SourceCandidateStatus.rejected
