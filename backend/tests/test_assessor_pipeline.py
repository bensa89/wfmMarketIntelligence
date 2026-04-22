import json
from unittest.mock import patch
import pytest
import app.models  # noqa: F401 — ensure all models are registered with Base before create_all


def _make_assessment_json(**overrides):
    base = {
        "capability_primary": "ai_copilot",
        "capability_secondary": ["shift_scheduling"],
        "signal_class": "product_capability_move",
        "evidence_strength": 4,
        "visibility_impact": "high",
        "strategic_intent_guess": "AI-first positioning.",
        "gameplay_tags": ["ai-narrative"],
        "assessment_summary": "Launched new AI module.",
        "implication_for_us": "Direct competition.",
        "watch_items": ["Monitor adoption"],
        "confidence": 0.85,
    }
    base.update(overrides)
    return json.dumps(base)


def test_assess_signal_creates_assessment(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    company = Company(name="ATOSS", slug="atoss-assess", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/assess", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/assess/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="AI Feature", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.85,
    )
    db_session.add(signal)
    db_session.commit()

    with patch("app.assessor.pipeline.call_llm", return_value=_make_assessment_json()):
        assess_signal(signal, db_session)

    assessment = db_session.query(SignalAssessment).filter(SignalAssessment.signal_id == signal.id).first()
    assert assessment is not None
    assert assessment.capability_primary == "ai_copilot"
    assert assessment.movement_score is not None
    assert assessment.movement_strength is not None


def test_assess_signal_overwrites_existing(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    company = Company(name="ATOSS2", slug="atoss-reassess", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/reassess", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/reassess/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="AI Feature 2", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.85,
    )
    db_session.add(signal)
    db_session.commit()

    with patch("app.assessor.pipeline.call_llm", return_value=_make_assessment_json(capability_primary="demand_forecasting")):
        assess_signal(signal, db_session)

    with patch("app.assessor.pipeline.call_llm", return_value=_make_assessment_json(capability_primary="shift_scheduling")):
        assess_signal(signal, db_session)

    assessments = db_session.query(SignalAssessment).filter(SignalAssessment.signal_id == signal.id).all()
    assert len(assessments) == 1
    assert assessments[0].capability_primary == "shift_scheduling"


def test_assess_signal_handles_llm_failure_gracefully(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    company = Company(name="ATOSS3", slug="atoss-fail", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/fail", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/fail/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="AI Feature 3", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.85,
    )
    db_session.add(signal)
    db_session.commit()

    with patch("app.assessor.pipeline.call_llm", return_value="not json"):
        assess_signal(signal, db_session)

    assert db_session.query(SignalAssessment).count() == 0


def test_assess_signal_uses_fallback_signal_class(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal
    import json

    company = Company(name="FallbackCo", slug="fallback-co", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://fallback.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://fallback.com/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="Partnership news", signal_type=SignalType.partnership,
        relevance_score=0.8, confidence_score=0.7,
    )
    db_session.add(signal)
    db_session.commit()

    # LLM returns no signal_class (null)
    llm_json = json.dumps({
        "capability_primary": "integration_hub",
        "signal_class": None,  # LLM omits this
        "evidence_strength": 3,
        "visibility_impact": "medium",
        "confidence": 0.7,
    })
    with patch("app.assessor.pipeline.call_llm", return_value=llm_json):
        result = assess_signal(signal, db_session)

    assert result is not None
    # partnership → ecosystem_move via map_signal_type_to_class
    assert result.signal_class == "ecosystem_move"


def test_generate_competitor_summary_creates_record(db_session):
    import json
    from datetime import date
    from unittest.mock import patch
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment, MovementStrength, SignalClass, VisibilityImpact
    from app.models.competitor_summary import CompetitorSummary
    from app.assessor.summarizer import generate_competitor_summary

    company = Company(name="SumCo", slug="sumco", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://sumco.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://sumco.com/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="Big Move", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.8,
    )
    db_session.add(signal)
    db_session.commit()
    assessment = SignalAssessment(
        signal_id=signal.id, company_id=company.id,
        capability_primary="ai_copilot",
        signal_class=SignalClass.product_capability_move,
        evidence_strength=4,
        visibility_impact=VisibilityImpact.high,
        movement_score=82, movement_strength=MovementStrength.market_shaping,
        assessment_summary="Major AI move.",
    )
    db_session.add(assessment)
    db_session.commit()

    summary_json = json.dumps({
        "strategic_posture": "aggressive_expansion",
        "positioning_summary": "Moving aggressively into AI.",
        "top_capabilities": ["ai_copilot"],
        "capability_assessment": [{"key": "ai_copilot", "label": "AI Copilot", "activity_level": "high", "notes": "Flagship feature."}],
        "top_risks": ["AI feature parity risk"],
        "top_opportunities": ["Partner with adjacent vendors"],
        "watchpoints": ["Track AI copilot adoption"],
    })

    with patch("app.assessor.summarizer.call_llm", return_value=summary_json):
        result = generate_competitor_summary(company, "30d", db_session)

    assert result is not None
    assert result.strategic_posture == "aggressive_expansion"
    assert db_session.query(CompetitorSummary).count() == 1
