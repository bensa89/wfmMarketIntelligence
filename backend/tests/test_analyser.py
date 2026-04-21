import pytest
from unittest.mock import patch, MagicMock
from app.analyser.prompts import build_analysis_prompt
from app.analyser.parser import parse_llm_response, SignalData, _is_unable_to_analyze
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


def test_parse_invalid_response_returns_none():
    result = parse_llm_response("This is not JSON at all.")
    assert result is None


def test_parse_unable_to_analyze_returns_none():
    raw = '{"title": "Unable to analyze - no content provided", "signal_type": "other", "topic": null, "summary": null, "why_it_matters": null, "relevance_score": 0.1, "confidence_score": 0.1}'
    result = parse_llm_response(raw)
    assert result is None


def test_parse_unable_to_analyze_plain_text_returns_none():
    result = parse_llm_response(
        "I cannot analyze this content as there is no content provided."
    )
    assert result is None


def test_is_unable_to_analyze():
    assert _is_unable_to_analyze("Unable to analyze - no content provided")
    assert _is_unable_to_analyze("Cannot analyze this document")
    assert _is_unable_to_analyze("There is no content to analyze here")
    assert _is_unable_to_analyze("Insufficient content for analysis")
    assert not _is_unable_to_analyze("New AI feature announced by competitor")


def test_analyse_document_skips_short_content(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="ATOSS", slug="atoss-short", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/short",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/short/1",
        content_markdown="Just a few words here",
        content_hash="h_short",
    )
    db_session.add(doc)
    db_session.commit()

    with patch("app.analyser.pipeline.call_llm") as mock_llm:
        analyse_document(doc, company.id, db_session)
        mock_llm.assert_not_called()

    assert db_session.query(Signal).count() == 0


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
        content_markdown="## AI Feature\n" + "ATOSS releases AI scheduling. " * 20,
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


def test_analyse_document_skips_if_signal_already_exists(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.analyser.pipeline import analyse_document

    company = Company(name="ATOSS", slug="atoss-dedup", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/dedup",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/dedup/1",
        content_markdown="## AI Feature\n" + "Duplicate content for testing. " * 20,
        content_hash="h_dedup",
    )
    db_session.add(doc)
    db_session.commit()

    existing_signal = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="Existing Signal",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.8,
    )
    db_session.add(existing_signal)
    db_session.commit()

    with patch(
        "app.analyser.pipeline.call_llm",
        return_value='{"title":"Duplicate","signal_type":"ai_announcement","topic":"AI","summary":"Dup.","why_it_matters":"Dup.","relevance_score":0.7,"confidence_score":0.7}',
    ):
        analyse_document(doc, company.id, db_session)

    assert db_session.query(Signal).count() == 1
    assert db_session.query(Signal).first().title == "Existing Signal"
    assert doc.is_analysed is True


def test_analyse_document_skips_if_published_at_older_than_1_year(db_session):
    from datetime import datetime, timedelta
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="OldCo", slug="oldco-age", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://oldco.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://oldco.com/blog/old-post",
        content_markdown="## Old Article\n" + "Some old content. " * 20,
        content_hash="h_old",
        published_at=datetime.utcnow() - timedelta(days=400),
    )
    db_session.add(doc)
    db_session.commit()

    with patch("app.analyser.pipeline.call_llm") as mock_llm:
        analyse_document(doc, company.id, db_session)
        mock_llm.assert_not_called()

    assert db_session.query(Signal).count() == 0
    assert doc.is_analysed is True


def test_analyse_document_skips_if_llm_published_at_older_than_1_year(db_session):
    from datetime import datetime, timedelta
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="OldCo2", slug="oldco-llm", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://oldco2.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://oldco2.com/blog/mystery-post",
        content_markdown="## Undated Article\n" + "Content without HTML date. " * 20,
        content_hash="h_mystery",
        published_at=None,  # no date from HTML
    )
    db_session.add(doc)
    db_session.commit()

    old_date = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
    llm_response = (
        f'{{"title":"Old News","signal_type":"other","topic":"Old","summary":"Old.",'
        f'"why_it_matters":"Stale.","relevance_score":0.5,"confidence_score":0.5,'
        f'"published_at":"{old_date}"}}'
    )

    with patch("app.analyser.pipeline.call_llm", return_value=llm_response):
        analyse_document(doc, company.id, db_session)

    assert db_session.query(Signal).count() == 0
    assert doc.is_analysed is True


def test_analyse_document_proceeds_if_published_at_recent(db_session):
    from datetime import datetime, timedelta
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="NewCo", slug="newco-age", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://newco.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://newco.com/blog/new-post",
        content_markdown="## Fresh Article\n" + "Recent content here. " * 20,
        content_hash="h_new_age",
        published_at=datetime.utcnow() - timedelta(days=30),
    )
    db_session.add(doc)
    db_session.commit()

    llm_response = '{"title":"Fresh News","signal_type":"other","topic":"Fresh","summary":"New.","why_it_matters":"Relevant.","relevance_score":0.6,"confidence_score":0.7}'

    with patch("app.analyser.pipeline.call_llm", return_value=llm_response):
        analyse_document(doc, company.id, db_session)

    assert db_session.query(Signal).count() == 1
