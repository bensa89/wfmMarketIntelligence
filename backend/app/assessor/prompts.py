import json
from typing import Any

ASSESSMENT_SYSTEM_PROMPT = """You are a competitive intelligence analyst for a Workforce Management (WFM) software company.
Your task is to assess competitor signals and return a structured JSON evaluation.
Return ONLY valid JSON. No prose, no explanation, no markdown code fences.
Your output must be parseable by json.loads()."""


def build_assessment_prompt(
    company_name: str,
    signal_type: str,
    title: str,
    topic: str | None,
    summary: str | None,
    why_it_matters: str | None,
    relevance_score: float,
    confidence_score: float,
    context: dict[str, Any],
    capability_keys: list[str],
) -> str:
    return f"""Assess this competitor signal for a WFM software vendor.

Signal:
- Company: {company_name}
- Type: {signal_type}
- Title: {title}
- Topic: {topic or "unknown"}
- Summary: {summary or "no summary"}
- Why it matters: {why_it_matters or "unknown"}
- Relevance score: {relevance_score}
- Confidence score: {confidence_score}

Our internal context:
- Core capabilities: {", ".join(context.get("core_capabilities", []))}
- Strategic priorities: {", ".join(context.get("strategic_priorities", []))}
- Differentiators: {", ".join(context.get("differentiators", []))}

Available capability keys: {", ".join(capability_keys)}

Return exactly this JSON object (no other text):
{{
  "capability_primary": "<one capability key from the list above, or null>",
  "capability_secondary": ["<key>"],
  "signal_class": "<product_capability_move|positioning_move|ecosystem_move|thought_leadership_signal|hiring_signal|weak_signal|market_expansion_move>",
  "evidence_strength": <integer 1-5>,
  "visibility_impact": "<low|medium|high>",
  "strategic_intent_guess": "<one sentence describing likely strategic intent>",
  "gameplay_tags": ["<tag>"],
  "assessment_summary": "<2-3 sentence summary of what this signal means>",
  "implication_for_us": "<1-2 sentences on what this means for our product/strategy>",
  "watch_items": ["<specific thing to monitor>"],
  "confidence": <float 0.0-1.0>,
  "buyer_relevance": <integer 1-5, only if evidence_strength >= 4 or movement is market_shaping — else omit>,
  "assessment_weight": <float 0.5-2.0, only if evidence_strength >= 4 or movement is market_shaping — else omit>
}}

If this signal has evidence_strength >= 4 or is market-shaping, also include:
- buyer_relevance (1=no direct buyer impact, 5=directly influences purchasing decisions)
- assessment_weight (0.5=significantly less important than typical, 2.0=exceptionally significant, default 1.0)
Otherwise omit these two fields entirely."""


SUMMARY_SYSTEM_PROMPT = """You are a competitive intelligence analyst for a WFM software company.
Synthesize multiple signal assessments into a competitor summary.
Return ONLY valid JSON. No prose, no markdown."""


def build_summary_prompt(
    company_name: str,
    period_label: str,
    assessments: list[dict[str, Any]],
    context: dict[str, Any],
) -> str:
    assessments_text = json.dumps(assessments, indent=2)
    return f"""Synthesize these signal assessments for competitor "{company_name}" over the {period_label}.

Assessments ({len(assessments)} signals):
{assessments_text}

Our internal context:
- Core capabilities: {", ".join(context.get("core_capabilities", []))}
- Strategic priorities: {", ".join(context.get("strategic_priorities", []))}

Return exactly this JSON object (no other text):
{{
  "strategic_posture": "<2-4 word label e.g. aggressive_expansion, defensive_consolidation, niche_deepening>",
  "positioning_summary": "<2-3 sentences on the competitor's overall strategic direction>",
  "top_capabilities": ["<capability_key>"],
  "capability_assessment": [
    {{"key": "<capability_key>", "label": "<label>", "activity_level": "<low|medium|high>", "notes": "<one sentence>"}}
  ],
  "top_risks": [
    {{"text": "<risk for us, one sentence>", "signal_ids": ["<signal_id from the list above>"]}}
  ],
  "top_opportunities": [
    {{"text": "<opportunity for us, one sentence>", "signal_ids": ["<signal_id from the list above>"]}}
  ],
  "watchpoints": [
    {{"text": "<specific thing to monitor>", "signal_ids": ["<signal_id from the list above>"]}}
  ]
}}

Each item in top_risks, top_opportunities, and watchpoints must cite 1-3 signal_ids from the assessments list above (use the exact signal_id values). Only include signal_ids that directly support or evidence the stated point."""
