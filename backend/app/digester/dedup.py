from app.models.signal import Signal

STRENGTH_ORDER: dict[str, int] = {
    "weak": 0,
    "relevant": 1,
    "strong": 2,
    "market_shaping": 3,
}


def get_prev_signal_index(prev_sections: list[dict]) -> dict[str, dict]:
    """Returns {signal_id: item_dict} for all items in previous digest sections."""
    index: dict[str, dict] = {}
    for section in prev_sections or []:
        for item in section.get("items", []):
            sid = item.get("signal_id")
            if sid:
                index[sid] = item
    return index


def should_include(signal: Signal, prev_index: dict[str, dict]) -> bool:
    """True if signal is new OR has improved movement_strength since last digest."""
    if signal.id not in prev_index:
        return True

    prev_item = prev_index[signal.id]
    prev_strength = prev_item.get("movement_strength")
    curr_strength = (
        signal.assessment.movement_strength.value
        if signal.assessment and signal.assessment.movement_strength
        else None
    )

    if not curr_strength or not prev_strength:
        return False

    return STRENGTH_ORDER.get(curr_strength, 0) > STRENGTH_ORDER.get(prev_strength, 0)
