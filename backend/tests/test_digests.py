import pytest
from datetime import date
from app.models.digest import WeeklyDigest


@pytest.fixture
def seed_digest(db_session):
    d = WeeklyDigest(
        week_start=date(2026, 4, 14),
        week_end=date(2026, 4, 20),
        summary="Big week in AI WFM.",
        key_signals=["signal-id-1", "signal-id-2"],
        is_published=True,
    )
    db_session.add(d)
    db_session.commit()
    return d


def test_list_digests(client, seed_digest):
    response = client.get("/api/digests")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_digest_by_id(client, seed_digest):
    response = client.get(f"/api/digests/{seed_digest.id}")
    assert response.status_code == 200
    assert response.json()["summary"] == "Big week in AI WFM."
    assert response.json()["key_signals"] == ["signal-id-1", "signal-id-2"]


def test_generate_digest(client):
    response = client.post("/api/digests/generate")
    assert response.status_code == 201
    data = response.json()
    assert "week_start" in data
    assert "week_end" in data
    assert isinstance(data["key_signals"], list)
