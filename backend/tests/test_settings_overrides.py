import pytest


@pytest.fixture(autouse=True)
def _restore_settings_overrides():
    from app.config import settings
    from app.settings_overrides import OVERRIDABLE_FIELDS

    snapshot = {key: getattr(settings, key) for key in OVERRIDABLE_FIELDS}
    yield
    for key, value in snapshot.items():
        setattr(settings, key, value)


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


def test_load_overrides_from_db_skips_bad_cast_row_without_raising(db_session):
    from app.models.app_setting import AppSetting
    from app.settings_overrides import load_overrides_from_db, default_value
    from app.config import settings

    baseline = default_value("discovery_depth")
    settings.discovery_depth = baseline

    db_session.add(AppSetting(key="discovery_depth", value="not-a-number"))
    db_session.commit()

    load_overrides_from_db(db_session)  # must not raise

    assert settings.discovery_depth == baseline
    assert isinstance(settings.discovery_depth, int)


def test_apply_override_does_not_mutate_settings_on_invalid_llm_provider():
    from app.settings_overrides import apply_override
    from app.config import settings

    original = settings.llm_provider

    with pytest.raises(ValueError):
        apply_override("llm_provider", "gpt4")

    assert settings.llm_provider == original
