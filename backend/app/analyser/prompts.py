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

    return f"""Du bist ein Market-Intelligence-Analyst und analysierst die externe Kommunikation deines eigenen Unternehmens.

Interner Kontext über das Unternehmen:
{ctx_str}

Analysiere den folgenden Inhalt von der öffentlichen Website oder dem Blog des Unternehmens. Beschreibe, was nach außen kommuniziert wird.

Fokus auf: Welche Botschaft oder welches Thema vermittelt dieser Inhalt? Wie positioniert er das Unternehmen? Signalisiert er eine strategische Richtung oder Capability?

INHALT:
{markdown[:4000]}

Antworte NUR mit einem gültigen JSON-Objekt nach diesem Schema. Alle Texte (title, topic, summary, why_it_matters) MÜSSEN AUF DEUTSCH sein:
{{
  "title": "kurzer beschreibender Titel der externen Botschaft (max 100 Zeichen, auf Deutsch)",
  "signal_type": eines von: product_update | ai_announcement | partnership | positioning_change | target_market_change | event_or_thought_leadership | hiring_signal | other,
  "topic": "Hauptthema oder -schwerpunkt (max 60 Zeichen, auf Deutsch)",
  "summary": "2-3 Sätze faktische Zusammenfassung was dieser Inhalt kommuniziert (auf Deutsch)",
  "why_it_matters": "1-2 Sätze was dies über unsere externe Positionierung oder strategische Ausrichtung aussagt (auf Deutsch)",
  "relevance_score": Dezimalzahl zwischen 0.0 (generisch/wenig aussagekräftig) und 1.0 (sehr strategische Botschaft),
  "confidence_score": Dezimalzahl zwischen 0.0 (unsicher) und 1.0 (sehr sicher in der Analyse),
  "published_at": "ISO-8601 Datumsstring des ursprünglichen Veröffentlichungsdatums, oder null falls unbekannt",
  "event_date": "ISO-8601 Datumsstring wann das Event stattfindet (nur für event_or_thought_leadership mit konkretem Termin), oder null",
  "event_name": "Offizieller Name des Events — nur für event_or_thought_leadership, oder null",
  "event_type": "Art des Events auf Deutsch, eines von: Messe | Konferenz | Webinar | Summit | Workshop | Roundtable | Pressemitteilung | Sonstiges — nur für event_or_thought_leadership, oder null",
  "event_location": "Stadt oder Veranstaltungsort (nur für event_or_thought_leadership mit konkretem Termin), oder null"
}}

Keine Markdown-Fences, kein zusätzlicher Text. Nur das JSON-Objekt."""
