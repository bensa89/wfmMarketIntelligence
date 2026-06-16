from datetime import date, datetime, time
from urllib.parse import urlparse

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.document import Document
from app.models.source import Source, SourceType
from app.models.company import Company, CompanyType
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

    if section.competitor_only:
        q = q.join(Signal.company).filter(Company.type == CompanyType.competitor)

    if section.use_source_type_filter and section.signal_types:
        q = q.filter(
            or_(
                Signal.signal_type.in_(section.signal_types),
                Source.source_type.in_([SourceType.news, SourceType.press]),
            )
        )
    elif section.use_source_type_filter:
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


def query_own_company_signals(
    db: Session,
    week_start: date,
    week_end: date,
) -> list[Signal]:
    from datetime import time as dt_time
    return (
        db.query(Signal)
        .join(Signal.company)
        .join(Signal.document)
        .options(
            selectinload(Signal.company),
            selectinload(Signal.document).selectinload(Document.source),
            selectinload(Signal.assessment),
        )
        .filter(
            Company.type == CompanyType.own_company,
            Signal.created_at >= datetime.combine(week_start, dt_time.min),
            Signal.created_at <= datetime.combine(week_end, dt_time.max),
            Signal.relevance_score >= 0.55,
        )
        .order_by(Signal.relevance_score.desc())
        .limit(4)
        .all()
    )


def build_own_company_signal_dict(signal: Signal) -> dict:
    doc = signal.document
    domain = urlparse(doc.url).netloc if doc and doc.url else None
    return {
        "signal_id": signal.id,
        "title": signal.title or "",
        "topic": signal.topic or "",
        "summary": signal.summary or "",
        "why_it_matters": signal.why_it_matters or "",
        "signal_type": signal.signal_type.value if signal.signal_type else None,
        "relevance_score": signal.relevance_score,
        "source_url": doc.url if doc else None,
        "source_domain": domain,
        "source_title": (doc.title or domain) if doc else None,
        "published_at": signal.published_at.isoformat() if signal.published_at else None,
    }


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
