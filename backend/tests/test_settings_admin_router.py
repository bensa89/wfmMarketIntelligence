import pytest

from app.settings_overrides import OVERRIDABLE_FIELDS, default_value


@pytest.fixture(autouse=True)
def _restore_live_settings():
    from app.config import settings as live_settings

    snapshot = {key: getattr(live_settings, key) for key in OVERRIDABLE_FIELDS}
    yield
    for key, value in snapshot.items():
        setattr(live_settings, key, value)


def test_list_settings_shows_defaults_initially(client):
    response = client.get("/api/admin/settings")
    assert response.status_code == 200
    data = response.json()
    entry = next(s for s in data if s["key"] == "crawl_concurrency")
    assert entry["is_override"] is False
    assert entry["current_value"] == entry["default_value"] == str(default_value("crawl_concurrency"))


def test_put_setting_applies_immediately(client):
    from app.config import settings as live_settings

    response = client.put("/api/admin/settings/crawl_concurrency", json={"value": "9"})
    assert response.status_code == 200
    data = response.json()
    assert data["is_override"] is True
    assert data["current_value"] == "9"
    assert live_settings.crawl_concurrency == 9


def test_put_setting_rejects_invalid_llm_provider(client):
    response = client.put("/api/admin/settings/llm_provider", json={"value": "gpt4"})
    assert response.status_code == 422


def test_put_setting_rejects_unknown_key(client):
    response = client.put("/api/admin/settings/anthropic_api_key", json={"value": "sk-x"})
    assert response.status_code == 404


def test_delete_setting_resets_to_default(client):
    from app.config import settings as live_settings

    client.put("/api/admin/settings/crawl_concurrency", json={"value": "9"})
    response = client.delete("/api/admin/settings/crawl_concurrency")
    assert response.status_code == 200
    data = response.json()
    assert data["is_override"] is False
    assert live_settings.crawl_concurrency == default_value("crawl_concurrency")


def test_load_overrides_from_db_reapplies_after_restart(client, db_session):
    from app.config import settings as live_settings
    from app.settings_overrides import load_overrides_from_db

    client.put("/api/admin/settings/analysis_concurrency", json={"value": "7"})
    live_settings.analysis_concurrency = 3  # simulate a fresh process re-reading .env

    load_overrides_from_db(db_session)
    assert live_settings.analysis_concurrency == 7
