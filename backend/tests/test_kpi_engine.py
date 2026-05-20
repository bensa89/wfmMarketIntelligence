import pytest
from dataclasses import dataclass
from typing import Optional


def _inp(
    id="a1",
    movement_score=70,
    movement_strength="relevant",
    signal_class="product_capability_move",
    evidence_strength=3,
    visibility_impact="medium",
    confidence=0.8,
    capability_primary="shift_scheduling",
    capability_secondary=None,
    assessment_weight=1.0,
    dimension_modifier=1.0,
    age_days=0,
    period_days=30,
):
    from app.scorecard.kpi_engine import AssessmentKPIInput
    return AssessmentKPIInput(
        id=id,
        movement_score=movement_score,
        movement_strength=movement_strength,
        signal_class=signal_class,
        evidence_strength=evidence_strength,
        visibility_impact=visibility_impact,
        confidence=confidence,
        capability_primary=capability_primary,
        capability_secondary=capability_secondary or [],
        assessment_weight=assessment_weight,
        dimension_modifier=dimension_modifier,
        age_days=age_days,
        period_days=period_days,
    )


# --- effective_weight ---

def test_effective_weight_no_decay():
    a = _inp(assessment_weight=1.0, dimension_modifier=1.0, age_days=0, period_days=30)
    assert a.effective_weight == pytest.approx(1.0)


def test_effective_weight_full_decay_floor():
    from app.scorecard.constants import RECENCY_DECAY_MAX
    a = _inp(assessment_weight=1.0, dimension_modifier=1.0, age_days=30, period_days=30)
    expected = 1.0 * 1.0 * (1.0 - RECENCY_DECAY_MAX)
    assert a.effective_weight == pytest.approx(expected)


def test_effective_weight_combines_all_three():
    from app.scorecard.constants import RECENCY_DECAY_MAX
    a = _inp(assessment_weight=2.0, dimension_modifier=0.7, age_days=15, period_days=30)
    recency = 1.0 - (15 / 30) * RECENCY_DECAY_MAX
    assert a.effective_weight == pytest.approx(2.0 * 0.7 * recency)


# --- capability_strength KPIs ---

def test_cap_weighted_score_empty_returns_null():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    result = compute_capability_strength_kpis([])
    assert result["cap_weighted_score"].value is None


def test_cap_weighted_score_single_capability():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    inputs = [_inp(movement_score=80, evidence_strength=3, capability_primary="ai_copilot")]
    result = compute_capability_strength_kpis(inputs)
    assert result["cap_weighted_score"].value == pytest.approx(80.0)
    assert "a1" in result["cap_weighted_score"].contributing_ids


def test_cap_weighted_score_averages_capabilities_not_volume():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    # 3 signals in ai_copilot (score 90) and 1 in shift_scheduling (score 50)
    # Expected: mean([90, 50]) = 70, not biased by volume in ai_copilot
    inputs = [
        _inp(id="a1", movement_score=90, capability_primary="ai_copilot"),
        _inp(id="a2", movement_score=90, capability_primary="ai_copilot"),
        _inp(id="a3", movement_score=90, capability_primary="ai_copilot"),
        _inp(id="a4", movement_score=50, capability_primary="shift_scheduling"),
    ]
    result = compute_capability_strength_kpis(inputs)
    assert result["cap_weighted_score"].value == pytest.approx(70.0)


def test_cap_strong_move_count_raw():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    inputs = [
        _inp(id="a1", movement_strength="strong"),
        _inp(id="a2", movement_strength="market_shaping"),
        _inp(id="a3", movement_strength="relevant"),
    ]
    result = compute_capability_strength_kpis(inputs)
    assert result["cap_strong_move_count_raw"].value == 2
    assert set(result["cap_strong_move_count_raw"].contributing_ids) == {"a1", "a2"}


def test_cap_market_shaping_ratio_empty_returns_null():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    result = compute_capability_strength_kpis([])
    assert result["cap_market_shaping_ratio"].value is None


# --- activity KPIs ---

def test_act_count_raw():
    from app.scorecard.kpi_engine import compute_activity_kpis
    inputs = [_inp(id="a1"), _inp(id="a2"), _inp(id="a3")]
    result = compute_activity_kpis(inputs)
    assert result["act_count_raw"].value == 3


def test_act_weighted_strength_empty_returns_null():
    from app.scorecard.kpi_engine import compute_activity_kpis
    result = compute_activity_kpis([])
    assert result["act_weighted_strength"].value is None


def test_act_signal_class_diversity_single_class_returns_zero():
    from app.scorecard.kpi_engine import compute_activity_kpis
    inputs = [_inp(id=f"a{i}", signal_class="product_capability_move") for i in range(3)]
    result = compute_activity_kpis(inputs)
    assert result["act_signal_class_diversity"].value == pytest.approx(0.0)


def test_act_signal_class_diversity_all_classes_returns_one():
    from app.scorecard.kpi_engine import compute_activity_kpis
    from app.scorecard.constants import SIGNAL_CLASS_COUNT
    classes = [
        "product_capability_move", "positioning_move", "ecosystem_move",
        "thought_leadership_signal", "hiring_signal", "weak_signal", "market_expansion_move"
    ]
    assert len(classes) == SIGNAL_CLASS_COUNT
    inputs = [_inp(id=f"a{i}", signal_class=c) for i, c in enumerate(classes)]
    result = compute_activity_kpis(inputs)
    assert result["act_signal_class_diversity"].value == pytest.approx(1.0, abs=0.01)


def test_act_diversity_zero_inputs():
    from app.scorecard.kpi_engine import compute_activity_kpis
    result = compute_activity_kpis([])
    assert result["act_signal_class_diversity"].value == pytest.approx(0.0)
