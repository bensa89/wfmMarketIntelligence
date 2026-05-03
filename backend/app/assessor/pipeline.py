import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.analyser.client import call_llm
from app.assessor.prompts import ASSESSMENT_SYSTEM_PROMPT, build_assessment_prompt
from app.assessor.parser import parse_assessment_response, MAX_RETRIES
from app.assessor.rules import compute_movement_score, compute_movement_strength, map_signal_type_to_class
from app.assessor.capabilities import CAPABILITY_KEYS, CAPABILITIES
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.context import InternalCompanyContext

logger = logging.getLogger(__name__)


def assess_signal(signal: Signal, db: Session) -> SignalAssessment | None:
    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
            "core_capabilities": ctx_record.core_capabilities or [],
            "strategic_priorities": ctx_record.strategic_priorities or [],
            "differentiators": ctx_record.differentiators or [],
        }

    company_name = signal.company.name if signal.company else "Unknown"
    prompt = build_assessment_prompt(
        company_name=company_name,
        signal_type=signal.signal_type.value,
        title=signal.title,
        topic=signal.topic,
        summary=signal.summary,
        why_it_matters=signal.why_it_matters,
        relevance_score=signal.relevance_score or 0.0,
        confidence_score=signal.confidence_score or 0.0,
        context=context,
        capability_keys=CAPABILITY_KEYS,
    )

    parsed = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            raw = call_llm(prompt)
        except Exception as exc:
            logger.warning("call_llm raised on attempt %d/%d for signal %s: %s", attempt + 1, MAX_RETRIES + 1, signal.id, exc)
            continue
        parsed = parse_assessment_response(raw)
        if parsed is not None:
            break
        logger.warning(
            "Assessment parse failed (attempt %d/%d) for signal %s",
            attempt + 1, MAX_RETRIES + 1, signal.id,
        )

    if parsed is None:
        logger.warning("All assessment attempts failed for signal %s — skipping", signal.id)
        return None

    signal_class = parsed.signal_class or map_signal_type_to_class(signal.signal_type)
    capability_primary = parsed.capability_primary
    strategic_weight = (
        CAPABILITIES[capability_primary]["strategic_weight"]
        if capability_primary and capability_primary in CAPABILITIES
        else 5
    )

    movement_score = compute_movement_score(
        relevance_score=signal.relevance_score or 0.0,
        confidence_score=signal.confidence_score or 0.0,
        evidence_strength=parsed.evidence_strength or 3,
        visibility_impact=parsed.visibility_impact or "low",
        signal_class=signal_class,
    )
    movement_strength = compute_movement_strength(movement_score)

    existing = db.query(SignalAssessment).filter(SignalAssessment.signal_id == signal.id).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.capability_primary = capability_primary
        existing.capability_secondary = parsed.capability_secondary
        existing.signal_class = signal_class
        existing.evidence_strength = parsed.evidence_strength
        existing.visibility_impact = parsed.visibility_impact
        existing.strategic_weight = strategic_weight
        existing.movement_score = movement_score
        existing.movement_strength = movement_strength
        existing.confidence = parsed.confidence
        existing.strategic_intent_guess = parsed.strategic_intent_guess
        existing.gameplay_tags = parsed.gameplay_tags
        existing.assessment_summary = parsed.assessment_summary
        existing.implication_for_us = parsed.implication_for_us
        existing.watch_items = parsed.watch_items
        existing.updated_at = now
        db.commit()
        # Trigger benchmark recompute for this company (best-effort, non-blocking)
        try:
            from app.benchmark.aggregation import BenchmarkAggregationService
            BenchmarkAggregationService(db).recompute_company(existing.company_id, "30d")
        except Exception as exc:
            logger.warning("Benchmark recompute failed: %s", exc)
        return existing

    assessment = SignalAssessment(
        signal_id=signal.id,
        company_id=signal.company_id,
        capability_primary=capability_primary,
        capability_secondary=parsed.capability_secondary,
        signal_class=signal_class,
        evidence_strength=parsed.evidence_strength,
        visibility_impact=parsed.visibility_impact,
        strategic_weight=strategic_weight,
        movement_score=movement_score,
        movement_strength=movement_strength,
        confidence=parsed.confidence,
        strategic_intent_guess=parsed.strategic_intent_guess,
        gameplay_tags=parsed.gameplay_tags,
        assessment_summary=parsed.assessment_summary,
        implication_for_us=parsed.implication_for_us,
        watch_items=parsed.watch_items,
        created_at=now,
        updated_at=now,
    )
    db.add(assessment)
    db.commit()
    # Trigger benchmark recompute for this company (best-effort, non-blocking)
    try:
        from app.benchmark.aggregation import BenchmarkAggregationService
        BenchmarkAggregationService(db).recompute_company(assessment.company_id, "30d")
    except Exception as exc:
        logger.warning("Benchmark recompute failed: %s", exc)
    return assessment
