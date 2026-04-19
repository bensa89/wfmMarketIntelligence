import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any

from app.analyser.client import call_llm
from app.config import settings


@dataclass
class QuerySpec:
    query_text: str
    search_intent: str


def _parse_query_list(raw: str) -> List[QuerySpec]:
    try:
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not json_match:
            return []
        data = json.loads(json_match.group(0))
        return [
            QuerySpec(
                query_text=str(item.get("query_text", ""))[:500],
                search_intent=str(item.get("search_intent", "general"))[:100],
            )
            for item in data
            if item.get("query_text")
        ]
    except Exception:
        return []


def generate_queries_for_company(
    company_name: str,
    company_type: str,
    context: Dict[str, Any],
) -> List[QuerySpec]:
    n = settings.search_queries_per_company
    industries = ", ".join(context.get("target_industries", []))
    capabilities = ", ".join(context.get("core_capabilities", []))
    priorities = ", ".join(context.get("strategic_priorities", []))
    competitive = ", ".join(context.get("relevant_competitive_areas", []))

    prompt = f"""You are a competitive intelligence analyst. Generate {n} web search queries to find recent news, reports, and mentions about the company "{company_name}" (type: {company_type}).

Our company context:
- Target industries: {industries or "N/A"}
- Core capabilities: {capabilities or "N/A"}
- Strategic priorities: {priorities or "N/A"}
- Competitive areas: {competitive or "N/A"}

Generate queries covering these intents: ai_announcement, product_update, partnership, pricing, hiring, event, analyst_coverage, positioning.

Respond ONLY with a JSON array:
[
  {{"query_text": "short precise search query", "search_intent": "intent_name"}},
  ...
]

No markdown fences, no extra text."""

    raw = call_llm(prompt)
    return _parse_query_list(raw)


def generate_trend_queries(competitive_areas: List[str]) -> List[QuerySpec]:
    areas = (
        ", ".join(competitive_areas) if competitive_areas else "workforce management"
    )
    prompt = f"""Generate 5 web search queries to discover recent market trends, news, and analysis in these areas: {areas}.

Focus on: industry reports, analyst coverage, emerging technologies, regulatory changes, market developments.

Respond ONLY with a JSON array:
[
  {{"query_text": "short precise search query", "search_intent": "market_trend"}},
  ...
]

No markdown fences, no extra text."""

    raw = call_llm(prompt)
    return _parse_query_list(raw)
