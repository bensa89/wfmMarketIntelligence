from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.document import Document
from app.models.signal import Signal
from app.models.context import InternalCompanyContext
import logging

from app.analyser.client import call_llm
from app.analyser.prompts import build_analysis_prompt
from app.analyser.parser import parse_llm_response

logger = logging.getLogger(__name__)

_MIN_CONTENT_WORDS = 50
_MAX_AGE_DAYS = 365


def analyse_document(doc: Document, company_id: str, db: Session) -> None:
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
    age_threshold = datetime.utcnow() - timedelta(days=_MAX_AGE_DAYS)
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

    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
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

    prompt = build_analysis_prompt(doc.content_markdown, context)
    raw_response = call_llm(prompt)
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
    )
    db.add(signal)

    doc.is_analysed = True
    db.commit()
