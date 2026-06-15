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
            "\nVorheriger Digest (gleiche Sektion — nicht wiederholen, außer bei signifikanter Aktualisierung):\n"
            + "\n".join(f"- {item.get('title', '')}" for item in prev_section_items)
        )

    return f"""Du bist ein Competitive-Intelligence-Analyst und kurierst die Sektion "{section_title}" eines wöchentlichen Briefings für ein Workforce-Management-Unternehmen (WFM).

Unser Kontext: {context_summary}
{prev_text}

Kandidaten — wähle die 1–3 wichtigsten:
{candidates_text}

Antworte AUSSCHLIESSLICH auf Deutsch und als valides JSON, ohne Prosa, ohne Markdown-Zäune:
{{
  "selected_items": [
    {{
      "signal_id": "<exakte signal_id aus den Kandidaten>",
      "title": "<prägnanter deutscher Titel, max. 10 Wörter>",
      "narrative": "<2–3 Sätze: Erkenntnis klar und prägnant formuliert>",
      "implication_for_us": "<1–2 Sätze: Was bedeutet das für unser Produkt oder unsere Strategie?>"
    }}
  ]
}}

Regeln:
- Nur signal_ids aus der Kandidatenliste verwenden
- Keine neuen Analysen erfinden — vorhandene Assessment-Daten umformulieren
- Wenn keine Kandidaten relevant sind, {{"selected_items": []}} zurückgeben
"""


def build_risks_opportunities_prompt(sections: list[dict], context_summary: str) -> str:
    items_text = "\n".join(
        f"- [{section['title']}] {item.get('company', '')} — {item.get('title', '')}\n"
        f"  Narrative: {item.get('narrative', '')}\n"
        f"  Implication: {item.get('implication_for_us', '')}"
        for section in sections
        for item in section.get("items", [])
        if section.get("key") != "events_calendar"
    )
    return (
        "Du bist ein strategischer Competitive-Intelligence-Analyst für ein WFM-Softwareunternehmen.\n"
        f"Unser Kontext: {context_summary}\n\n"
        "Basierend auf den kuratierten Signalen dieser Woche: identifiziere die 2 wichtigsten Risks "
        "und die 2 wichtigsten Opportunities für unser Unternehmen.\n\n"
        f"Kuratierte Signale:\n{items_text}\n\n"
        "Antworte AUSSCHLIESSLICH als valides JSON, auf Deutsch, ohne Prosa:\n"
        '{"risks": [{"text": "<1 klarer Satz>", "company_name": "<Competitor>"}, ...], '
        '"opportunities": [{"text": "<1 klarer Satz>", "company_name": "<Competitor>"}, ...]}'
    )


def build_intro_summary_prompt(sections: list[dict]) -> str:
    items_text = "\n".join(
        f"[{section['title']}] {item.get('title', '')} ({item.get('company', '')})"
        for section in sections
        for item in section.get("items", [])
    )
    return (
        "Schreibe eine 1–2 Sätze lange Zusammenfassung auf Deutsch "
        "der wichtigsten Competitive-Intelligence-Erkenntnis dieser Woche.\n\n"
        f"Diese Woche:\n{items_text}\n\n"
        "Antworte AUSSCHLIESSLICH als valides JSON, auf Deutsch, ohne Prosa:\n"
        '{"summary": "<1–2 Sätze auf Deutsch>"}'
    )
