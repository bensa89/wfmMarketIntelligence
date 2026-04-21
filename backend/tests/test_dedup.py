import pytest
from unittest.mock import patch, MagicMock
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.analyser.dedup import deduplicate_signals, build_dedup_prompt


def test_build_dedup_prompt_includes_signals():
    signals = [
        MagicMock(
            id="id1",
            title="AI Feature Launch",
            signal_type=SignalType.ai_announcement,
            topic="AI",
            summary="Company launched AI.",
            relevance_score=0.9,
        ),
        MagicMock(
            id="id2",
            title="New AI Feature",
            signal_type=SignalType.ai_announcement,
            topic="AI",
            summary="Similar AI launch.",
            relevance_score=0.7,
        ),
    ]
    prompt = build_dedup_prompt(signals)
    assert "id1" in prompt
    assert "id2" in prompt
    assert "AI Feature Launch" in prompt
    assert "New AI Feature" in prompt


def test_deduplicate_merges_duplicate_signals(db_session):
    company = Company(
        name="ATOSS", slug="atoss-dedup-merge", type=CompanyType.competitor
    )
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/dedup-merge",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc1 = Document(
        source_id=source.id, url="https://atoss.com/dedup-merge/1", content_hash="hm1"
    )
    doc2 = Document(
        source_id=source.id, url="https://atoss.com/dedup-merge/2", content_hash="hm2"
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    s1 = Signal(
        document_id=doc1.id,
        company_id=company.id,
        title="ATOSS launches AI scheduling",
        signal_type=SignalType.ai_announcement,
        topic="AI",
        summary="ATOSS released a new AI scheduling module for workforce management.",
        why_it_matters="Competes directly with our scheduling product.",
        relevance_score=0.9,
        confidence_score=0.85,
    )
    s2 = Signal(
        document_id=doc2.id,
        company_id=company.id,
        title="AI scheduling feature from ATOSS",
        signal_type=SignalType.ai_announcement,
        topic="AI",
        summary="ATOSS has introduced AI-powered scheduling capabilities.",
        why_it_matters="Threat to our market position in scheduling.",
        relevance_score=0.6,
        confidence_score=0.7,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    llm_response = f'{{"merge_groups": [["{s1.id}", "{s2.id}"]]}}'

    with patch("app.analyser.dedup.call_llm", return_value=llm_response):
        result = deduplicate_signals(db_session, company_id=company.id)

    assert result["merged_count"] == 1
    assert result["removed_ids"] == [s2.id]
    assert result["kept_signals"][0]["id"] == s1.id
    assert db_session.query(Signal).count() == 1
    kept = db_session.query(Signal).first()
    assert kept.title == "ATOSS launches AI scheduling"
    assert kept.relevance_score == 0.9


def test_deduplicate_no_duplicates_found(db_session):
    company = Company(name="ATOSS", slug="atoss-dedup-no", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/dedup-no",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id, url="https://atoss.com/dedup-no/1", content_hash="hn1"
    )
    db_session.add(doc)
    db_session.commit()

    s1 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="AI Feature",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    db_session.add(s1)
    db_session.commit()

    with patch("app.analyser.dedup.call_llm", return_value='{"merge_groups": []}'):
        result = deduplicate_signals(db_session, company_id=company.id)

    assert result["merged_count"] == 0
    assert result["removed_ids"] == []
    assert db_session.query(Signal).count() == 1


def test_deduplicate_keeps_better_summary_on_merge(db_session):
    company = Company(name="ATOSS", slug="atoss-dedup-sum", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/dedup-sum",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc1 = Document(
        source_id=source.id, url="https://atoss.com/dedup-sum/1", content_hash="hs1"
    )
    doc2 = Document(
        source_id=source.id, url="https://atoss.com/dedup-sum/2", content_hash="hs2"
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    s1 = Signal(
        document_id=doc1.id,
        company_id=company.id,
        title="Partner Deal",
        signal_type=SignalType.partnership,
        summary="Short.",
        why_it_matters="Brief note.",
        relevance_score=0.9,
        confidence_score=0.8,
    )
    s2 = Signal(
        document_id=doc2.id,
        company_id=company.id,
        title="Partnership Announcement",
        signal_type=SignalType.partnership,
        summary="A very detailed and comprehensive summary of the partnership with specific details about the agreement and market impact.",
        why_it_matters="Detailed explanation of why this matters for competitive positioning and strategic direction.",
        relevance_score=0.6,
        confidence_score=0.7,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    llm_response = f'{{"merge_groups": [["{s1.id}", "{s2.id}"]]}}'

    with patch("app.analyser.dedup.call_llm", return_value=llm_response):
        result = deduplicate_signals(db_session, company_id=company.id)

    kept = db_session.query(Signal).first()
    assert kept.title == "Partner Deal"
    assert kept.relevance_score == 0.9
    assert len(kept.summary) > len("Short.")
