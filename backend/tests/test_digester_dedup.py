import pytest
from unittest.mock import MagicMock
from app.digester.dedup import get_prev_signal_index, should_include


def make_signal(signal_id: str, movement_strength: str | None = None) -> MagicMock:
    signal = MagicMock()
    signal.id = signal_id
    if movement_strength:
        assessment = MagicMock()
        assessment.movement_strength = MagicMock()
        assessment.movement_strength.value = movement_strength
        signal.assessment = assessment
    else:
        signal.assessment = None
    return signal


def test_get_prev_signal_index_empty():
    assert get_prev_signal_index([]) == {}


def test_get_prev_signal_index_builds_lookup():
    prev = [
        {"key": "events", "items": [{"signal_id": "abc", "movement_strength": "relevant"}]},
        {"key": "new_trends", "items": [{"signal_id": "xyz", "movement_strength": "strong"}]},
    ]
    index = get_prev_signal_index(prev)
    assert index["abc"]["movement_strength"] == "relevant"
    assert index["xyz"]["movement_strength"] == "strong"


def test_should_include_new_signal():
    signal = make_signal("new-id", "relevant")
    assert should_include(signal, {}) is True


def test_should_include_same_strength_excluded():
    signal = make_signal("existing-id", "relevant")
    index = {"existing-id": {"movement_strength": "relevant"}}
    assert should_include(signal, index) is False


def test_should_include_improved_strength():
    signal = make_signal("existing-id", "strong")
    index = {"existing-id": {"movement_strength": "relevant"}}
    assert should_include(signal, index) is True


def test_should_include_degraded_strength_excluded():
    signal = make_signal("existing-id", "weak")
    index = {"existing-id": {"movement_strength": "strong"}}
    assert should_include(signal, index) is False


def test_should_include_no_assessment_excluded_if_in_prev():
    signal = make_signal("existing-id", movement_strength=None)
    index = {"existing-id": {"movement_strength": "relevant"}}
    assert should_include(signal, index) is False


def test_should_include_market_shaping_beats_strong():
    signal = make_signal("existing-id", "market_shaping")
    index = {"existing-id": {"movement_strength": "strong"}}
    assert should_include(signal, index) is True
