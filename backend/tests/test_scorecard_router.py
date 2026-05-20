import pytest
import app.models  # noqa
from datetime import datetime, timezone


def _make_company_with_scorecard(db, slug="test-co"):
    from app.models.company import Company, CompanyType
    from app.models.competitor_scorecard import CompetitorScorecard
    company = Company(name=slug.title(), slug=slug, type=CompanyType.competitor)
    db.add(company)
    db.commit()
    sc = CompetitorScorecard(
        company_id=company.id,
        period_type="30d",
        period_start=datetime.now(timezone.utc).date(),
        period_end=datetime.now(timezone.utc).date(),
        generated_at=datetime.now(timezone.utc),
        overall_score=72.5,
        overall_trend="rising",
        dimension_scores={},
        top_capabilities=[],
        top_moves=[],
        risk_flags=[],
        watchpoints=[],
        benchmark_position={"rank": 1, "percentile": 100, "total_competitors": 1},
        contributing_assessment_ids=[],
        is_current=True,
        scorecard_version="sc_v1",
        routing_version="v1",
    )
    db.add(sc)
    db.commit()
    return company, sc


def test_get_scorecard_requires_period_type(client):
    client.get("/api/scorecards/any-slug").status_code == 400


def test_get_scorecard_returns_404_for_unknown_company(client):
    r = client.get("/api/scorecards/no-such-company?period_type=30d")
    assert r.status_code == 404


def test_get_scorecard_returns_scorecard(client, db_session):
    company, sc = _make_company_with_scorecard(db_session)
    r = client.get(f"/api/scorecards/{company.slug}?period_type=30d")
    assert r.status_code == 200
    data = r.json()
    assert data["overall_score"] == pytest.approx(72.5)
    assert data["overall_trend"] == "rising"


def test_get_history_returns_list(client, db_session):
    company, sc = _make_company_with_scorecard(db_session)
    r = client.get(f"/api/scorecards/{company.slug}/history?period_type=30d")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 1


def test_get_benchmark_requires_period_type(client):
    assert client.get("/api/scorecards/benchmark").status_code == 400


def test_get_benchmark_returns_paginated(client, db_session):
    company, sc = _make_company_with_scorecard(db_session, "bench-co")
    r = client.get("/api/scorecards/benchmark?period_type=30d")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["period_type"] == "30d"


def test_get_explain_returns_404_when_no_scorecard(client):
    r = client.get("/api/scorecards/ghost-co/explain?period_type=30d")
    assert r.status_code == 404


def test_recompute_returns_ack(client, db_session):
    from unittest.mock import patch
    company, _ = _make_company_with_scorecard(db_session, "recompute-co")
    with patch("app.routers.scorecards.ScorecardBuilder") as mock_builder:
        instance = mock_builder.return_value
        from app.models.competitor_scorecard import CompetitorScorecard
        from datetime import datetime, timezone
        fake_sc = CompetitorScorecard(
            id="fake-id", company_id=company.id, period_type="30d",
            period_start=datetime.now(timezone.utc).date(),
            period_end=datetime.now(timezone.utc).date(),
            generated_at=datetime.now(timezone.utc),
            is_current=True,
        )
        instance.build.return_value = fake_sc
        r = client.post(f"/api/scorecards/{company.slug}/recompute")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["company_slug"] == company.slug
    assert "recomputed_periods" in body
