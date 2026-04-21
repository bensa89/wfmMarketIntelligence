# backend/tests/test_briefings_router.py
from unittest.mock import patch
from app.models.crawl_briefing import CrawlBriefing
from datetime import datetime, timezone


def test_get_latest_briefing_404_when_none(client):
    response = client.get("/api/briefings/latest")
    assert response.status_code == 404


def test_get_latest_briefing_returns_most_recent(client, db_session):
    older = CrawlBriefing(
        content="older briefing",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = CrawlBriefing(
        content="newer briefing",
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get("/api/briefings/latest")
    assert response.status_code == 200
    assert response.json()["content"] == "newer briefing"


def test_generate_briefing(client):
    with patch(
        "app.routers.briefings.generate_briefing_content",
        return_value="Test briefing content",
    ):
        response = client.post("/api/briefings/generate", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Test briefing content"
    assert data["crawl_run_id"] is None


def test_generate_briefing_with_crawl_run_id(client):
    with patch(
        "app.routers.briefings.generate_briefing_content",
        return_value="Briefing with run",
    ):
        response = client.post(
            "/api/briefings/generate", json={"crawl_run_id": "some-run-id"}
        )
    assert response.status_code == 200
    assert response.json()["crawl_run_id"] == "some-run-id"
