from unittest.mock import patch
from datetime import datetime, timezone
from app.models.intelligence_briefing import IntelligenceBriefing


def test_get_latest_404_when_none(client):
    response = client.get("/api/intelligence/briefing/latest")
    assert response.status_code == 404


def test_get_latest_returns_most_recent(client, db_session):
    older = IntelligenceBriefing(
        content="old briefing",
        signal_count=5,
        assessment_count=3,
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = IntelligenceBriefing(
        content="new briefing",
        signal_count=10,
        assessment_count=8,
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get("/api/intelligence/briefing/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "new briefing"
    assert data["signal_count"] == 10
    assert data["assessment_count"] == 8


def test_generate_creates_and_returns_briefing(client):
    with patch(
        "app.routers.intelligence_briefing.generate_intelligence_briefing",
        return_value=("## Strategischer Überblick\nTest.", 12, 9),
    ):
        response = client.post("/api/intelligence/briefing/generate")

    assert response.status_code == 200
    data = response.json()
    assert "Strategischer Überblick" in data["content"]
    assert data["signal_count"] == 12
    assert data["assessment_count"] == 9
    assert data["id"] is not None
    assert data["generated_at"] is not None


def test_generate_persists_briefing(client, db_session):
    with patch(
        "app.routers.intelligence_briefing.generate_intelligence_briefing",
        return_value=("Briefing content", 3, 2),
    ):
        client.post("/api/intelligence/briefing/generate")

    stored = db_session.query(IntelligenceBriefing).first()
    assert stored is not None
    assert stored.content == "Briefing content"
