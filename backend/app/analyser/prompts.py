from typing import Dict, Any


def build_analysis_prompt(markdown: str, context: Dict[str, Any]) -> str:
    ctx_str = f"""
Company: {context.get("company_name", "N/A")}
Description: {context.get("short_description", "N/A")}
Target Industries: {", ".join(context.get("target_industries", []))}
Target Segments: {", ".join(context.get("target_segments", []))}
Core Capabilities: {", ".join(context.get("core_capabilities", []))}
Strategic Priorities: {", ".join(context.get("strategic_priorities", []))}
Differentiators: {", ".join(context.get("differentiators", []))}
Relevant Competitive Areas: {", ".join(context.get("relevant_competitive_areas", []))}
Non-Focus Areas: {", ".join(context.get("non_focus_areas", []))}
""".strip()

    return f"""You are a market intelligence analyst for the following company:

{ctx_str}

Analyze the following competitor/market content and extract a structured signal.

CONTENT:
{markdown[:4000]}

Also consider recency: more recent developments should receive a higher relevance_score than older, stale information.

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "title": "short descriptive title (max 100 chars)",
  "signal_type": one of: product_update | ai_announcement | partnership | positioning_change | target_market_change | event_or_thought_leadership | hiring_signal | other,
  "topic": "main topic or theme (max 60 chars)",
  "summary": "2-3 sentence factual summary of the content",
  "why_it_matters": "1-2 sentences explaining strategic relevance to our company specifically",
  "relevance_score": float between 0.0 (irrelevant) and 1.0 (highly relevant to us),
  "confidence_score": float between 0.0 (uncertain) and 1.0 (very confident in analysis),
  "published_at": "ISO-8601 date string of when the content was originally published, or null if unknown"
}}

No markdown fences, no extra text. Only the JSON object."""
