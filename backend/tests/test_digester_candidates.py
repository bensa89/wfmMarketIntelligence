import pytest
from datetime import date, datetime, timezone
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.signal_assessment import SignalAssessment
from app.digester.sections import SECTIONS
from app.digester.candidates import query_candidates, build_candidate_dict


@pytest.fixture
def seeded(db_session):
    company = Company(name="Acme", slug="acme", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    source = Source(company_id=company.id, url="https://acme.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()

    doc = Document(source_id=source.id, url="https://acme.com/article", title="Acme News", content_hash="h1")
    db_session.add(doc)
    db_session.commit()

    signal = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="Acme AI Launch",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.8,
        created_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(signal)
    db_session.commit()

    assessment = SignalAssessment(
        signal_id=signal.id,
        company_id=company.id,
        movement_score=70,
        assessment_summary="Big move.",
        implication_for_us="We need to respond.",
        strategic_intent_guess="Capturing SMB market.",
    )
    db_session.add(assessment)
    db_session.commit()

    return company, source, doc, signal, assessment


def test_query_candidates_returns_signal_in_week(db_session, seeded):
    _, _, _, signal, _ = seeded
    section = next(s for s in SECTIONS if s.key == "new_trends")
    results = query_candidates(db_session, section, date(2026, 5, 5), date(2026, 5, 11))
    assert any(r.id == signal.id for r in results)


def test_query_candidates_excludes_signal_outside_week(db_session, seeded):
    section = next(s for s in SECTIONS if s.key == "new_trends")
    results = query_candidates(db_session, section, date(2026, 4, 1), date(2026, 4, 7))
    assert results == []


def test_query_candidates_filters_by_signal_type(db_session, seeded):
    _, _, _, signal, _ = seeded
    # ai_announcement is in new_trends, not in market_movements, and market_movements
    # has no source-type fallback filter — so it must not match here.
    section_news = next(s for s in SECTIONS if s.key == "new_trends")
    section_other = next(s for s in SECTIONS if s.key == "market_movements")
    assert any(r.id == signal.id for r in query_candidates(db_session, section_news, date(2026, 5, 5), date(2026, 5, 11)))
    assert not any(r.id == signal.id for r in query_candidates(db_session, section_other, date(2026, 5, 5), date(2026, 5, 11)))


def test_query_candidates_excludes_given_signal_ids(db_session, seeded):
    _, _, _, signal, _ = seeded
    section = next(s for s in SECTIONS if s.key == "new_trends")
    results = query_candidates(db_session, section, date(2026, 5, 5), date(2026, 5, 11), excluded_signal_ids={signal.id})
    assert not any(r.id == signal.id for r in results)


def test_query_candidates_competitors_section_uses_source_type_or_filter(db_session, seeded):
    _, _, _, signal, _ = seeded
    # signal_type is ai_announcement (not in competitors.signal_types), but the seeded
    # source is SourceType.news -> the OR(signal_type, source_type) filter should still match.
    section = next(s for s in SECTIONS if s.key == "competitors")
    results = query_candidates(db_session, section, date(2026, 5, 5), date(2026, 5, 11))
    assert any(r.id == signal.id for r in results)


def test_query_candidates_competitors_section_excludes_market_source(db_session):
    # competitor_only=True must exclude signals from market_source companies even
    # though their source_type would otherwise satisfy the OR-source-type-filter.
    market_company = Company(name="Industry Watch", slug="industry-watch", type=CompanyType.market_source)
    db_session.add(market_company)
    db_session.commit()

    source = Source(company_id=market_company.id, url="https://industry-watch.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()

    doc = Document(source_id=source.id, url="https://industry-watch.com/article", content_hash="h_market")
    db_session.add(doc)
    db_session.commit()

    signal = Signal(
        document_id=doc.id,
        company_id=market_company.id,
        title="Market Trend",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.7,
        created_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(signal)
    db_session.commit()

    section = next(s for s in SECTIONS if s.key == "competitors")
    results = query_candidates(db_session, section, date(2026, 5, 5), date(2026, 5, 11))
    assert not any(r.id == signal.id for r in results)


def test_build_candidate_dict_structure(db_session, seeded):
    _, _, doc, signal, assessment = seeded
    section = next(s for s in SECTIONS if s.key == "new_trends")
    results = query_candidates(db_session, section, date(2026, 5, 5), date(2026, 5, 11))
    assert results
    candidate = build_candidate_dict(results[0])
    assert candidate["signal_id"] == signal.id
    assert candidate["company"] == "Acme"
    assert candidate["title"] == "Acme AI Launch"
    assert candidate["assessment_summary"] == "Big move."
    assert candidate["implication_for_us"] == "We need to respond."
    assert candidate["source_url"] == "https://acme.com/article"
    assert candidate["source_domain"] == "acme.com"
    assert candidate["source_title"] == "Acme News"
