from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SubScores:
    capability_depth: int = 0
    execution_momentum: int = 0
    market_proof: int = 0
    strategic_focus: int = 0
    evidence_coverage: int = 0


def _bin(value: float, thresholds: list[tuple[float, int]]) -> int:
    """Map a value to an integer bin. thresholds: list of (upper_bound, score) ascending."""
    for upper, score in thresholds:
        if value <= upper:
            return score
    return thresholds[-1][1]


_EXTERNAL_KEYWORDS = {"customer", "reference", "analyst", "partner", "ecosystem", "integration"}


def _has_external_evidence(assessment) -> bool:
    if assessment.visibility_impact == "high":
        return True
    tags = assessment.gameplay_tags or []
    return bool(_EXTERNAL_KEYWORDS.intersection(t.lower() for t in tags))


def compute_sub_scores(
    cap_assessments: list,
    all_assessments: list,
    period_start: date,
    period_end: date,
    cap_key: str,
    weights: list[float] | None = None,
    all_weights: list[float] | None = None,
) -> SubScores:
    if not cap_assessments:
        return SubScores()

    # Use uniform weights=1.0 when not provided (backward compat)
    w = weights if weights is not None else [1.0] * len(cap_assessments)
    aw = all_weights if all_weights is not None else [1.0] * len(all_assessments)

    total_weight = sum(w)
    if total_weight == 0:
        return SubScores()

    # 1. Capability Depth
    raw_depth = 0.0
    for a, wi in zip(cap_assessments, w):
        sc = a.signal_class or ""
        val = 0.0
        if sc == "product_capability_move":
            val += 2.0
        elif sc in ("positioning_move", "ecosystem_move"):
            val += 1.0
        elif sc in ("thought_leadership_signal", "hiring_signal", "weak_signal", "market_expansion_move"):
            val += 0.5
        ev = a.evidence_strength or 0
        val += (ev / 5) * 0.5
        ms = a.movement_strength or ""
        if ms in ("market_shaping", "strong"):
            val += 0.5
        raw_depth += val * wi
    avg_depth = raw_depth / total_weight
    depth_score = _bin(avg_depth, [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])
    depth_score = min(5, depth_score)

    # 2. Execution Momentum
    signal_density = _bin(total_weight, [(0, 0), (1, 1), (3, 2), (6, 3), (10, 4), (float("inf"), 5)])
    weighted_momentum = sum((a.movement_score or 0) * wi for a, wi in zip(cap_assessments, w))
    avg_momentum = (weighted_momentum / total_weight) / 20  # 0-100 → 0-5
    strong_weight = sum(
        wi for a, wi in zip(cap_assessments, w)
        if (a.movement_strength or "") in ("strong", "market_shaping")
    )
    strong_ratio = (strong_weight / total_weight) * 5
    exec_momentum = round((signal_density + avg_momentum + strong_ratio) / 3)
    exec_momentum = min(5, max(0, exec_momentum))

    # 3. Market Proof
    raw_proof = 0.0
    for a, wi in zip(cap_assessments, w):
        sc = a.signal_class or ""
        vi = a.visibility_impact or ""
        val = 0.0
        if sc == "ecosystem_move":
            val += 1.5
        elif sc == "product_capability_move" and _has_external_evidence(a):
            val += 1.0
        else:
            val += 0.5
        if vi == "high":
            val += 1.0
        elif vi == "medium":
            val += 0.5
        tags = a.gameplay_tags or []
        if _EXTERNAL_KEYWORDS.intersection(t.lower() for t in tags):
            val += 0.5
        raw_proof += val * wi
    avg_proof = raw_proof / total_weight
    proof_score = _bin(avg_proof, [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])
    proof_score = min(5, proof_score)

    # 4. Strategic Focus
    all_total_weight = sum(aw)
    share = total_weight / all_total_weight if all_total_weight > 0 else 0
    base_focus = _bin(
        share,
        [(0.05, 0), (0.10, 1), (0.15, 2), (0.20, 3), (0.30, 4), (1.0, 5)],
    )
    weighted_positioning = sum(
        wi for a, wi in zip(cap_assessments, w)
        if (a.signal_class or "") == "positioning_move"
    )
    messaging_bonus = min(1, weighted_positioning / (3 * (total_weight / max(len(cap_assessments), 1))))
    focus_score = min(5, int(base_focus + messaging_bonus))

    # 5. Evidence Coverage
    # Freshness is intentionally excluded: exponential decay already penalises old
    # assessments in every weighted computation above.
    distinct_docs = len({getattr(a, "signal_id", i) for i, a in enumerate(cap_assessments)})
    source_diversity = _bin(distinct_docs, [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (float("inf"), 5)])

    weighted_conf = sum((a.confidence or 0.0) * wi for a, wi in zip(cap_assessments, w))
    avg_conf_score = round((weighted_conf / total_weight) * 5)

    evidence_coverage = round((source_diversity + avg_conf_score) / 2)

    return SubScores(
        capability_depth=depth_score,
        execution_momentum=exec_momentum,
        market_proof=proof_score,
        strategic_focus=focus_score,
        evidence_coverage=evidence_coverage,
    )


def compute_relative_strength(scores: SubScores) -> int:
    raw = (
        scores.capability_depth * 0.35
        + scores.execution_momentum * 0.25
        + scores.market_proof * 0.20
        + scores.strategic_focus * 0.10
        + scores.evidence_coverage * 0.10
    )
    return round(raw * (100 / 5))


def determine_tier(score: int, confidence: float, evidence_coverage: int) -> str:
    if evidence_coverage < 2:
        return "weakly_evidenced"
    if score >= 75:
        tier = "leader"
    elif score >= 55:
        tier = "strong"
    elif score >= 30:
        tier = "emerging"
    else:
        tier = "weakly_evidenced"
    if confidence < 0.4:
        if tier == "leader":
            tier = "strong"
        elif tier == "strong":
            tier = "emerging"
        elif tier == "emerging":
            tier = "weakly_evidenced"
    return tier


def compute_confidence(cap_assessments: list, evidence_coverage: int, weights: list[float] | None = None) -> float:
    count = len(cap_assessments)
    if count == 0:
        return 0.0
    w = weights if weights is not None else [1.0] * count
    total_weight = sum(w)
    weighted_conf = sum((a.confidence or 0.0) * wi for a, wi in zip(cap_assessments, w))
    avg_confidence = weighted_conf / total_weight if total_weight > 0 else 0.0
    # Use raw count (not weighted sum) for the low-signal penalty so that old but
    # numerous assessments are not incorrectly capped.
    raw = (min(count, 8) / 8) * 0.5 + (evidence_coverage / 5) * 0.3 + avg_confidence * 0.2
    confidence = min(1.0, raw)
    if count < 3:
        confidence = min(confidence, 0.3)
    return round(confidence, 2)
