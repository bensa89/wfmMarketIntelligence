import pytest
from unittest.mock import patch, MagicMock


FULL_PAYLOAD = {
    "crawl_enabled": False,
    "crawl_day_of_week": 0,
    "crawl_time": "06:00",
    "crawl_timezone": "Europe/Berlin",
    "digest_after_crawl": True,
    "digest_enabled": False,
    "digest_day_of_week": 1,
    "digest_time": "08:00",
    "email_enabled": False,
    "email_recipients": [],
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
}


def test_get_schedule_returns_defaults(client):
    with patch("app.routers.schedule.apply_schedule"):
        response = client.get("/api/schedule")
    assert response.status_code == 200
    data = response.json()
    assert "config" in data
    assert data["config"]["crawl_enabled"] is False
    assert data["next_crawl"] is None
    assert data["next_digest"] is None


def test_put_schedule_saves_config(client):
    payload = {**FULL_PAYLOAD, "crawl_enabled": True, "crawl_time": "07:30"}

    with patch("app.routers.schedule.apply_schedule") as mock_apply:
        response = client.put("/api/schedule", json=payload)
        assert response.status_code == 200
        mock_apply.assert_called_once()

    # Verify persisted
    with patch("app.routers.schedule.apply_schedule"):
        get_response = client.get("/api/schedule")
    assert get_response.json()["config"]["crawl_enabled"] is True
    assert get_response.json()["config"]["crawl_time"] == "07:30"


def test_put_schedule_returns_updated_config(client):
    payload = {**FULL_PAYLOAD, "crawl_day_of_week": 4}

    with patch("app.routers.schedule.apply_schedule"):
        response = client.put("/api/schedule", json=payload)
    assert response.json()["config"]["crawl_day_of_week"] == 4


def test_put_schedule_rejects_invalid_day(client):
    payload = {**FULL_PAYLOAD, "crawl_day_of_week": 7}  # invalid: 0-6 only

    with patch("app.routers.schedule.apply_schedule"):
        response = client.put("/api/schedule", json=payload)
    assert response.status_code == 422


def test_test_email_returns_400_on_smtp_failure(client):
    # First configure email
    payload = {
        **FULL_PAYLOAD,
        "email_enabled": True,
        "email_recipients": ["test@example.com"],
        "smtp_host": "bad-host",
        "smtp_from": "from@example.com",
    }
    with patch("app.routers.schedule.apply_schedule"):
        client.put("/api/schedule", json=payload)

    with patch("app.notifications.email.send_crawl_report", side_effect=Exception("SMTP failed")):
        response = client.post("/api/schedule/test-email")
    assert response.status_code == 400
    assert "SMTP failed" in response.json()["detail"]


def test_test_email_returns_200_on_success(client):
    payload = {
        **FULL_PAYLOAD,
        "email_enabled": True,
        "email_recipients": ["test@example.com"],
        "smtp_host": "smtp.example.com",
        "smtp_from": "from@example.com",
    }
    with patch("app.routers.schedule.apply_schedule"):
        client.put("/api/schedule", json=payload)

    with patch("app.notifications.email.send_crawl_report"):
        response = client.post("/api/schedule/test-email")
    assert response.status_code == 200


def test_test_email_returns_400_when_no_recipients(client):
    with patch("app.routers.schedule.apply_schedule"):
        client.put("/api/schedule", json={**FULL_PAYLOAD, "email_enabled": True, "email_recipients": []})

    response = client.post("/api/schedule/test-email")
    assert response.status_code == 400


# --- POST /schedule/test-digest-email ---

def _configure_email(client):
    payload = {
        **FULL_PAYLOAD,
        "email_enabled": True,
        "email_recipients": ["test@example.com"],
        "smtp_host": "smtp.example.com",
        "smtp_from": "from@example.com",
    }
    with patch("app.routers.schedule.apply_schedule"):
        client.put("/api/schedule", json=payload)


def _create_digest(db_session):
    from datetime import date
    from app.models.digest import WeeklyDigest
    digest = WeeklyDigest(
        id="digest-test-id",
        week_start=date(2026, 6, 9),
        week_end=date(2026, 6, 15),
        summary="Test summary",
        sections=[
            {
                "key": "competitors",
                "title": "Wettbewerber",
                "items": [
                    {
                        "signal_id": "s1",
                        "company": "Acme",
                        "title": "Acme expands",
                        "narrative": "Narrative text",
                        "implication_for_us": "Watch out",
                        "movement_strength": "moderate",
                        "source_url": "https://example.com/acme",
                        "source_domain": "example.com",
                        "source_title": "Example – Acme",
                    }
                ],
            }
        ],
    )
    db_session.add(digest)
    db_session.commit()
    return digest


def test_test_digest_email_returns_400_when_no_digest(client):
    _configure_email(client)
    response = client.post("/api/schedule/test-digest-email")
    assert response.status_code == 400
    assert "Digest" in response.json()["detail"]


def test_test_digest_email_returns_400_when_no_recipients(client):
    response = client.post("/api/schedule/test-digest-email")
    assert response.status_code == 400


def test_test_digest_email_returns_200_on_success(client, db_session):
    _configure_email(client)
    _create_digest(db_session)
    with patch("app.notifications.email.send_digest_email"):
        response = client.post("/api/schedule/test-digest-email")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert data["digest_id"] == "digest-test-id"
    assert "test@example.com" in data["recipients"]


def test_test_digest_email_returns_400_on_smtp_failure(client, db_session):
    _configure_email(client)
    _create_digest(db_session)
    with patch("app.notifications.email.send_digest_email", side_effect=Exception("SMTP failed")):
        response = client.post("/api/schedule/test-digest-email")
    assert response.status_code == 400
    assert "SMTP failed" in response.json()["detail"]
