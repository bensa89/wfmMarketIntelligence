import pytest
from app.models.signal import Signal, SignalType
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document


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
