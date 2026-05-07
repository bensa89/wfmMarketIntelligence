def build_section_curation_prompt(
    section_title: str,
    candidates: list[dict],
    prev_section_items: list[dict],
    context_summary: str,
) -> str:
    candidates_text = "\n".join(
        f"[{i + 1}] signal_id={c['signal_id']}\n"
        f"  Company: {c['company']}\n"
        f"  Title: {c['title']}\n"
        f"  Assessment: {c.get('assessment_summary', '')}\n"
        f"  Implication: {c.get('implication_for_us', '')}\n"
        f"  Strategic intent: {c.get('strategic_intent_guess', '')}\n"
        f"  Movement: {c.get('movement_strength', 'unknown')}"
        for i, c in enumerate(candidates)
    )

    prev_text = ""
    if prev_section_items:
        prev_text = (
            "\nPrevious digest (same section — avoid repeating unless significantly updated):\n"
            + "\n".join(f"- {item.get('title', '')}" for item in prev_section_items)
        )

    return f"""You are a competitive intelligence analyst curating the "{section_title}" section of a weekly briefing for a Workforce Management (WFM) software company.

Our context: {context_summary}
{prev_text}

Candidates — select 1–3 most important:
{candidates_text}

Return ONLY valid JSON, no prose, no markdown fences:
{{
  "selected_items": [
    {{
      "signal_id": "<exact signal_id from candidates above>",
      "narrative": "<2-3 sentences summarising the finding as a clear insight>",
      "implication_for_us": "<1-2 sentences on what this means for our product or strategy>"
    }}
  ]
}}

Rules:
- Only use signal_ids from the candidates list
- Do not invent new analysis — reframe existing assessment data
- If no candidates are worth including, return {{"selected_items": []}}
"""


def build_intro_summary_prompt(sections: list[dict]) -> str:
    items_text = "\n".join(
        f"[{section['title']}] {item.get('title', '')} ({item.get('company', '')})"
        for section in sections
        for item in section.get("items", [])
    )
    return f"""Write a 1–2 sentence executive summary of this week's most important competitive intelligence finding.

Items this week:
{items_text}

Return ONLY valid JSON, no prose:
{{"summary": "<1-2 sentences>"}}
"""
