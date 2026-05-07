import json

from app.analyser.client import call_llm
from app.digester.prompts import (
    build_section_curation_prompt,
    build_intro_summary_prompt,
)


def curate_section(
    section_title: str,
    candidates: list[dict],
    prev_section_items: list[dict],
    context_summary: str,
) -> list[dict]:
    if not candidates:
        return []

    prompt = build_section_curation_prompt(
        section_title, candidates, prev_section_items, context_summary
    )
    response = call_llm(prompt, max_tokens=2048)

    try:
        data = json.loads(response)
        selected = data.get("selected_items", [])
    except (json.JSONDecodeError, AttributeError):
        return []

    candidate_by_id = {c["signal_id"]: c for c in candidates}
    result = []
    for item in selected:
        sid = item.get("signal_id")
        if sid not in candidate_by_id:
            continue
        base = candidate_by_id[sid]
        result.append(
            {
                "signal_id": sid,
                "company": base["company"],
                "title": base["title"],
                "narrative": item.get("narrative", ""),
                "implication_for_us": item.get("implication_for_us")
                or base.get("implication_for_us")
                or "",
                "movement_strength": base.get("movement_strength"),
                "source_url": base.get("source_url"),
                "source_domain": base.get("source_domain"),
                "source_title": base.get("source_title"),
            }
        )
    return result


def generate_intro_summary(sections: list[dict]) -> str:
    prompt = build_intro_summary_prompt(sections)
    response = call_llm(prompt, max_tokens=256)
    try:
        data = json.loads(response)
        return data.get("summary", "")
    except (json.JSONDecodeError, AttributeError):
        return ""
