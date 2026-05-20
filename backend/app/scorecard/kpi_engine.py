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
