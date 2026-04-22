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
    evidence_strength: Optional[int] = Field(default=None, ge=1, le=5)
    visibility_impact: Optional[str] = None
    strategic_intent_guess: Optional[str] = None
    gameplay_tags: list[str] = Field(default_factory=list)
    assessment_summary: Optional[str] = None
    implication_for_us: Optional[str] = None
    watch_items: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

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


class SummaryLLMOutput(BaseModel):
    strategic_posture: Optional[str] = None
    positioning_summary: Optional[str] = None
    top_capabilities: list[str] = Field(default_factory=list)
    capability_assessment: list[dict] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    top_opportunities: list[str] = Field(default_factory=list)
    watchpoints: list[str] = Field(default_factory=list)


def _extract_json(raw: str) -> Optional[dict]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
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
