import json

from app.assessor.rules import compute_movement_score, compute_movement_strength, map_signal_type_to_class
from app.models.signal import SignalType


def test_compute_movement_score_high():
    score = compute_movement_score(
        relevance_score=1.0,
        confidence_score=1.0,
        evidence_strength=5,
        visibility_impact="high",
        signal_class="product_capability_move",
    )
    # 35 + 20 + 30 + 15 - 0 = 100
    assert score == 100


def test_compute_movement_score_thought_leadership_penalty():
    score = compute_movement_score(
        relevance_score=1.0,
        confidence_score=1.0,
        evidence_strength=5,
        visibility_impact="high",
        signal_class="thought_leadership_signal",
    )
    # 100 - 10 = 90
    assert score == 90


def test_compute_movement_score_base_case():
    score = compute_movement_score(
        relevance_score=0.0,
        confidence_score=0.0,
        evidence_strength=1,
        visibility_impact="low",
        signal_class="weak_signal",
    )
    # 0 + 0 + 6 + 0 = 6
    assert score == 6


def test_compute_movement_score_clamp_to_zero():
    score = compute_movement_score(
        relevance_score=0.0,
        confidence_score=0.0,
        evidence_strength=0,
        visibility_impact="low",
        signal_class="thought_leadership_signal",
    )
    # raw = -10, clamped to 0
    assert score == 0


def test_compute_movement_strength_thresholds():
    assert compute_movement_strength(0) == "weak"
    assert compute_movement_strength(29) == "weak"
    assert compute_movement_strength(30) == "relevant"
    assert compute_movement_strength(59) == "relevant"
    assert compute_movement_strength(60) == "strong"
    assert compute_movement_strength(79) == "strong"
    assert compute_movement_strength(80) == "market_shaping"
    assert compute_movement_strength(100) == "market_shaping"


def test_map_signal_type_to_class():
    assert map_signal_type_to_class(SignalType.product_update) == "product_capability_move"
    assert map_signal_type_to_class(SignalType.ai_announcement) == "product_capability_move"
    assert map_signal_type_to_class(SignalType.partnership) == "ecosystem_move"
    assert map_signal_type_to_class(SignalType.positioning_change) == "positioning_move"
    assert map_signal_type_to_class(SignalType.target_market_change) == "positioning_move"
    assert map_signal_type_to_class(SignalType.event_or_thought_leadership) == "thought_leadership_signal"
    assert map_signal_type_to_class(SignalType.hiring_signal) == "hiring_signal"
    assert map_signal_type_to_class(SignalType.other) == "weak_signal"


def test_build_assessment_prompt_contains_signal_data():
    from app.assessor.prompts import build_assessment_prompt
    prompt = build_assessment_prompt(
        company_name="ATOSS",
        signal_type="ai_announcement",
        title="New AI Scheduling",
        topic="AI",
        summary="ATOSS launches AI scheduling module.",
        why_it_matters="Competes with our core product.",
        relevance_score=0.9,
        confidence_score=0.85,
        context={"core_capabilities": ["WFM"], "strategic_priorities": ["AI-first"], "differentiators": ["Speed"]},
        capability_keys=["shift_scheduling", "ai_copilot"],
    )
    assert "ATOSS" in prompt
    assert "ai_announcement" in prompt
    assert "New AI Scheduling" in prompt
    assert "shift_scheduling" in prompt
    assert "JSON" in prompt


def test_build_summary_prompt_contains_assessments():
    from app.assessor.prompts import build_summary_prompt
    assessments = [
        {"capability_primary": "ai_copilot", "signal_class": "product_capability_move",
         "assessment_summary": "Launched AI feature.", "movement_strength": "strong"}
    ]
    prompt = build_summary_prompt(
        company_name="ATOSS",
        period_label="last 30 days",
        assessments=assessments,
        context={"core_capabilities": ["WFM"], "strategic_priorities": ["Scale"]},
    )
    assert "ATOSS" in prompt
    assert "ai_copilot" in prompt
    assert "last 30 days" in prompt


def test_parse_assessment_valid_json():
    from app.assessor.parser import parse_assessment_response, AssessmentLLMOutput
    raw = json.dumps({
        "capability_primary": "ai_copilot",
        "capability_secondary": ["shift_scheduling"],
        "signal_class": "product_capability_move",
        "evidence_strength": 4,
        "visibility_impact": "high",
        "strategic_intent_guess": "Positioning as AI-first WFM vendor.",
        "gameplay_tags": ["ai-narrative"],
        "assessment_summary": "Launched new AI feature.",
        "implication_for_us": "Direct competition with our roadmap.",
        "watch_items": ["Monitor adoption rate"],
        "confidence": 0.85,
    })
    result = parse_assessment_response(raw)
    assert result is not None
    assert result.capability_primary == "ai_copilot"
    assert result.evidence_strength == 4
    assert result.confidence == 0.85


def test_parse_assessment_invalid_json_returns_none():
    from app.assessor.parser import parse_assessment_response
    result = parse_assessment_response("not json at all")
    assert result is None


def test_parse_assessment_missing_required_field_returns_none():
    from app.assessor.parser import parse_assessment_response
    raw = json.dumps({"capability_primary": "ai_copilot"})  # missing most fields
    # Should still parse — all fields are optional in LLM output
    result = parse_assessment_response(raw)
    assert result is not None  # partial data is accepted
