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


def test_compute_movement_score_clamp_min():
    score = compute_movement_score(
        relevance_score=0.0,
        confidence_score=0.0,
        evidence_strength=1,
        visibility_impact="low",
        signal_class="weak_signal",
    )
    # 0 + 0 + 6 + 0 = 6
    assert score == 6


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
