import pytest


def test_cast_value_casts_per_field_type():
    from app.settings_overrides import cast_value

    assert cast_value("crawl_concurrency", "9") == 9
    assert cast_value("search_relevance_threshold", "0.6") == 0.6
    assert cast_value("js_rendering_enabled", "true") is True
    assert cast_value("js_rendering_enabled", "false") is False
    assert cast_value("claude_model", "claude-x") == "claude-x"


def test_validate_value_rejects_unknown_llm_provider():
    from app.settings_overrides import validate_value

    with pytest.raises(ValueError):
        validate_value("llm_provider", "gpt4")
    validate_value("llm_provider", "ollama")  # does not raise


def test_apply_override_sets_live_settings_singleton():
    from app.settings_overrides import apply_override
    from app.config import settings

    apply_override("crawl_concurrency", "9")
    assert settings.crawl_concurrency == 9
    apply_override("crawl_concurrency", "4")  # restore


def test_reset_override_restores_env_default():
    from app.settings_overrides import apply_override, reset_override
    from app.config import settings

    apply_override("analysis_concurrency", "11")
    assert settings.analysis_concurrency == 11
    reset_override("analysis_concurrency")
    assert settings.analysis_concurrency == 3  # default from config.py


def test_load_overrides_from_db_applies_stored_rows(db_session):
    from app.models.app_setting import AppSetting
    from app.settings_overrides import load_overrides_from_db
    from app.config import settings

    db_session.add(AppSetting(key="discovery_depth", value="3"))
    db_session.commit()

    load_overrides_from_db(db_session)
    assert settings.discovery_depth == 3
