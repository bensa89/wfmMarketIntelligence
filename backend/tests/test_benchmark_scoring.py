from datetime import date, timedelta
from types import SimpleNamespace
import pytest

from app.benchmark.period import get_period_bounds
from app.benchmark.scoring import (
    compute_sub_scores,
    compute_relative_strength,
    determine_tier,
    compute_confidence,
    SubScores,
)


# --- Period utility tests ---

def test_get_period_bounds_30d():
    start, end = get_period_bounds("30d")
    assert end == date.today()
    assert start == date.today() - timedelta(days=30)


def test_get_period_bounds_90d():
    start, end = get_period_bounds("90d")
    assert end == date.today()
    assert start == date.today() - timedelta(days=90)


def test_get_period_bounds_180d():
    start, end = get_period_bounds("180d")
    assert end == date.today()
    assert start == date.today() - timedelta(days=180)


def test_get_period_bounds_invalid():
    with pytest.raises(ValueError):
        get_period_bounds("7d")


# --- Scoring tests ---

def _make_assessment(**kwargs) -> SimpleNamespace:
    """Build a minimal SignalAssessment-like object."""
    defaults = dict(
        signal_class="product_capability_move",
        evidence_strength=3,
        visibility_impact="medium",
        movement_score=50,
        movement_strength="relevant",
        confidence=0.7,
        gameplay_tags=[],
        signal_id="sig-1",
        created_at=date.today(),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


TODAY = date.today()
PERIOD_START = TODAY - timedelta(days=30)
PERIOD_END = TODAY


# --- compute_relative_strength ---

def test_relative_strength_all_zeros():
    s = SubScores(capability_depth=0, execution_momentum=0, market_proof=0, strategic_focus=0, evidence_coverage=0)
    assert compute_relative_strength(s) == 0


def test_relative_strength_all_fives():
    s = SubScores(capability_depth=5, execution_momentum=5, market_proof=5, strategic_focus=5, evidence_coverage=5)
    assert compute_relative_strength(s) == 100


def test_relative_strength_weighted():
    # depth=5 only → 5 * 0.35 * 20 = 35
    s = SubScores(capability_depth=5, execution_momentum=0, market_proof=0, strategic_focus=0, evidence_coverage=0)
    assert compute_relative_strength(s) == 35


# --- determine_tier ---

def test_tier_leader():
    assert determine_tier(score=80, confidence=0.9, evidence_coverage=3) == "leader"


def test_tier_strong():
    assert determine_tier(score=60, confidence=0.9, evidence_coverage=3) == "strong"


def test_tier_emerging():
    assert determine_tier(score=40, confidence=0.9, evidence_coverage=3) == "emerging"


def test_tier_weakly_evidenced_by_score():
    assert determine_tier(score=20, confidence=0.9, evidence_coverage=3) == "weakly_evidenced"


def test_tier_confidence_downgrade_leader_to_strong():
    assert determine_tier(score=80, confidence=0.3, evidence_coverage=3) == "strong"


def test_tier_confidence_downgrade_strong_to_emerging():
    assert determine_tier(score=60, confidence=0.3, evidence_coverage=3) == "emerging"


def test_tier_confidence_downgrade_emerging_to_weakly():
    assert determine_tier(score=40, confidence=0.3, evidence_coverage=3) == "weakly_evidenced"


def test_tier_low_evidence_coverage_forces_weakly():
    assert determine_tier(score=90, confidence=0.9, evidence_coverage=1) == "weakly_evidenced"


# --- compute_confidence ---

def test_confidence_no_assessments():
    assert compute_confidence([], evidence_coverage=0) == 0.0


def test_confidence_capped_at_0_3_for_less_than_3_signals():
    a = _make_assessment(confidence=1.0)
    result = compute_confidence([a, a], evidence_coverage=5)
    assert result <= 0.3


def test_confidence_above_threshold_with_many_signals():
    assessments = [_make_assessment(confidence=0.9) for _ in range(8)]
    result = compute_confidence(assessments, evidence_coverage=5)
    assert result > 0.4


# --- compute_sub_scores ---

def test_sub_scores_no_assessments():
    scores = compute_sub_scores(
        cap_assessments=[],
        all_assessments=[],
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        cap_key="demand_forecasting",
    )
    assert scores.capability_depth == 0
    assert scores.execution_momentum == 0
    assert scores.market_proof == 0
    assert scores.strategic_focus == 0
    assert scores.evidence_coverage == 0


def test_sub_scores_product_capability_move_increases_depth():
    a = _make_assessment(signal_class="product_capability_move", evidence_strength=3, movement_strength="strong")
    all_a = [a]
    scores = compute_sub_scores(
        cap_assessments=[a],
        all_assessments=all_a,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        cap_key="demand_forecasting",
    )
    assert scores.capability_depth >= 1


def test_sub_scores_strategic_focus_based_on_share():
    assessments = [_make_assessment(signal_class="product_capability_move") for _ in range(5)]
    scores = compute_sub_scores(
        cap_assessments=assessments,
        all_assessments=assessments,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        cap_key="demand_forecasting",
    )
    assert scores.strategic_focus >= 4
