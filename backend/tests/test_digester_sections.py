from app.digester.sections import SECTIONS


def test_sections_has_five_entries():
    assert len(SECTIONS) == 5


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


def test_competitor_news_uses_source_type_filter():
    news = next(s for s in SECTIONS if s.key == "competitor_news")
    assert news.use_source_type_filter is True
    assert news.signal_types == []


def test_events_section_signal_types():
    events = next(s for s in SECTIONS if s.key == "events")
    assert "event_or_thought_leadership" in events.signal_types
