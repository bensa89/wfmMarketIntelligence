import json
import logging
import re
from collections import defaultdict
from typing import Dict, List
from sqlalchemy.orm import Session, selectinload
from app.models.signal import Signal
from app.analyser.client import call_llm

logger = logging.getLogger(__name__)


_EXCERPT_MAX_CHARS = 200


def _content_excerpt(signal: Signal) -> str:
    doc = signal.document
    if not doc or not doc.content_markdown:
        return ""
    lines = [l for l in doc.content_markdown.splitlines() if l.strip()]
    text = " ".join(lines)
    return text[:_EXCERPT_MAX_CHARS] + ("…" if len(text) > _EXCERPT_MAX_CHARS else "")


def build_dedup_prompt(signals: List[Signal]) -> str:
    lines = []
    for i, s in enumerate(signals, 1):
        url = s.document.url if s.document else "N/A"
        excerpt = _content_excerpt(s)
        lines.append(
            f'{i}. [{s.id}] "{s.title}" | {s.signal_type.value} | '
            f"topic: {s.topic or 'N/A'} | summary: {s.summary or 'N/A'} | "
            f"relevance: {s.relevance_score or 0:.2f} | "
            f"url: {url}"
            + (f" | content_excerpt: {excerpt}" if excerpt else "")
        )
    signal_list = "\n".join(lines)
    return f"""You are a market intelligence analyst reviewing signals for duplicates.

Two signals are duplicates if they refer to the same specific event, announcement, or change — even if worded differently.
Strong indicators of duplicates: identical or very similar URL, nearly identical title or content excerpt, same topic covered from the same angle.
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


def _merge_group(group_signals: List[Signal], db: Session, removed_ids: List[str], kept_signals_data: List[dict]) -> None:
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


def _hash_dedup(signals: List[Signal], db: Session) -> tuple[List[Signal], List[str], List[dict]]:
    removed_ids: List[str] = []
    kept_signals_data: List[dict] = []

    by_hash: dict[str, List[Signal]] = defaultdict(list)
    no_hash: List[Signal] = []
    for s in signals:
        h = s.document.content_hash if s.document else None
        if h:
            by_hash[h].append(s)
        else:
            no_hash.append(s)

    remaining: List[Signal] = list(no_hash)
    for h, group in by_hash.items():
        if len(group) > 1:
            logger.info("Hash-dedup: merging %d signals for content_hash %s", len(group), h)
            _merge_group(group, db, removed_ids, kept_signals_data)
            kept_id = kept_signals_data[-1]["id"]
            remaining.append(next(s for s in group if s.id == kept_id))
        else:
            remaining.extend(group)

    return remaining, removed_ids, kept_signals_data


_BATCH_SIZE = 75


def _llm_dedup_batched(
    signals: List[Signal],
    db: Session,
    removed_ids: List[str],
    kept_signals_data: List[dict],
) -> None:
    deleted_ids: set[str] = set()
    for i in range(0, len(signals), _BATCH_SIZE):
        batch = [s for s in signals[i : i + _BATCH_SIZE] if s.id not in deleted_ids]
        if not batch:
            continue
        valid_ids = {s.id for s in batch}
        prompt = build_dedup_prompt(batch)
        raw_response = call_llm(prompt)
        merge_groups = _parse_merge_groups(raw_response, valid_ids)
        for group_ids in merge_groups:
            group_signals = [s for s in batch if s.id in group_ids]
            _merge_group(group_signals, db, removed_ids, kept_signals_data)
            deleted_ids.update(s.id for s in group_signals[1:])


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

    signals, removed_ids, kept_signals_data = _hash_dedup(signals, db)

    if signals:
        _llm_dedup_batched(signals, db, removed_ids, kept_signals_data)

    merged_count = len(kept_signals_data)
    return {
        "merged_count": merged_count,
        "removed_ids": removed_ids,
        "kept_signals": kept_signals_data,
    }
