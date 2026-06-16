from typing import Dict, Any, Optional


def build_analysis_prompt(markdown: str, context: Dict[str, Any], external_view: Optional[Dict[str, Any]] = None) -> str:
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

    external_view_str = ""
    if external_view:
        external_view_str = f"""
Our External Presence (how we appear publicly, derived from our own website):
Key Messages: {", ".join(external_view.get("key_messages") or [])}
Observed Capabilities: {", ".join(external_view.get("observed_capabilities") or [])}
Observed Differentiators: {", ".join(external_view.get("observed_differentiators") or [])}
Observed Target Markets: {", ".join(external_view.get("observed_target_markets") or [])}
Tone & Positioning: {external_view.get("tone_and_positioning") or "N/A"}
""".strip()

    return f"""You are a market intelligence analyst for the following company:

{ctx_str}
{chr(10) + external_view_str + chr(10) if external_view_str else ""}
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
  "published_at": "ISO-8601 date string of when the content was originally published, or null if unknown",
  "event_date": "ISO-8601 date string of when the event itself takes place (only for event_or_thought_leadership signals describing a specific event), or null",
  "event_name": "Official name of the event (e.g. 'Dreamforce', 'CeBIT', 'AWS re:Invent') — only for event_or_thought_leadership signals, or null",
  "event_type": "Type of event in German, one of: Messe | Konferenz | Webinar | Summit | Workshop | Roundtable | Pressemitteilung | Sonstiges — only for event_or_thought_leadership signals, or null",
  "event_location": "City or venue where the event takes place (only for event_or_thought_leadership signals describing a specific event), or null"
}}

No markdown fences, no extra text. Only the JSON object."""


def build_self_analysis_prompt(markdown: str, context: Dict[str, Any]) -> str:
    ctx_str = f"""
Company: {context.get("company_name", "N/A")}
Description: {context.get("short_description", "N/A")}
Strategic Priorities: {", ".join(context.get("strategic_priorities", []))}
Differentiators: {", ".join(context.get("differentiators", []))}
""".strip()

    return f"""You are a market intelligence analyst reviewing your own company's external communication.

Internal context about the company:
{ctx_str}

Analyze the following content from the company's own public website/blog and extract a structured signal describing what is being communicated externally.

Focus on: what message or theme this content conveys, how it positions the company, and whether it signals any strategic direction or capability.

CONTENT:
{markdown[:4000]}

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "title": "short descriptive title of the external message (max 100 chars)",
  "signal_type": one of: product_update | ai_announcement | partnership | positioning_change | target_market_change | event_or_thought_leadership | hiring_signal | other,
  "topic": "main topic or theme (max 60 chars)",
  "summary": "2-3 sentence factual summary of what this content communicates",
  "why_it_matters": "1-2 sentences on what this reveals about our external positioning or strategic direction",
  "relevance_score": float between 0.0 (generic/low-signal) and 1.0 (highly strategic message),
  "confidence_score": float between 0.0 (uncertain) and 1.0 (very confident in analysis),
  "published_at": "ISO-8601 date string of when the content was originally published, or null if unknown",
  "event_date": "ISO-8601 date string of when the event itself takes place (only for event_or_thought_leadership signals describing a specific event), or null",
  "event_name": "Official name of the event — only for event_or_thought_leadership signals, or null",
  "event_type": "Type of event in German, one of: Messe | Konferenz | Webinar | Summit | Workshop | Roundtable | Pressemitteilung | Sonstiges — only for event_or_thought_leadership signals, or null",
  "event_location": "City or venue where the event takes place (only for event_or_thought_leadership signals describing a specific event), or null"
}}

No markdown fences, no extra text. Only the JSON object."""
