import logging
from typing import Any, Dict

from app.config import Settings, settings

logger = logging.getLogger(__name__)

OVERRIDABLE_FIELDS: Dict[str, type] = {
    "llm_provider": str,
    "claude_model": str,
    "ollama_base_url": str,
    "ollama_model": str,
    "opencode_model": str,
    "opencode_base_url": str,
    "discovery_depth": int,
    "js_rendering_enabled": bool,
    "search_relevance_threshold": float,
    "search_queries_per_company": int,
    "assessment_threshold": float,
    "crawl_concurrency": int,
    "discovery_concurrency": int,
    "analysis_concurrency": int,
}

LLM_PROVIDER_CHOICES = {"claude", "ollama", "opencode"}


def cast_value(key: str, raw_value: str) -> Any:
    field_type = OVERRIDABLE_FIELDS[key]
    if field_type is bool:
        return raw_value.strip().lower() in ("true", "1", "yes")
    if field_type is int:
        return int(raw_value)
    if field_type is float:
        return float(raw_value)
    return raw_value


def validate_value(key: str, value: Any) -> None:
    if key == "llm_provider" and value not in LLM_PROVIDER_CHOICES:
        raise ValueError(f"llm_provider must be one of {sorted(LLM_PROVIDER_CHOICES)}")


def default_value(key: str) -> Any:
    return getattr(Settings(), key)


def load_overrides_from_db(db) -> None:
    from app.models.app_setting import AppSetting

    for row in db.query(AppSetting).all():
        if row.key not in OVERRIDABLE_FIELDS:
            continue
        try:
            value = cast_value(row.key, row.value)
            setattr(settings, row.key, value)
        except (ValueError, TypeError):
            logger.warning("Skipping invalid stored setting %s=%s", row.key, row.value)


def apply_override(key: str, raw_value: str) -> Any:
    value = cast_value(key, raw_value)
    validate_value(key, value)
    setattr(settings, key, value)
    return value


def reset_override(key: str) -> Any:
    value = default_value(key)
    setattr(settings, key, value)
    return value
