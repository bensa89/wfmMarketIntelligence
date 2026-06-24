import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, case

from app.database import get_db
from app.models.company import Company, CompanyType
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment, MovementStrength
from app.models.competitor_summary import CompetitorSummary, PeriodType
from app.models.intelligence_briefing import IntelligenceBriefing

logger = logging.getLogger(__name__)
router = APIRouter()


def _assessment_to_dict(a: SignalAssessment) -> dict:
    return {
        "id": a.id,
        "signal_id": a.signal_id,
        "company_id": a.company_id,
        "capability_primary": a.capability_primary,
        "capability_secondary": a.capability_secondary or [],
        "signal_class": a.signal_class.value if a.signal_class else None,
        "evidence_strength": a.evidence_strength,
        "visibility_impact": a.visibility_impact.value if a.visibility_impact else None,
        "strategic_weight": a.strategic_weight,
        "movement_score": a.movement_score,
        "movement_strength": a.movement_strength.value if a.movement_strength else None,
        "confidence": a.confidence,
        "strategic_intent_guess": a.strategic_intent_guess,
        "gameplay_tags": a.gameplay_tags or [],
        "assessment_summary": a.assessment_summary,
        "implication_for_us": a.implication_for_us,
        "watch_items": a.watch_items or [],
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _signal_feed_item(signal: Signal, assessment: Optional[SignalAssessment]) -> dict:
    doc = signal.document
    return {
        "id": signal.id,
        "title": signal.title,
        "signal_type": signal.signal_type.value,
        "topic": signal.topic,
        "summary": signal.summary,
        "why_it_matters": signal.why_it_matters,
        "relevance_score": signal.relevance_score,
        "confidence_score": signal.confidence_score,
        "published_at": signal.published_at.isoformat() if signal.published_at else None,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
        "company_id": signal.company_id,
        "company_name": signal.company.name if signal.company else None,
        "company_slug": signal.company.slug if signal.company else None,
        "source_url": doc.url if doc else None,
        "document_id": signal.document_id,
        "document_title": doc.title if doc else None,
        "event_date": signal.event_date.date().isoformat() if signal.event_date else None,
        "event_name": signal.event_name,
        "event_type": signal.event_type,
        "event_location": signal.event_location,
        "company_logo_path": signal.company.logo_path if signal.company else None,
        "assessment": _assessment_to_dict(assessment) if assessment else None,
    }


@router.get("/events")
def get_events(db: Session = Depends(get_db), full: bool = Query(False)) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    query = (
        db.query(Signal)
        .options(selectinload(Signal.company))
        .filter(
            Signal.signal_type == "event_or_thought_leadership",
            Signal.event_date.isnot(None),
        )
    )
    if not full:
        cutoff_30d = now - timedelta(days=30)
        query = query.filter(Signal.event_date >= cutoff_30d)

    signals = query.order_by(Signal.event_date.asc()).all()

    upcoming: list[dict] = []
    past: list[dict] = []

    event_map: dict[str, dict] = {}
    for signal in signals:
        if not signal.event_date or not signal.company:
            continue
        key = f"{signal.event_date.date()}||{signal.title.strip().lower()}"
        if key not in event_map:
            event_map[key] = {
                "event_date": signal.event_date.date().isoformat(),
                "event_name": signal.event_name,
                "event_type": signal.event_type,
                "event_location": signal.event_location,
                "title": signal.title,
                "newest_signal_at": signal.created_at.isoformat() if signal.created_at else None,
                "attendees": [],
            }
        else:
            if signal.created_at and (
                event_map[key]["newest_signal_at"] is None
                or signal.created_at.isoformat() > event_map[key]["newest_signal_at"]
            ):
                event_map[key]["newest_signal_at"] = signal.created_at.isoformat()
        event_map[key]["attendees"].append({
            "company_id": signal.company_id,
            "company_name": signal.company.name,
            "company_slug": signal.company.slug,
            "signal_id": signal.id,
            "relevance_score": signal.relevance_score,
        })

    for entry in event_map.values():
        entry["attendees"].sort(key=lambda a: a["relevance_score"] or 0, reverse=True)
        if entry["event_date"] >= now.date().isoformat():
            upcoming.append(entry)
        else:
            past.append(entry)

    upcoming.sort(key=lambda e: e["event_date"])
    past.sort(key=lambda e: e["event_date"], reverse=True)

    return {"upcoming": upcoming, "past": past}


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    def _top_movers(cutoff: datetime) -> list[dict]:
        rows = (
            db.query(
                SignalAssessment.company_id,
                func.avg(SignalAssessment.movement_score).label("avg_score"),
                func.count(SignalAssessment.id).label("count"),
            )
            .join(Signal, SignalAssessment.signal_id == Signal.id)
            .join(Company, Company.id == SignalAssessment.company_id)
            .filter(Signal.created_at >= cutoff, Company.type == CompanyType.competitor)
            .group_by(SignalAssessment.company_id)
            .order_by(func.avg(SignalAssessment.movement_score).desc())
            .limit(10)
            .all()
        )
        result = []
        for row in rows:
            company = db.query(Company).filter(Company.id == row.company_id).first()
            if not company:
                continue
            top_cap = (
                db.query(SignalAssessment.capability_primary)
                .join(Signal, SignalAssessment.signal_id == Signal.id)
                .filter(SignalAssessment.company_id == row.company_id, Signal.created_at >= cutoff)
                .group_by(SignalAssessment.capability_primary)
                .order_by(func.count(SignalAssessment.id).desc())
                .limit(1)
                .scalar()
            )
            result.append({
                "company_id": company.id,
                "company_name": company.name,
                "company_slug": company.slug,
                "logo_path": company.logo_path,
                "avg_movement_score": round(row.avg_score or 0, 1),
                "signal_count": row.count,
                "top_capability": top_cap,
            })
        return result

    def _heatmap(cutoff: datetime) -> list[dict]:
        heatmap_rows = (
            db.query(
                SignalAssessment.company_id,
                SignalAssessment.capability_primary,
                func.avg(SignalAssessment.movement_score).label("avg_score"),
            )
            .join(Signal, SignalAssessment.signal_id == Signal.id)
            .filter(Signal.created_at >= cutoff, SignalAssessment.capability_primary.isnot(None))
            .group_by(SignalAssessment.company_id, SignalAssessment.capability_primary)
            .all()
        )
        heatmap: dict[str, dict] = {}
        for row in heatmap_rows:
            company = db.query(Company).filter(Company.id == row.company_id).first()
            if not company or company.type != CompanyType.competitor:
                continue
            key = company.id
            if key not in heatmap:
                heatmap[key] = {
                    "company_id": company.id,
                    "company_name": company.name,
                    "company_slug": company.slug,
                    "company_logo_path": company.logo_path,
                    "capabilities": {},
                }
            if row.capability_primary:
                heatmap[key]["capabilities"][row.capability_primary] = round(row.avg_score or 0, 1)
        return list(heatmap.values())

    strength_rank = case(
        (SignalAssessment.movement_strength == MovementStrength.market_shaping, 0),
        (SignalAssessment.movement_strength == MovementStrength.strong, 1),
        else_=2,
    )

    def _market_shaping_signals(cutoff: datetime) -> list[SignalAssessment]:
        return (
            db.query(SignalAssessment)
            .options(selectinload(SignalAssessment.signal))
            .filter(SignalAssessment.movement_strength.in_(
                [MovementStrength.strong, MovementStrength.market_shaping]
            ))
            .join(Signal, SignalAssessment.signal_id == Signal.id)
            .filter(Signal.created_at >= cutoff)
            .order_by(strength_rank, Signal.created_at.desc())
            .limit(10)
            .all()
        )

    market_shaping_7d = _market_shaping_signals(cutoff_7d)
    market_shaping_30d = _market_shaping_signals(cutoff_30d)
    market_shaping_90d = _market_shaping_signals(cutoff_90d)

    def _to_overview_item(raw: dict | str, company: Company) -> dict:
        if isinstance(raw, dict):
            return {
                "text": raw.get("text", ""),
                "signal_ids": raw.get("signal_ids") or [],
                "is_new": raw.get("is_new", False),
                "company_id": company.id,
                "company_name": company.name,
                "company_slug": company.slug,
                "logo_path": company.logo_path,
            }
        return {
            "text": raw,
            "signal_ids": [],
            "is_new": False,
            "company_id": company.id,
            "company_name": company.name,
            "company_slug": company.slug,
            "logo_path": company.logo_path,
        }

    def _dedup(items: list[dict], max_items: int = 10) -> list[dict]:
        seen: set[str] = set()
        result = []
        for item in items:
            key = item["text"].strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(item)
                if len(result) >= max_items:
                    break
        return result

    # Use LLM-curated items from latest briefing if available, else fall back to mechanical aggregation
    latest_briefing = (
        db.query(IntelligenceBriefing)
        .filter(IntelligenceBriefing.curated_risks.isnot(None))
        .order_by(IntelligenceBriefing.generated_at.desc())
        .first()
    )

    if latest_briefing:
        emerging_risks: list[dict] = latest_briefing.curated_risks or []
        emerging_opportunities: list[dict] = latest_briefing.curated_opportunities or []
        emerging_watchpoints: list[dict] = latest_briefing.curated_watchpoints or []

        all_cids = {
            item.get("company_id")
            for items in (emerging_risks, emerging_opportunities, emerging_watchpoints)
            for item in items
            if item.get("company_id")
        }
        logo_by_id = {
            c.id: c.logo_path
            for c in db.query(Company).filter(Company.id.in_(all_cids)).all()
        }
        for items in (emerging_risks, emerging_opportunities, emerging_watchpoints):
            for item in items:
                if "logo_path" not in item:
                    item["logo_path"] = logo_by_id.get(item.get("company_id"))
    else:
        emerging_risks = []
        emerging_opportunities = []
        emerging_watchpoints = []
        companies_with_summaries = (
            db.query(CompetitorSummary.company_id)
            .filter(CompetitorSummary.period_type == PeriodType.thirty_days)
            .distinct()
            .all()
        )
        for (cid,) in companies_with_summaries:
            company = db.query(Company).filter(Company.id == cid).first()
            if not company:
                continue
            latest = (
                db.query(CompetitorSummary)
                .filter(
                    CompetitorSummary.company_id == cid,
                    CompetitorSummary.period_type == PeriodType.thirty_days,
                )
                .order_by(CompetitorSummary.created_at.desc())
                .first()
            )
            if latest:
                emerging_risks.extend(
                    _to_overview_item(item, company)
                    for item in (latest.top_risks or [])
                    if item
                )
                emerging_opportunities.extend(
                    _to_overview_item(item, company)
                    for item in (latest.top_opportunities or [])
                    if item
                )
                emerging_watchpoints.extend(
                    _to_overview_item(item, company)
                    for item in (latest.watchpoints or [])
                    if item
                )
        emerging_risks = _dedup(emerging_risks)
        emerging_opportunities = _dedup(emerging_opportunities)
        emerging_watchpoints = _dedup(emerging_watchpoints)

    return {
        "top_movers_7d": _top_movers(cutoff_7d),
        "top_movers_30d": _top_movers(cutoff_30d),
        "capability_heatmap_7d": _heatmap(cutoff_7d),
        "capability_heatmap_30d": _heatmap(cutoff_30d),
        "recent_market_shaping_7d": [
            _signal_feed_item(a.signal, a) for a in market_shaping_7d if a.signal
        ],
        "recent_market_shaping_30d": [
            _signal_feed_item(a.signal, a) for a in market_shaping_30d if a.signal
        ],
        "recent_market_shaping_90d": [
            _signal_feed_item(a.signal, a) for a in market_shaping_90d if a.signal
        ],
        "emerging_risks": emerging_risks,
        "emerging_opportunities": emerging_opportunities,
        "emerging_watchpoints": emerging_watchpoints,
    }


@router.get("/competitors/{slug}/workspace")
def get_competitor_workspace(slug: str, db: Session = Depends(get_db)) -> dict:
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Competitor not found")

    now = datetime.now(timezone.utc)

    def _latest_summary(period_type: PeriodType):
        return (
            db.query(CompetitorSummary)
            .filter(
                CompetitorSummary.company_id == company.id,
                CompetitorSummary.period_type == period_type,
            )
            .order_by(CompetitorSummary.created_at.desc())
            .first()
        )

    def _summary_to_dict(s: Optional[CompetitorSummary]) -> Optional[dict]:
        if s is None:
            return None
        return {
            "id": s.id,
            "company_id": s.company_id,
            "period_type": s.period_type.value,
            "period_start": s.period_start.isoformat(),
            "period_end": s.period_end.isoformat(),
            "strategic_posture": s.strategic_posture,
            "positioning_summary": s.positioning_summary,
            "top_capabilities": s.top_capabilities or [],
            "capability_assessment": s.capability_assessment or [],
            "top_risks": s.top_risks or [],
            "top_opportunities": s.top_opportunities or [],
            "watchpoints": s.watchpoints or [],
            "what_changed": s.what_changed,
            "avg_movement_score": s.avg_movement_score,
            "signal_count": s.signal_count,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }

    recent_assessments = (
        db.query(SignalAssessment)
        .options(selectinload(SignalAssessment.signal))
        .filter(SignalAssessment.company_id == company.id)
        .join(Signal, SignalAssessment.signal_id == Signal.id)
        .order_by(Signal.created_at.desc())
        .limit(20)
        .all()
    )

    cap_dist_rows = (
        db.query(
            SignalAssessment.capability_primary,
            func.count(SignalAssessment.id).label("count"),
            func.avg(SignalAssessment.movement_score).label("avg_score"),
        )
        .filter(SignalAssessment.company_id == company.id, SignalAssessment.capability_primary.isnot(None))
        .group_by(SignalAssessment.capability_primary)
        .order_by(func.count(SignalAssessment.id).desc())
        .all()
    )

    timeline = (
        db.query(Signal)
        .options(selectinload(Signal.assessment))
        .filter(Signal.company_id == company.id)
        .order_by(Signal.published_at.desc().nullslast(), Signal.created_at.desc())
        .limit(30)
        .all()
    )

    return {
        "competitor_profile": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "type": company.type.value,
            "description": company.description,
            "website": company.website,
            "logo_path": company.logo_path,
            "created_at": company.created_at.isoformat() if company.created_at else None,
        },
        "summary_30d": _summary_to_dict(_latest_summary(PeriodType.thirty_days)),
        "summary_90d": _summary_to_dict(_latest_summary(PeriodType.ninety_days)),
        "recent_assessments": [
            _signal_feed_item(a.signal, a) for a in recent_assessments if a.signal
        ],
        "capability_distribution": [
            {
                "capability_key": r.capability_primary,
                "count": r.count,
                "avg_movement_score": round(r.avg_score or 0, 1),
            }
            for r in cap_dist_rows
        ],
        "timeline_of_moves": [
            {
                "signal_id": s.id,
                "title": s.title,
                "signal_type": s.signal_type.value,
                "published_at": s.published_at.isoformat() if s.published_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "movement_strength": s.assessment.movement_strength.value if s.assessment and s.assessment.movement_strength else None,
                "movement_score": s.assessment.movement_score if s.assessment else None,
                "capability_primary": s.assessment.capability_primary if s.assessment else None,
            }
            for s in timeline
        ],
    }


