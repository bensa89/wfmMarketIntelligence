from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
from app.scorecard.constants import (
    RECENCY_DECAY_MAX, SIGNAL_CLASS_COUNT,
    MOMENTUM_RISING_THRESHOLD, MOMENTUM_DECLINING_THRESHOLD,
)


@dataclass
class AssessmentKPIInput:
    id: str
    movement_score: int
    movement_strength: str
    signal_class: str
    evidence_strength: int
    visibility_impact: str
    confidence: float
    capability_primary: str
    capability_secondary: list[str]
    assessment_weight: float
    dimension_modifier: float
    age_days: int
    period_days: int

    @property
    def effective_weight(self) -> float:
        recency = 1.0 - (self.age_days / max(self.period_days, 1)) * RECENCY_DECAY_MAX
        return self.assessment_weight * self.dimension_modifier * recency


@dataclass
class KPIValue:
    value: Optional[float]
    contributing_ids: list[str] = field(default_factory=list)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def compute_capability_strength_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    if not inputs:
        return {
            "cap_weighted_score": KPIValue(None),
            "cap_strong_move_count_raw": KPIValue(0),
            "cap_strong_move_count_weighted": KPIValue(0.0),
            "cap_market_shaping_ratio": KPIValue(None),
        }

    # Per-capability weighted score
    cap_num: dict[str, float] = defaultdict(float)
    cap_den: dict[str, float] = defaultdict(float)
    cap_ids: dict[str, list[str]] = defaultdict(list)
    for a in inputs:
        ev_w = a.evidence_strength / 3.0
        w = a.effective_weight * ev_w
        cap_num[a.capability_primary] += a.movement_score * w
        cap_den[a.capability_primary] += w
        cap_ids[a.capability_primary].append(a.id)

    cap_scores = {cap: cap_num[cap] / cap_den[cap] for cap in cap_num if cap_den[cap] > 0}
    all_ids = [a.id for a in inputs]
    overall = _clamp(sum(cap_scores.values()) / len(cap_scores)) if cap_scores else None

    strong = [a for a in inputs if a.movement_strength in ("strong", "market_shaping")]
    ms_ids = [a.id for a in inputs if a.movement_strength == "market_shaping"]
    total_ew = sum(a.effective_weight for a in inputs)
    ms_ew = sum(a.effective_weight for a in inputs if a.movement_strength == "market_shaping")
    shaping_ratio = _clamp(ms_ew / total_ew, 0.0, 1.0) if total_ew > 0 else None

    return {
        "cap_weighted_score": KPIValue(overall, all_ids),
        "cap_strong_move_count_raw": KPIValue(len(strong), [a.id for a in strong]),
        "cap_strong_move_count_weighted": KPIValue(
            sum(a.effective_weight for a in strong), [a.id for a in strong]
        ),
        "cap_market_shaping_ratio": KPIValue(shaping_ratio, ms_ids),
    }


def compute_activity_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    all_ids = [a.id for a in inputs]
    if not inputs:
        return {
            "act_count_raw": KPIValue(0),
            "act_count_weighted": KPIValue(0.0),
            "act_strong_count_raw": KPIValue(0),
            "act_strong_count_weighted": KPIValue(0.0),
            "act_weighted_strength": KPIValue(None),
            "act_signal_class_diversity": KPIValue(0.0),
        }

    strong = [a for a in inputs if a.movement_strength in ("strong", "market_shaping")]
    total_ew = sum(a.effective_weight for a in inputs)
    wt_strength = _clamp(sum(a.movement_score * a.effective_weight for a in inputs) / total_ew) if total_ew > 0 else None

    # Shannon entropy normalised to [0, 1] over SIGNAL_CLASS_COUNT classes
    class_weights: dict[str, float] = defaultdict(float)
    for a in inputs:
        class_weights[a.signal_class] += a.effective_weight
    total_w = sum(class_weights.values())
    diversity = 0.0
    if total_w > 0 and SIGNAL_CLASS_COUNT > 1:
        entropy = -sum(
            (w / total_w) * math.log(w / total_w)
            for w in class_weights.values() if w > 0
        )
        diversity = _clamp(entropy / math.log(SIGNAL_CLASS_COUNT), 0.0, 1.0)

    return {
        "act_count_raw": KPIValue(len(inputs), all_ids),
        "act_count_weighted": KPIValue(sum(a.effective_weight for a in inputs), all_ids),
        "act_strong_count_raw": KPIValue(len(strong), [a.id for a in strong]),
        "act_strong_count_weighted": KPIValue(
            sum(a.effective_weight for a in strong), [a.id for a in strong]
        ),
        "act_weighted_strength": KPIValue(wt_strength, all_ids),
        "act_signal_class_diversity": KPIValue(diversity, all_ids),
    }


_VIS_WEIGHTS = {"low": 0.3, "medium": 0.7, "high": 1.0}
_STRATEGIC_CLASSES = {"product_capability_move", "market_expansion_move", "ecosystem_move", "positioning_move"}
_CUSTOMER_CLASSES = {"ecosystem_move", "positioning_move"}
_QUALITY_CLASSES = {"product_capability_move", "market_expansion_move", "ecosystem_move"}


