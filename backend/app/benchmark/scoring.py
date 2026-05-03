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
) -> SubScores:
    if not cap_assessments:
        return SubScores()

    count = len(cap_assessments)

    # 1. Capability Depth
    raw_depth = 0.0
    for a in cap_assessments:
        sc = a.signal_class or ""
        if sc == "product_capability_move":
            raw_depth += 2.0
        elif sc in ("positioning_move", "ecosystem_move"):
            raw_depth += 1.0
        elif sc in ("thought_leadership_signal", "hiring_signal", "weak_signal", "market_expansion_move"):
            raw_depth += 0.5
        ev = a.evidence_strength or 0
        raw_depth += (ev / 5) * 0.5
        ms = a.movement_strength or ""
        if ms in ("market_shaping", "strong"):
            raw_depth += 0.5
    avg_depth = raw_depth / count
    depth_score = _bin(avg_depth, [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])
    depth_score = min(5, depth_score)

    # 2. Execution Momentum
    signal_density = _bin(count, [(0, 0), (1, 1), (3, 2), (6, 3), (10, 4), (float("inf"), 5)])
    movements = [a.movement_score or 0 for a in cap_assessments]
    avg_momentum = (sum(movements) / count) / 20  # 0-100 → 0-5
    strong_count = sum(
        1 for a in cap_assessments
        if (a.movement_strength or "") in ("strong", "market_shaping")
    )
    strong_ratio = (strong_count / count) * 5
    exec_momentum = round((signal_density + avg_momentum + strong_ratio) / 3)
    exec_momentum = min(5, max(0, exec_momentum))

    # 3. Market Proof
    raw_proof = 0.0
    for a in cap_assessments:
        sc = a.signal_class or ""
        vi = a.visibility_impact or ""
        if sc == "ecosystem_move":
            raw_proof += 1.5
        elif sc == "product_capability_move" and _has_external_evidence(a):
            raw_proof += 1.0
        else:
            raw_proof += 0.5
        if vi == "high":
            raw_proof += 1.0
        elif vi == "medium":
            raw_proof += 0.5
        tags = a.gameplay_tags or []
        if _EXTERNAL_KEYWORDS.intersection(t.lower() for t in tags):
            raw_proof += 0.5
    avg_proof = raw_proof / count
    proof_score = _bin(avg_proof, [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])
    proof_score = min(5, proof_score)

    # 4. Strategic Focus
    total = len(all_assessments)
    share = count / total if total > 0 else 0
    base_focus = _bin(
        share,
        [(0.05, 0), (0.10, 1), (0.15, 2), (0.20, 3), (0.30, 4), (1.0, 5)],
    )
    positioning_count = sum(
        1 for a in cap_assessments if (a.signal_class or "") == "positioning_move"
    )
    messaging_bonus = min(1, positioning_count / 3)
    focus_score = min(5, int(base_focus + messaging_bonus))

    # 5. Evidence Coverage
    distinct_docs = len({getattr(a, "signal_id", i) for i, a in enumerate(cap_assessments)})
    source_diversity = _bin(distinct_docs, [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (float("inf"), 5)])

    confidences = [a.confidence or 0.0 for a in cap_assessments]
    avg_conf_score = round((sum(confidences) / count) * 5)

    fresh_cutoff = period_end - timedelta(days=30)
    fresh_count = 0
    for a in cap_assessments:
        created = a.created_at
        if hasattr(created, "date"):
            created = created.date()
        if created >= fresh_cutoff:
            fresh_count += 1
    freshness_ratio = fresh_count / count
    freshness = _bin(freshness_ratio, [(0, 0), (0.25, 1), (0.50, 2), (0.75, 3), (0.90, 4), (1.0, 5)])

    evidence_coverage = min(source_diversity, avg_conf_score, freshness)

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


def compute_confidence(cap_assessments: list, evidence_coverage: int) -> float:
    count = len(cap_assessments)
    if count == 0:
        return 0.0
    avg_confidence = sum(a.confidence or 0.0 for a in cap_assessments) / count
    raw = (count / 8) * 0.5 + (evidence_coverage / 5) * 0.3 + avg_confidence * 0.2
    confidence = min(1.0, raw)
    if count < 3:
        confidence = min(confidence, 0.3)
    return round(confidence, 2)
