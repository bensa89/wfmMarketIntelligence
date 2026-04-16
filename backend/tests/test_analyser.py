import pytest
from unittest.mock import patch, MagicMock
from app.analyser.prompts import build_analysis_prompt
from app.analyser.parser import parse_llm_response, SignalData
from app.models.signal import SignalType


def test_build_prompt_includes_markdown_and_context():
    context = {
        "company_name": "WFM Corp",
        "target_industries": ["Retail"],
        "core_capabilities": ["WFM", "Analytics"],
        "differentiators": ["Real-time planning"],
    }
    prompt = build_analysis_prompt(
        markdown="## New AI Feature\nATOSS releases AI scheduling.",
        context=context,
    )
    assert "WFM Corp" in prompt
    assert "ATOSS releases AI scheduling" in prompt
    assert "Retail" in prompt
    assert "Real-time planning" in prompt


def test_parse_valid_llm_response():
    raw = """
    {
      "title": "ATOSS AI Scheduling Launch",
      "signal_type": "ai_announcement",
      "topic": "AI in WFM",
      "summary": "ATOSS launched a new AI scheduling module.",
      "why_it_matters": "Directly competes with our core capability.",
      "relevance_score": 0.9,
      "confidence_score": 0.85
    }
    """
    result = parse_llm_response(raw)
    assert isinstance(result, SignalData)
    assert result.title == "ATOSS AI Scheduling Launch"
    assert result.signal_type == SignalType.ai_announcement
    assert result.relevance_score == 0.9


def test_parse_llm_response_with_json_in_markdown_fence():
    raw = """
    Here is my analysis:
    ```json
    {
      "title": "Partnership Announced",
      "signal_type": "partnership",
      "topic": "Ecosystem",
      "summary": "New SAP partnership.",
      "why_it_matters": "SAP is a key integration target for us.",
      "relevance_score": 0.7,
      "confidence_score": 0.8
    }
    ```
    """
    result = parse_llm_response(raw)
    assert result.title == "Partnership Announced"
    assert result.signal_type == SignalType.partnership


def test_parse_invalid_response_returns_fallback():
    result = parse_llm_response("This is not JSON at all.")
    assert isinstance(result, SignalData)
    assert result.signal_type == SignalType.other
    assert result.relevance_score == 0.1


def test_analyse_document_creates_signal(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="ATOSS", slug="atoss-anal", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/anal", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/anal/1",
        content_markdown="## AI Feature",
        content_hash="h_anal",
    )
    db_session.add(doc)
    db_session.commit()

    mock_signal = SignalData(
        title="AI Feature",
        signal_type=SignalType.ai_announcement,
        topic="AI",
        summary="New AI feature.",
        why_it_matters="Competes with us.",
        relevance_score=0.9,
        confidence_score=0.85,
    )

    with patch(
        "app.analyser.pipeline.call_llm",
        return_value='{"title":"AI Feature","signal_type":"ai_announcement","topic":"AI","summary":"New AI feature.","why_it_matters":"Competes.","relevance_score":0.9,"confidence_score":0.85}',
    ):
        analyse_document(doc, company.id, db_session)

    signal = db_session.query(Signal).first()
    assert signal is not None
    assert signal.document_id == doc.id
    assert doc.is_analysed is True
