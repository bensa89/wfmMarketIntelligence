import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.digest import WeeklyDigest
from app.models.context import InternalCompanyContext
from app.digester.sections import SECTIONS
from app.digester.candidates import (
    query_candidates,
    build_candidate_dict,
    query_own_company_signals,
    build_own_company_signal_dict,
)
from app.digester.dedup import get_prev_signal_index, should_include
from app.digester.curator import curate_section, generate_intro_summary, generate_digest_risks_opportunities
from app.digester.events import build_event_calendar_section


def _get_week_range() -> tuple[date, date]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _get_context_summary(db: Session) -> str:
    ctx = db.query(InternalCompanyContext).first()
    if not ctx:
        return "WFM software company"
    parts: list[str] = []
    if getattr(ctx, "short_description", None):
        parts.append(ctx.short_description)
    if getattr(ctx, "strategic_priorities", None):
        parts.append(f"Priorities: {ctx.strategic_priorities}")
    if getattr(ctx, "differentiators", None):
        parts.append(f"Differentiators: {ctx.differentiators}")
    return " | ".join(parts) or "WFM software company"


def _get_prev_sections(db: Session, current_week_start: date) -> list[dict]:
    prev = (
        db.query(WeeklyDigest)
        .filter(WeeklyDigest.week_start < current_week_start)
        .order_by(WeeklyDigest.week_start.desc())
        .first()
    )
    if prev and prev.sections:
        return prev.sections
    return []


def generate_digest(db: Session) -> WeeklyDigest:
    week_start, week_end = _get_week_range()
    context_summary = _get_context_summary(db)
    prev_sections = _get_prev_sections(db, week_start)
    prev_index = get_prev_signal_index(prev_sections)

    selected_signal_ids: set[str] = set()
    built_sections: list[dict] = []

    for section_def in SECTIONS:
        candidates_raw = query_candidates(
            db,
            section_def,
            week_start,
            week_end,
            excluded_signal_ids=selected_signal_ids,
        )
        candidates = [
            build_candidate_dict(s)
            for s in candidates_raw
            if should_include(s, prev_index)
        ]

        prev_section_items = next(
            (
                s.get("items", [])
                for s in prev_sections
                if s.get("key") == section_def.key
            ),
            [],
        )

        items = curate_section(
            section_def.title, candidates, prev_section_items, context_summary
        )

        if items:
            built_sections.append(
                {
                    "key": section_def.key,
                    "title": section_def.title,
                    "items": items,
                }
            )
            selected_signal_ids.update(item["signal_id"] for item in items)

    own_company_signals = query_own_company_signals(db, week_start, week_end)
    if own_company_signals:
        built_sections.append({
            "key": "own_company_communication",
            "title": "Unsere externe Kommunikation",
            "items": [build_own_company_signal_dict(s) for s in own_company_signals],
        })

    event_section = build_event_calendar_section(db, week_start)
    if event_section:
        built_sections.append(event_section)

    summary = generate_intro_summary(built_sections) if built_sections else ""
    digest_risks, digest_opportunities = (
        generate_digest_risks_opportunities(built_sections, context_summary)
        if built_sections else ([], [])
    )

    digest = WeeklyDigest(
        id=str(uuid.uuid4()),
        week_start=week_start,
        week_end=week_end,
        summary=summary,
        key_signals=[],
        sections=built_sections,
        risks=digest_risks or None,
        opportunities=digest_opportunities or None,
        is_published=False,
    )
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return digest
