import json
import logging
import re
from typing import Dict, List
from sqlalchemy.orm import Session, selectinload
from app.models.signal import Signal
from app.analyser.client import call_llm

logger = logging.getLogger(__name__)


def build_dedup_prompt(signals: List[Signal]) -> str:
    lines = []
    for i, s in enumerate(signals, 1):
        lines.append(
            f'{i}. [{s.id}] "{s.title}" | {s.signal_type.value} | '
            f"topic: {s.topic or 'N/A'} | summary: {s.summary or 'N/A'} | "
            f"relevance: {s.relevance_score or 0:.2f}"
        )
    signal_list = "\n".join(lines)
    return f"""You are a market intelligence analyst reviewing signals for duplicates.

Two signals are duplicates if they refer to the same specific event, announcement, or change — even if worded differently.
Signals about similar but distinct events are NOT duplicates (e.g., two different product launches are not duplicates).

{signal_list}

Return ONLY a valid JSON object:
{{"merge_groups": [[signal_id_1, signal_id_2], [signal_id_3, signal_id_4, signal_id_5]]}}

Each group is a set of duplicate signals. If no duplicates exist, return {{"merge_groups": []}}.
No markdown fences, no extra text."""


def _parse_merge_groups(raw: str, valid_ids: set) -> List[List[str]]:
    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        data = json.loads(raw)
        groups = data.get("merge_groups", [])
        result = []
        for group in groups:
            clean = [gid for gid in group if gid in valid_ids]
            if len(clean) > 1:
                result.append(clean)
        return result
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse LLM dedup response: %s", raw[:200])
        return []


def deduplicate_signals(
    db: Session,
    company_id: str,
    max_age_days: int = 90,
) -> Dict:
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    signals = (
        db.query(Signal)
        .options(selectinload(Signal.document))
        .filter(
            Signal.company_id == company_id,
            Signal.created_at >= cutoff,
        )
        .order_by(Signal.relevance_score.desc())
        .all()
    )

    if not signals:
        return {"merged_count": 0, "removed_ids": [], "kept_signals": []}

    valid_ids = {s.id for s in signals}
    prompt = build_dedup_prompt(signals)
    raw_response = call_llm(prompt)
    merge_groups = _parse_merge_groups(raw_response, valid_ids)

    if not merge_groups:
        return {"merged_count": 0, "removed_ids": [], "kept_signals": []}

    removed_ids = []
    kept_signals_data = []

    for group_ids in merge_groups:
        group_signals = [s for s in signals if s.id in group_ids]
        group_signals.sort(key=lambda s: s.relevance_score or 0, reverse=True)
        primary = group_signals[0]
        others = group_signals[1:]

        for field in ("summary", "why_it_matters"):
            primary_val = getattr(primary, field) or ""
            for other in others:
                other_val = getattr(other, field) or ""
                if len(other_val) > len(primary_val):
                    setattr(primary, field, other_val)
                    primary_val = other_val

        for other in others:
            db.delete(other)
            removed_ids.append(other.id)

        db.commit()
        kept_signals_data.append(
            {
                "id": primary.id,
                "title": primary.title,
                "relevance_score": primary.relevance_score,
            }
        )

    return {
        "merged_count": len(merge_groups),
        "removed_ids": removed_ids,
        "kept_signals": kept_signals_data,
    }