def compute_market_impact_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    high = [a for a in inputs if a.visibility_impact == "high"]
    qualify = [a for a in inputs if a.signal_class in _QUALITY_CLASSES]
    strategic = [a for a in inputs if a.signal_class in _STRATEGIC_CLASSES]

    def weighted_mean_score(subset: list[AssessmentKPIInput], weight_fn=None) -> Optional[float]:
        if not subset:
            return None
        num = sum((weight_fn(a) if weight_fn else 1.0) * a.movement_score * a.effective_weight for a in subset)
        den = sum((weight_fn(a) if weight_fn else 1.0) * a.effective_weight for a in subset)
        return _clamp(num / den) if den > 0 else None

    vis_score = weighted_mean_score(inputs, lambda a: _VIS_WEIGHTS.get(a.visibility_impact, 0.3)) if inputs else None

    strat_num = sum(a.evidence_strength * a.confidence * a.effective_weight for a in strategic)
    strat_den = sum(a.effective_weight for a in strategic)
    strat_q = _clamp((strat_num / strat_den) * 20) if strat_den > 0 else None

    return {
        "mkt_high_visibility_count_raw": KPIValue(len(high), [a.id for a in high]),
        "mkt_high_visibility_count_weighted": KPIValue(
            sum(a.effective_weight for a in high), [a.id for a in high]
        ),
        "mkt_weighted_visibility": KPIValue(vis_score, [a.id for a in inputs]),
        "mkt_move_quality": KPIValue(
            weighted_mean_score(qualify), [a.id for a in qualify]
        ),
        "mkt_strategic_quality": KPIValue(strat_q, [a.id for a in strategic]),
    }


def compute_customer_proof_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    ecosystem = [a for a in inputs if a.signal_class in _CUSTOMER_CLASSES]
    high_ev = [a for a in inputs if a.evidence_strength >= 4]
    total_ew = sum(a.effective_weight for a in inputs)
    high_ew = sum(a.effective_weight for a in high_ev)
    high_ratio = _clamp(high_ew / total_ew, 0.0, 1.0) if total_ew > 0 else None

    ev_num = sum(a.evidence_strength * a.confidence * a.effective_weight for a in ecosystem)
    ev_den = sum(a.effective_weight for a in ecosystem)
    weighted_ev = _clamp((ev_num / ev_den) * 20) if ev_den > 0 else None

    validation = None
    if weighted_ev is not None and high_ratio is not None:
        validation = _clamp(weighted_ev * 0.6 + high_ratio * 100 * 0.4)

    return {
        "cp_ecosystem_count_raw": KPIValue(len(ecosystem), [a.id for a in ecosystem]),
        "cp_ecosystem_count_weighted": KPIValue(
            sum(a.effective_weight for a in ecosystem), [a.id for a in ecosystem]
        ),
        "cp_weighted_evidence": KPIValue(weighted_ev, [a.id for a in ecosystem]),
        "cp_high_evidence_ratio": KPIValue(high_ratio, [a.id for a in high_ev]),
        "cp_validation_score": KPIValue(validation, [a.id for a in inputs]),
    }


def compute_momentum_kpis(
    current: list[AssessmentKPIInput],
    prior: list[AssessmentKPIInput],
) -> dict[str, KPIValue]:
    def _wt_strength(lst: list[AssessmentKPIInput]) -> Optional[float]:
        ew = sum(a.effective_weight for a in lst)
        if ew <= 0:
            return None
        return _clamp(sum(a.movement_score * a.effective_weight for a in lst) / ew)

    def _strong_ew(lst: list[AssessmentKPIInput]) -> float:
        return sum(a.effective_weight for a in lst if a.movement_strength in ("strong", "market_shaping"))

    cur_str = _wt_strength(current)
    pri_str = _wt_strength(prior)
    delta = _clamp(cur_str - pri_str, -100.0, 100.0) if (cur_str is not None and pri_str is not None) else None
    accel = _strong_ew(current) - _strong_ew(prior) if prior else None
    hiring = [a for a in current if a.signal_class == "hiring_signal"]
    hiring_vel = sum(a.effective_weight for a in hiring) if hiring else None

    trend = None
    if delta is not None:
        if delta > MOMENTUM_RISING_THRESHOLD:
            trend = "rising"
        elif delta < MOMENTUM_DECLINING_THRESHOLD:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "mom_period_delta": KPIValue(delta, [a.id for a in current]),
        "mom_strong_move_acceleration": KPIValue(accel, [a.id for a in current]),
        "mom_hiring_velocity": KPIValue(hiring_vel, [a.id for a in hiring]),
        "mom_trend": KPIValue(trend, [a.id for a in current]),
    }


_DIMENSION_PRIMARY_KPI = {
    "capability_strength": "cap_weighted_score",
    "activity": "act_weighted_strength",
    "market_impact": "mkt_weighted_visibility",
    "customer_proof": "cp_validation_score",
    "momentum": "mom_period_delta",
}


def compute_dimension_score(dimension_key: str, kpis: dict) -> Optional[float]:
    primary = _DIMENSION_PRIMARY_KPI.get(dimension_key)
    if primary is None:
        return None
    kpi = kpis.get(primary)
    if kpi is None:
        return None
    raw = kpi["value"] if isinstance(kpi, dict) else kpi.value
    if raw is None:
        return None
    if dimension_key == "momentum":
        return _clamp(50.0 + raw / 2.0)
    return _clamp(raw)
