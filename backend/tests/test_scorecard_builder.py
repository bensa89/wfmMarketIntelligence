import pytest
from datetime import date, datetime, timezone
import app.models  # noqa


def _make_company(db, slug="acme"):
    from app.models.company import Company, CompanyType
    c = Company(name=slug.title(), slug=slug, type=CompanyType.competitor)
    db.add(c)
    db.commit()
    return c


def _make_signal(db, company):
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    s = Source(company_id=company.id, url=f"https://{company.slug}.com", source_type=SourceType.news)
    db.add(s)
    db.commit()
    doc = Document(source_id=s.id, url=f"https://{company.slug}.com/1")
    db.add(doc)
    db.commit()
    sig = Signal(
        document_id=doc.id, company_id=company.id,
        title="Test signal", signal_type=SignalType.product_update,
        relevance_score=0.9, confidence_score=0.85,
    )
    db.add(sig)
    db.commit()
    return sig


def _make_assessment(db, signal, company, **kwargs):
    from app.models.signal_assessment import SignalAssessment, SignalClass, VisibilityImpact, MovementStrength
    from datetime import datetime, timezone
    defaults = dict(
        signal_id=signal.id,
        company_id=company.id,
        capability_primary="ai_copilot",
        signal_class=SignalClass.product_capability_move,
        evidence_strength=4,
        visibility_impact=VisibilityImpact.high,
        movement_score=75,
        movement_strength=MovementStrength.strong,
        confidence=0.85,
        watch_items=["Watch adoption"],
        assessment_weight=1.0,
        valid_from=datetime.now(timezone.utc),
        dimension_targets={"capability_strength": 1.0, "market_impact": 1.0, "activity": 1.0},
        kpi_targets=["cap_weighted_score", "mkt_move_quality", "act_count_raw"],
        routing_version="v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    a = SignalAssessment(**defaults)
    db.add(a)
    db.commit()
    return a


def test_build_with_no_assessments_produces_null_scorecard(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "empty-co")
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert scorecard is not None
    assert scorecard.overall_score is None
    assert scorecard.is_current is True


def test_build_produces_scorecard_with_score(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "active-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert scorecard.overall_score is not None
    assert scorecard.overall_score > 0


def test_build_sets_is_current_and_flips_previous(db_session):
    from app.scorecard.builder import ScorecardBuilder
    from app.models.competitor_scorecard import CompetitorScorecard
    company = _make_company(db_session, "flip-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    ScorecardBuilder(db_session).build(company.id, "30d")
    ScorecardBuilder(db_session).build(company.id, "30d")
    current = db_session.query(CompetitorScorecard).filter_by(company_id=company.id, period_type="30d", is_current=True).all()
    assert len(current) == 1


def test_build_populates_watchpoints_from_all_assessments(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "watch-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company, watch_items=["Watch adoption", "Monitor pricing"])
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert "Watch adoption" in scorecard.watchpoints
    assert "Monitor pricing" in scorecard.watchpoints


def test_build_benchmark_position_single_competitor(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "solo-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert scorecard.benchmark_position["rank"] == 1
    assert scorecard.benchmark_position["total_competitors"] == 1


def test_build_top_moves_include_signal_id(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "moves-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    if scorecard.top_moves:
        assert "signal_id" in scorecard.top_moves[0]
