from app.digester.sections import SECTIONS


def test_sections_has_four_entries():
    assert len(SECTIONS) == 4


def test_section_keys_are_unique():
    keys = [s.key for s in SECTIONS]
    assert len(keys) == len(set(keys))


def test_all_sections_have_required_fields():
    for s in SECTIONS:
        assert s.key
        assert s.title
        assert isinstance(s.signal_types, list)
        assert isinstance(s.assessment_classes, list)
        assert isinstance(s.use_source_type_filter, bool)


def test_competitors_section_uses_source_type_filter_and_is_competitor_only():
    competitors = next(s for s in SECTIONS if s.key == "competitors")
    assert competitors.use_source_type_filter is True
    assert competitors.competitor_only is True
    assert competitors.signal_types == ["product_update", "partnership", "hiring_signal"]


def test_events_section_signal_types():
    events = next(s for s in SECTIONS if s.key == "events")
    assert "event_or_thought_leadership" in events.signal_types
