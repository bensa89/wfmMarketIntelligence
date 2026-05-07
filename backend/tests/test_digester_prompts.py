from app.digester.prompts import (
    build_section_curation_prompt,
    build_intro_summary_prompt,
)


CANDIDATES = [
    {
        "signal_id": "abc123",
        "company": "Acme",
        "title": "Acme launches AI Scheduler",
        "assessment_summary": "Acme has released an AI scheduling product.",
        "implication_for_us": "Increases competitive pressure in core scheduling.",
        "strategic_intent_guess": "Capturing enterprise WFM market.",
        "movement_strength": "strong",
    }
]


def test_section_curation_prompt_contains_signal_id():
    prompt = build_section_curation_prompt(
        "Wettbewerber-Aktivitäten", CANDIDATES, [], "WFM company"
    )
    assert "abc123" in prompt


def test_section_curation_prompt_contains_company():
    prompt = build_section_curation_prompt(
        "Wettbewerber-Aktivitäten", CANDIDATES, [], "WFM company"
    )
    assert "Acme" in prompt


def test_section_curation_prompt_contains_section_title():
    prompt = build_section_curation_prompt(
        "Wettbewerber-Aktivitäten", CANDIDATES, [], "WFM company"
    )
    assert "Wettbewerber-Aktivitäten" in prompt


def test_section_curation_prompt_contains_json_key():
    prompt = build_section_curation_prompt(
        "Wettbewerber-Aktivitäten", CANDIDATES, [], "WFM company"
    )
    assert "selected_items" in prompt


def test_section_curation_prompt_includes_prev_items():
    prev = [{"title": "Old signal"}]
    prompt = build_section_curation_prompt(
        "Wettbewerber-Aktivitäten", CANDIDATES, prev, "WFM company"
    )
    assert "Old signal" in prompt


def test_intro_summary_prompt_contains_section_title():
    sections = [
        {"title": "Events", "items": [{"title": "BigConf 2026", "company": "Acme"}]}
    ]
    prompt = build_intro_summary_prompt(sections)
    assert "Events" in prompt
    assert "BigConf 2026" in prompt


def test_intro_summary_prompt_requests_summary_key():
    sections = [
        {"title": "Events", "items": [{"title": "BigConf 2026", "company": "Acme"}]}
    ]
    prompt = build_intro_summary_prompt(sections)
    assert '"summary"' in prompt
