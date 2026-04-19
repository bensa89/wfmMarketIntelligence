from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.signal import Signal
from app.models.context import InternalCompanyContext
from app.analyser.client import call_llm
from app.analyser.prompts import build_analysis_prompt
from app.analyser.parser import parse_llm_response


def analyse_document(doc: Document, company_id: str, db: Session) -> None:
    if not doc.content_markdown:
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
