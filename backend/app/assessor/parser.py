import json
import logging
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class AssessmentLLMOutput(BaseModel):
    capability_primary: Optional[str] = None
    capability_secondary: list[str] = Field(default_factory=list)
    signal_class: Optional[str] = None
    evidence_strength: Optional[int] = None  # valid range: 1–5
    visibility_impact: Optional[str] = None
    strategic_intent_guess: Optional[str] = None
    gameplay_tags: list[str] = Field(default_factory=list)
    assessment_summary: Optional[str] = None
    implication_for_us: Optional[str] = None
    watch_items: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None  # valid range: 0.0–1.0
    buyer_relevance: Optional[int] = None
    assessment_weight: Optional[float] = None

    @field_validator("evidence_strength")
    @classmethod
    def validate_evidence_strength(cls, v):
        if v is not None and not (1 <= v <= 5):
            return None
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if v is not None and not (0.0 <= v <= 1.0):
            return None
        return v

    @field_validator("visibility_impact")
    @classmethod
    def validate_visibility_impact(cls, v):
        if v is not None and v not in ("low", "medium", "high"):
            return None
        return v

    @field_validator("signal_class")
    @classmethod
    def validate_signal_class(cls, v):
        valid = {
            "product_capability_move", "positioning_move", "ecosystem_move",
            "thought_leadership_signal", "hiring_signal", "weak_signal", "market_expansion_move",
        }
        if v is not None and v not in valid:
            return None
        return v

    @field_validator("buyer_relevance")
    @classmethod
    def validate_buyer_relevance(cls, v):
        if v is not None:
            try:
                v = max(1, min(5, int(v)))
            except (TypeError, ValueError):
                return None
        return v

    @field_validator("assessment_weight")
    @classmethod
    def validate_assessment_weight(cls, v):
        if v is not None:
            try:
                v = max(0.5, min(2.0, float(v)))
            except (TypeError, ValueError):
                return None
        return v


class SummaryLLMOutput(BaseModel):
    strategic_posture: Optional[str] = None
    positioning_summary: Optional[str] = None
    what_changed: Optional[str] = None
    top_capabilities: list[str] = Field(default_factory=list)
    capability_assessment: list[dict] = Field(default_factory=list)
    top_risks: list[dict] = Field(default_factory=list)
    top_opportunities: list[dict] = Field(default_factory=list)
    watchpoints: list[dict] = Field(default_factory=list)

    @staticmethod
    def _normalize_items(v) -> list[dict]:
        result = []
        for item in v or []:
            if isinstance(item, str):
                result.append({"text": item, "signal_ids": []})
            elif isinstance(item, dict):
                entry: dict = {
                    "text": item.get("text", ""),
                    "signal_ids": [s for s in item.get("signal_ids", []) if isinstance(s, str)],
                }
                if "is_new" in item and isinstance(item["is_new"], bool):
                    entry["is_new"] = item["is_new"]
                result.append(entry)
        return result

    @field_validator("top_risks", "top_opportunities", "watchpoints", mode="before")
    @classmethod
    def normalize_cited_items(cls, v):
        return cls._normalize_items(v)


def _extract_json(raw: str) -> Optional[dict]:
    # Strip markdown code fences if present
    stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Greedy match: works for typical LLM JSON-in-prose output
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def parse_assessment_response(raw: str) -> Optional[AssessmentLLMOutput]:
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        return AssessmentLLMOutput.model_validate(data)
    except Exception as e:
        logger.warning("Assessment validation error: %s", e)
        return None


def parse_summary_response(raw: str) -> Optional[SummaryLLMOutput]:
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        return SummaryLLMOutput.model_validate(data)
    except Exception as e:
        logger.warning("Summary validation error: %s", e)
        return None
