import pytest
from types import SimpleNamespace


def _a(**kwargs):
    """Build a minimal assessment-like object for routing tests."""
    defaults = dict(
        signal_class="product_capability_move",
        evidence_strength=3,
        visibility_impact="medium",
        movement_strength="relevant",
        capability_primary="shift_scheduling",
        assessment_weight=1.0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_product_capability_move_routes_to_capability_and_market():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="product_capability_move"))
    assert "capability_strength" in result.dimension_targets
    assert "market_impact" in result.dimension_targets
    assert result.dimension_targets["capability_strength"] == 1.0
    assert "cap_weighted_score" in result.kpi_targets
    assert "mkt_move_quality" in result.kpi_targets


def test_hiring_signal_routes_to_activity_and_momentum_with_correct_modifiers():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="hiring_signal"))
    assert result.dimension_targets.get("activity") == pytest.approx(0.6)
    assert result.dimension_targets.get("momentum") == pytest.approx(1.0)
    assert "capability_strength" not in result.dimension_targets
    assert "act_count_raw" in result.kpi_targets
    assert "mom_hiring_velocity" in result.kpi_targets


def test_hiring_overrides_base_activity_weight():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="hiring_signal"))
    # Must be 0.6, not 1.0 (base) + 0.6 stacked
    assert result.dimension_targets["activity"] == pytest.approx(0.6)


def test_market_expansion_without_strong_evidence_no_capability():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="market_expansion_move", evidence_strength=3))
    assert "capability_strength" not in result.dimension_targets
    assert "market_impact" in result.dimension_targets


def test_market_expansion_with_strong_evidence_adds_capability_at_reduced_weight():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="market_expansion_move", evidence_strength=4))
    assert result.dimension_targets.get("capability_strength") == pytest.approx(0.7)
    assert "market_impact" in result.dimension_targets


def test_thought_leadership_strict_conditions_adds_market_impact():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(
        signal_class="thought_leadership_signal",
        visibility_impact="high",
        movement_strength="strong",
    ))
    assert result.dimension_targets.get("market_impact") == pytest.approx(0.4)
    assert result.dimension_targets.get("activity") == pytest.approx(0.5)


def test_thought_leadership_default_activity_only():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(
        signal_class="thought_leadership_signal",
        visibility_impact="medium",
        movement_strength="relevant",
    ))
    assert "market_impact" not in result.dimension_targets
    assert result.dimension_targets.get("activity") == pytest.approx(0.5)


def test_high_visibility_adds_market_impact_kpis():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(
        signal_class="ecosystem_move", visibility_impact="high"
    ))
    assert "mkt_high_visibility_count_raw" in result.kpi_targets


def test_routing_version_is_set():
    from app.scorecard.dimension_router import DimensionRouter
    from app.scorecard.constants import ROUTING_VERSION
    result = DimensionRouter.route(_a())
    assert result.routing_version == ROUTING_VERSION


def test_strong_movement_adds_strong_count_kpis():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(movement_strength="strong"))
    assert "act_strong_count_raw" in result.kpi_targets
    assert "act_strong_count_weighted" in result.kpi_targets