@router.get("/signals/feed")
def get_signals_feed(
    company_id: Optional[str] = None,
    capability: Optional[str] = None,
    signal_type: Optional[str] = None,
    movement_strength: Optional[str] = None,
    min_confidence: Optional[float] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    sort_by: str = Query(default="published_at", pattern="^(published_at|movement_score|confidence)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    query = (
        db.query(Signal)
        .options(
            selectinload(Signal.company),
            selectinload(Signal.document),
            selectinload(Signal.assessment),
        )
    )

    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if from_date:
        try:
            query = query.filter(Signal.published_at >= datetime.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            query = query.filter(Signal.published_at <= datetime.fromisoformat(to_date))
        except ValueError:
            pass
    if created_from:
        try:
            query = query.filter(Signal.created_at >= datetime.fromisoformat(created_from))
        except ValueError:
            pass
    if created_to:
        try:
            query = query.filter(Signal.created_at <= datetime.fromisoformat(created_to).replace(hour=23, minute=59, second=59))
        except ValueError:
            pass

    if capability or movement_strength or min_confidence:
        query = query.join(SignalAssessment, SignalAssessment.signal_id == Signal.id, isouter=True)
        if capability:
            query = query.filter(SignalAssessment.capability_primary == capability)
        if movement_strength:
            query = query.filter(SignalAssessment.movement_strength == movement_strength)
        if min_confidence:
            query = query.filter(SignalAssessment.confidence >= min_confidence)

    total = query.count()

    if sort_by == "movement_score":
        if not (capability or movement_strength or min_confidence):
            query = query.join(SignalAssessment, SignalAssessment.signal_id == Signal.id, isouter=True)
        query = query.order_by(SignalAssessment.movement_score.desc().nullslast(), Signal.created_at.desc())
    elif sort_by == "confidence":
        if not (capability or movement_strength or min_confidence):
            query = query.join(SignalAssessment, SignalAssessment.signal_id == Signal.id, isouter=True)
        query = query.order_by(SignalAssessment.confidence.desc().nullslast(), Signal.created_at.desc())
    else:
        query = query.order_by(Signal.published_at.desc().nullslast(), Signal.created_at.desc())

    signals = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_signal_feed_item(s, s.assessment) for s in signals],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/signals/{signal_id}")
def get_signal_feed_item(signal_id: str, db: Session = Depends(get_db)) -> dict:
    signal = (
        db.query(Signal)
        .options(
            selectinload(Signal.company),
            selectinload(Signal.document),
            selectinload(Signal.assessment),
        )
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _signal_feed_item(signal, signal.assessment)


@router.post("/signals/{signal_id}/assess")
def trigger_assess_signal(signal_id: str, db: Session = Depends(get_db)) -> dict:
    signal = (
        db.query(Signal)
        .options(selectinload(Signal.company), selectinload(Signal.document))
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    from app.assessor.pipeline import assess_signal
    assessment = assess_signal(signal, db)
    if assessment is None:
        raise HTTPException(status_code=422, detail="Assessment generation failed")
    return _assessment_to_dict(assessment)


@router.post("/competitors/{company_id}/summarize")
def trigger_summarize(
    company_id: str,
    period_type: str = Query(default="30d", pattern="^(7d|30d|90d|quarter)$"),
    db: Session = Depends(get_db),
) -> dict:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from app.assessor.summarizer import generate_competitor_summary
    summary = generate_competitor_summary(company, period_type, db)
    if summary is None:
        raise HTTPException(status_code=422, detail="No assessments found for this period")

    return {
        "id": summary.id,
        "company_id": summary.company_id,
        "period_type": summary.period_type.value,
        "strategic_posture": summary.strategic_posture,
        "signal_count": summary.signal_count,
        "avg_movement_score": summary.avg_movement_score,
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
    }
