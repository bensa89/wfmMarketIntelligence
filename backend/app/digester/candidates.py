from datetime import date, datetime, time
from urllib.parse import urlparse

from sqlalchemy.orm import Session, selectinload

from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.document import Document
from app.models.source import Source, SourceType
from app.digester.sections import SectionDef


def query_candidates(
    db: Session,
    section: SectionDef,
    week_start: date,
    week_end: date,
    excluded_signal_ids: set[str] | None = None,
) -> list[Signal]:
    q = (
        db.query(Signal)
        .join(Signal.document)
        .join(Document.source)
        .outerjoin(Signal.assessment)
        .options(
            selectinload(Signal.company),
            selectinload(Signal.document).selectinload(Document.source),
            selectinload(Signal.assessment),
        )
        .filter(
            Signal.created_at >= datetime.combine(week_start, time.min),
            Signal.created_at <= datetime.combine(week_end, time.max),
        )
    )

    if section.use_source_type_filter:
        q = q.filter(Source.source_type.in_([SourceType.news, SourceType.press]))
    elif section.signal_types:
        q = q.filter(Signal.signal_type.in_(section.signal_types))

    if excluded_signal_ids:
        q = q.filter(Signal.id.notin_(excluded_signal_ids))

    from sqlalchemy import func

    q = q.order_by(
        func.coalesce(SignalAssessment.movement_score, -1).desc(),
        func.coalesce(Signal.relevance_score, 0.0).desc(),
    )

    return q.limit(30).all()


def build_candidate_dict(signal: Signal) -> dict:
    doc = signal.document
    assessment = signal.assessment
    domain = urlparse(doc.url).netloc if doc and doc.url else None
    return {
        "signal_id": signal.id,
        "company": signal.company.name if signal.company else "Unknown",
        "title": signal.title or "",
        "assessment_summary": assessment.assessment_summary
        if assessment
        else (signal.summary or ""),
        "implication_for_us": assessment.implication_for_us if assessment else None,
        "strategic_intent_guess": assessment.strategic_intent_guess
        if assessment
        else None,
        "movement_strength": assessment.movement_strength.value
        if assessment and assessment.movement_strength
        else None,
        "source_url": doc.url if doc else None,
        "source_domain": domain,
        "source_title": (doc.title or domain) if doc else None,
    }
