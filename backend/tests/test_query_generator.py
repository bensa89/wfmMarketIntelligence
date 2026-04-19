from unittest.mock import patch
from app.searcher.query_generator import (
    generate_queries_for_company,
    QuerySpec,
    generate_trend_queries,
)


def test_generate_queries_returns_list():
    mock_llm_response = """[
      {"query_text": "Quinyx AI scheduling 2025", "search_intent": "ai_announcement"},
      {"query_text": "Quinyx partnership announcement", "search_intent": "partnership"}
    ]"""

    with patch("app.searcher.query_generator.call_llm", return_value=mock_llm_response):
        queries = generate_queries_for_company(
            company_name="Quinyx",
            company_type="competitor",
            context={
                "target_industries": ["retail", "healthcare"],
                "core_capabilities": ["scheduling", "time tracking"],
                "strategic_priorities": ["AI"],
                "relevant_competitive_areas": ["workforce management"],
            },
        )

    assert len(queries) == 2
    assert queries[0].query_text == "Quinyx AI scheduling 2025"
    assert queries[0].search_intent == "ai_announcement"


def test_generate_queries_returns_empty_on_parse_error():
    with patch("app.searcher.query_generator.call_llm", return_value="invalid json"):
        queries = generate_queries_for_company(
            company_name="Quinyx",
            company_type="competitor",
            context={},
        )
    assert queries == []


def test_generate_trend_queries_returns_list():
    mock_response = """[
      {"query_text": "workforce management AI trends 2025", "search_intent": "market_trend"}
    ]"""

    with patch("app.searcher.query_generator.call_llm", return_value=mock_response):
        queries = generate_trend_queries(
            competitive_areas=["workforce management", "scheduling"]
        )

    assert len(queries) == 1
    assert queries[0].search_intent == "market_trend"
