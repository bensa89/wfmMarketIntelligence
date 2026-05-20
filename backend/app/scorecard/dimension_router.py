from dataclasses import dataclass, field
from app.scorecard.constants import ROUTING_VERSION


@dataclass
class RoutingResult:
    dimension_targets: dict[str, float]   # {dimension_key: dimension_modifier}
    kpi_targets: list[str]
    assessment_weight: float
    routing_version: str


class DimensionRouter:
    @staticmethod
    def route(assessment) -> RoutingResult:
        sc = assessment.signal_class if isinstance(assessment.signal_class, str) else assessment.signal_class.value
        vi = assessment.visibility_impact if isinstance(assessment.visibility_impact, str) else assessment.visibility_impact.value
        ms = assessment.movement_strength if isinstance(assessment.movement_strength, str) else assessment.movement_strength.value
        es = assessment.evidence_strength or 0

        dims: dict[str, float] = {}
        kpis: set[str] = set()

        def add(dimension: str, modifier: float, new_kpis: list[str]):
            # Specific rules override base weight for the same dimension
            if dimension not in dims or modifier != 1.0:
                dims[dimension] = modifier
            kpis.update(new_kpis)

        # Base rule: all assessments contribute to activity
        base_activity_weight = 1.0
        if sc == "hiring_signal":
            base_activity_weight = 0.6
        elif sc == "thought_leadership_signal":
            base_activity_weight = 0.5
        add("activity", base_activity_weight, ["act_count_raw", "act_count_weighted", "act_weighted_strength"])

        # Strong/market_shaping adds strong count KPIs
        if ms in ("strong", "market_shaping"):
            kpis.update(["act_strong_count_raw", "act_strong_count_weighted"])

        # Signal-class specific rules
        if sc == "product_capability_move":
            add("capability_strength", 1.0, ["cap_weighted_score"])
            add("market_impact", 1.0, ["mkt_move_quality"])

        elif sc == "market_expansion_move":
            add("market_impact", 1.0, ["mkt_weighted_visibility", "mkt_strategic_quality"])
            if es >= 4:
                add("capability_strength", 0.7, ["cap_weighted_score"])

        elif sc in ("ecosystem_move", "positioning_move"):
            add("market_impact", 1.0, ["mkt_strategic_quality"])
            add("customer_proof", 1.0, ["cp_ecosystem_count_raw", "cp_ecosystem_count_weighted"])
            if sc == "ecosystem_move" and es >= 4:
                kpis.add("cp_weighted_evidence")

        elif sc == "hiring_signal":
            add("momentum", 1.0, ["mom_hiring_velocity"])

        elif sc == "thought_leadership_signal":
            if vi == "high" and ms in ("strong", "market_shaping"):
                add("market_impact", 0.4, ["mkt_weighted_visibility"])

        # High visibility adds market impact KPIs regardless of signal class
        if vi == "high":
            if "market_impact" not in dims:
                dims["market_impact"] = 1.0
            kpis.update(["mkt_high_visibility_count_raw", "mkt_high_visibility_count_weighted", "mkt_weighted_visibility"])

        return RoutingResult(
            dimension_targets=dims,
            kpi_targets=sorted(kpis),
            assessment_weight=getattr(assessment, "assessment_weight", None) or 1.0,
            routing_version=ROUTING_VERSION,
        )
