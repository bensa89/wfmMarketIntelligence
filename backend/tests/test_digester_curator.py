import json
import pytest
from unittest.mock import patch
from app.digester.curator import curate_section, generate_intro_summary

CANDIDATES = [
    {
        "signal_id": "abc123",
        "company": "Acme",
        "title": "Acme AI Scheduler",
        "assessment_summary": "Major product launch.",
        "implication_for_us": "Direct competition with our core product.",
        "strategic_intent_guess": "Market expansion.",
        "movement_strength": "strong",
        "source_url": "https://acme.com/blog/ai",
        "source_domain": "acme.com",
        "source_title": "Acme Blog",
    }
]

VALID_LLM_RESPONSE = json.dumps(
    {
        "selected_items": [
            {
                "signal_id": "abc123",
                "narrative": "Acme has launched an AI-powered scheduler.",
                "implication_for_us": "We must accelerate our own AI roadmap.",
            }
        ]
    }
)


def test_curate_section_returns_enriched_items():
    with patch("app.digester.curator.call_llm", return_value=VALID_LLM_RESPONSE):
        items = curate_section(
            "Wettbewerber-Aktivitäten", CANDIDATES, [], "WFM company"
        )
    assert len(items) == 1
    item = items[0]
    assert item["signal_id"] == "abc123"
    assert item["company"] == "Acme"
    assert item["title"] == "Acme AI Scheduler"
    assert item["narrative"] == "Acme has launched an AI-powered scheduler."
    assert item["source_domain"] == "acme.com"
    assert item["source_title"] == "Acme Blog"
    assert item["movement_strength"] == "strong"


def test_curate_section_empty_candidates_returns_empty():
    with patch("app.digester.curator.call_llm") as mock_llm:
        items = curate_section("Events", [], [], "WFM company")
    mock_llm.assert_not_called()
    assert items == []


def test_curate_section_invalid_json_returns_empty():
    with patch("app.digester.curator.call_llm", return_value="not json"):
        items = curate_section("Events", CANDIDATES, [], "WFM company")
    assert items == []


def test_curate_section_unknown_signal_id_skipped():
    bad_response = json.dumps(
        {
            "selected_items": [
                {"signal_id": "unknown-id", "narrative": "x", "implication_for_us": "y"}
            ]
        }
    )
    with patch("app.digester.curator.call_llm", return_value=bad_response):
        items = curate_section("Events", CANDIDATES, [], "WFM company")
    assert items == []


def test_generate_intro_summary_returns_string():
    sections = [{"title": "Events", "items": [{"title": "BigConf", "company": "Acme"}]}]
    llm_response = json.dumps(
        {"summary": "This week saw a major conference announcement."}
    )
    with patch("app.digester.curator.call_llm", return_value=llm_response):
        result = generate_intro_summary(sections)
    assert result == "This week saw a major conference announcement."


def test_generate_intro_summary_invalid_json_returns_empty():
    sections = [{"title": "Events", "items": [{"title": "BigConf", "company": "Acme"}]}]
    with patch("app.digester.curator.call_llm", return_value="bad json"):
        result = generate_intro_summary(sections)
    assert result == ""
