import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.analyser.client import call_llm
from app.assessor.prompts import build_summary_prompt
from app.assessor.parser import parse_summary_response
from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.competitor_summary import CompetitorSummary, PeriodType
from app.models.context import InternalCompanyContext

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "quarter": 90}
_PERIOD_LABELS = {"7d": "last 7 days", "30d": "last 30 days", "90d": "last 90 days", "quarter": "last quarter"}


def generate_competitor_summary(
    company: Company,
    period_type: str,
    db: Session,
) -> CompetitorSummary | None:
    days = _PERIOD_DAYS.get(period_type, 30)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    assessments = (
        db.query(SignalAssessment)
        .join(Signal, SignalAssessment.signal_id == Signal.id)
        .filter(
            SignalAssessment.company_id == company.id,
            Signal.created_at >= since,
        )
        .order_by(Signal.created_at.desc())
        .limit(50)
        .all()
    )

    if not assessments:
        logger.info("No assessments found for %s in period %s — skipping summary", company.name, period_type)
        return None

    try:
        period_type_enum = PeriodType(period_type)
    except ValueError:
        period_type_enum = PeriodType.thirty_days

    previous = (
        db.query(CompetitorSummary)
        .filter_by(company_id=company.id, period_type=period_type_enum)
        .order_by(CompetitorSummary.created_at.desc())
        .first()
    )
    previous_summary_dict: dict | None = None
    if previous:
        previous_summary_dict = {
            "positioning_summary": previous.positioning_summary,
            "top_risks": previous.top_risks or [],
            "top_opportunities": previous.top_opportunities or [],
            "watchpoints": previous.watchpoints or [],
        }

    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
            "core_capabilities": ctx_record.core_capabilities or [],
            "strategic_priorities": ctx_record.strategic_priorities or [],
        }

    assessments_data = [
        {
            "signal_id": a.signal_id,
            "capability_primary": a.capability_primary,
            "signal_class": a.signal_class.value if a.signal_class else None,
            "evidence_strength": a.evidence_strength,
            "movement_strength": a.movement_strength.value if a.movement_strength else None,
            "assessment_summary": a.assessment_summary,
            "implication_for_us": a.implication_for_us,
            "gameplay_tags": a.gameplay_tags or [],
        }
        for a in assessments
    ]

    prompt = build_summary_prompt(
        company_name=company.name,
        period_label=_PERIOD_LABELS.get(period_type, f"last {days} days"),
        assessments=assessments_data,
        context=context,
        previous_summary=previous_summary_dict,
    )

    try:
        raw = call_llm(prompt, max_tokens=4096)
    except Exception as exc:
        logger.warning("call_llm raised for summary %s period %s: %s", company.name, period_type, exc)
        return None

    parsed = parse_summary_response(raw)

    if parsed is None:
        logger.warning("Summary parsing failed for %s period %s", company.name, period_type)
        return None

    scores = [a.movement_score for a in assessments if a.movement_score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    summary = CompetitorSummary(
        company_id=company.id,
        period_type=period_type_enum,
        period_start=(now - timedelta(days=days)).date(),
        period_end=now.date(),
        strategic_posture=parsed.strategic_posture,
        positioning_summary=parsed.positioning_summary,
        what_changed=parsed.what_changed,
        top_capabilities=parsed.top_capabilities,
        capability_assessment=parsed.capability_assessment,
        top_risks=parsed.top_risks,
        top_opportunities=parsed.top_opportunities,
        watchpoints=parsed.watchpoints,
        avg_movement_score=avg_score,
        signal_count=len(assessments),
        created_at=now,
        updated_at=now,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary
