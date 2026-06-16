from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.document import Document
from app.models.signal import Signal
from app.models.context import InternalCompanyContext
from app.models.company import Company
import logging

from app.analyser.client import call_llm
from app.analyser.prompts import build_analysis_prompt, build_self_analysis_prompt
from app.analyser.parser import parse_llm_response
from app.models.company import CompanyType

logger = logging.getLogger(__name__)

_MIN_CONTENT_WORDS = 20
_MAX_AGE_DAYS = 365


def _build_context_dict(ctx_record) -> dict:
    if not ctx_record:
        return {}
    return {
        "company_name": ctx_record.company_name,
        "short_description": ctx_record.short_description,
        "target_industries": ctx_record.target_industries or [],
        "target_segments": ctx_record.target_segments or [],
        "core_capabilities": ctx_record.core_capabilities or [],
        "strategic_priorities": ctx_record.strategic_priorities or [],
        "differentiators": ctx_record.differentiators or [],
        "relevant_competitive_areas": ctx_record.relevant_competitive_areas or [],
        "non_focus_areas": ctx_record.non_focus_areas or [],
    }


def analyse_document(
    doc: Document,
    company_id: str,
    db: Session,
    preloaded_context: dict | None = None,
) -> None:
    if not doc.content_markdown:
        return

    word_count = len(doc.content_markdown.split())
    if word_count < _MIN_CONTENT_WORDS:
        logger.info(
            "Skipping analysis for doc %s: only %d words (minimum %d)",
            doc.id,
            word_count,
            _MIN_CONTENT_WORDS,
        )
        return

    existing_signal = db.query(Signal).filter(Signal.document_id == doc.id).first()
    if existing_signal:
        doc.is_analysed = True
        db.commit()
        return

    if doc.content_hash:
        duplicate = (
            db.query(Signal)
            .join(Document, Signal.document_id == Document.id)
            .filter(
                and_(
                    Document.content_hash == doc.content_hash,
                    Signal.company_id == company_id,
                )
            )
            .first()
        )
        if duplicate:
            logger.info(
                "Skipping analysis for doc %s: content_hash already analysed (duplicate of doc %s)",
                doc.id,
                duplicate.document_id,
            )
            doc.is_analysed = True
            db.commit()
            return

    # Checkpoint 1: skip if published_at from HTML is older than _MAX_AGE_DAYS
    age_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=_MAX_AGE_DAYS)
    if doc.published_at and doc.published_at < age_threshold:
        logger.info(
            "Skipping analysis for doc %s: published_at %s is older than %d days",
            doc.id,
            doc.published_at,
            _MAX_AGE_DAYS,
        )
        doc.is_analysed = True
        db.commit()
        return

    if preloaded_context is not None:
        context = preloaded_context
    else:
        ctx_record = db.query(InternalCompanyContext).first()
        context = _build_context_dict(ctx_record)

    logger.info(
        "Analysing doc %s — title=%r words=%d",
        doc.id,
        (doc.title or "")[:60],
        word_count,
    )

    # Detect if this document belongs to own_company → use adapted prompt
    company = db.query(Company).filter_by(id=company_id).first()
    is_own_company = company and company.type == CompanyType.own_company

    if is_own_company:
        logger.info(
            "Using self-analysis prompt for own_company doc %s [company=%s]",
            doc.id,
            company.name if company else company_id,
        )
        prompt = build_self_analysis_prompt(doc.content_markdown, context)
    else:
        from app.models.external_company_view import ExternalCompanyView
        ext_view_record = db.query(ExternalCompanyView).first()
        external_view = None
        if ext_view_record and ext_view_record.summary:
            external_view = {
                "key_messages": ext_view_record.key_messages or [],
                "observed_capabilities": ext_view_record.observed_capabilities or [],
                "observed_differentiators": ext_view_record.observed_differentiators or [],
                "observed_target_markets": ext_view_record.observed_target_markets or [],
                "tone_and_positioning": ext_view_record.tone_and_positioning,
            }
            logger.debug(
                "ExternalCompanyView injected into competitor analysis for doc %s [signals_used=%d]",
                doc.id,
                ext_view_record.signal_count_used or 0,
            )
        else:
            logger.debug(
                "No ExternalCompanyView available for doc %s — using standard prompt",
                doc.id,
            )
        prompt = build_analysis_prompt(doc.content_markdown, context, external_view=external_view)
    raw_response = call_llm(prompt, caller="analyser:signal-extraction")
    signal_data = parse_llm_response(raw_response)

    if signal_data is None:
        logger.info(
            "Skipping signal creation for doc %s: LLM unable to analyze content",
            doc.id,
        )
        doc.is_analysed = True
        db.commit()
        return

    # Checkpoint 2: skip if LLM-detected published_at is older than _MAX_AGE_DAYS
    if signal_data.published_at and signal_data.published_at < age_threshold:
        logger.info(
            "Skipping signal for doc %s: LLM-detected published_at %s is older than %d days",
            doc.id,
            signal_data.published_at,
            _MAX_AGE_DAYS,
        )
        doc.is_analysed = True
        db.commit()
        return

    signal = Signal(
        document_id=doc.id,
        company_id=company_id,
        title=signal_data.title,
        signal_type=signal_data.signal_type,
        topic=signal_data.topic,
        summary=signal_data.summary,
        why_it_matters=signal_data.why_it_matters,
        relevance_score=signal_data.relevance_score,
        confidence_score=signal_data.confidence_score,
        published_at=signal_data.published_at or doc.published_at or doc.crawled_at,
        event_date=signal_data.event_date,
        event_name=signal_data.event_name,
        event_type=signal_data.event_type,
        event_location=signal_data.event_location,
    )
    db.add(signal)

    doc.is_analysed = True
    db.commit()
    db.refresh(signal)

    logger.info(
        "Signal created — type=%s title=%r relevance=%.2f event_date=%s",
        signal_data.signal_type,
        signal_data.title[:60],
        signal_data.relevance_score or 0.0,
        signal_data.event_date or "none",
    )

    # Skip assessment for own_company signals — the assessor is designed for competitor intelligence
    # and would generate semantically incorrect implication_for_us fields for own content.
    if not is_own_company:
        try:
            from app.config import settings
            if (signal.relevance_score or 0.0) >= settings.assessment_threshold:
                from app.assessor.pipeline import assess_signal
                logger.info("Triggering assessment for signal %s (relevance=%.2f)", signal.id, signal.relevance_score)
                assess_signal(signal, db)
        except Exception as e:
            logger.warning("Assessment hook failed for signal %s: %s", signal.id, e)
    else:
        logger.debug("Skipping assessment for own_company signal %s", signal.id)
