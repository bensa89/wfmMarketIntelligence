from app.models.signal import SignalType

_VISIBILITY_WEIGHTS = {"low": 0, "medium": 8, "high": 15}
_SIGNAL_TYPE_CLASS_MAP = {
    SignalType.product_update: "product_capability_move",
    SignalType.ai_announcement: "product_capability_move",
    SignalType.partnership: "ecosystem_move",
    SignalType.positioning_change: "positioning_move",
    SignalType.target_market_change: "positioning_move",
    SignalType.event_or_thought_leadership: "thought_leadership_signal",
    SignalType.hiring_signal: "hiring_signal",
    SignalType.other: "weak_signal",
}


def compute_movement_score(
    relevance_score: float,
    confidence_score: float,
    evidence_strength: int,
    visibility_impact: str,
    signal_class: str,
) -> int:
    score = (
        relevance_score * 35
        + confidence_score * 20
        + evidence_strength * 6
        + _VISIBILITY_WEIGHTS.get(visibility_impact, 0)
        - (10 if signal_class == "thought_leadership_signal" else 0)
    )
    return max(0, min(100, round(score)))


def compute_movement_strength(movement_score: int) -> str:
    if movement_score >= 80:
        return "market_shaping"
    if movement_score >= 60:
        return "strong"
    if movement_score >= 30:
        return "relevant"
    return "weak"


def map_signal_type_to_class(signal_type: SignalType) -> str:
    return _SIGNAL_TYPE_CLASS_MAP.get(signal_type, "weak_signal")
