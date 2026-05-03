import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models  # noqa: F401 — ensure all models are registered with Base
from app.database import Base
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.signal_assessment import SignalAssessment, SignalClass, VisibilityImpact, MovementStrength
from app.models.capability_benchmark import CompetitorCapabilityBenchmark
from app.benchmark.aggregation import BenchmarkAggregationService
from app.assessor.capabilities import CAPABILITY_KEYS


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def competitor(db):
    c = Company(id="comp-1", name="Acme WFM", slug="acme-wfm", type=CompanyType.competitor)
    db.add(c)
    db.commit()
    return c


@pytest.fixture
def signal_with_assessment(db, competitor):
    source = Source(
        id="src-1",
        company_id="comp-1",
        url="https://acme.com/blog",
        source_type=SourceType.blog,
    )
    db.add(source)
    db.commit()

    doc = Document(
        id="doc-1",
        source_id="src-1",
        url="https://acme.com/blog/ai-scheduling",
    )
    db.add(doc)
    db.commit()

    sig = Signal(
        id="sig-1",
        document_id="doc-1",
        company_id="comp-1",
        title="Acme launches AI scheduling",
        signal_type=SignalType.product_update,
        relevance_score=0.8,
        confidence_score=0.9,
    )
    db.add(sig)
    db.commit()

    today = date.today()
    assessment = SignalAssessment(
        id="sa-1",
        signal_id="sig-1",
        company_id="comp-1",
        capability_primary="shift_scheduling",
        signal_class=SignalClass.product_capability_move,
        evidence_strength=4,
        visibility_impact=VisibilityImpact.high,
        movement_score=70,
        movement_strength=MovementStrength.strong,
        confidence=0.85,
        gameplay_tags=["product", "ai"],
        created_at=today,
    )
    db.add(assessment)
    db.commit()
    return assessment


def test_recompute_company_creates_benchmarks(db, competitor, signal_with_assessment):
    service = BenchmarkAggregationService(db)
    results = service.recompute_company("comp-1", "30d")
    assert len(results) == len(CAPABILITY_KEYS)
    seeded = next(r for r in results if r.capability_key == "shift_scheduling")
    assert seeded.source_signal_count == 1
    assert seeded.relative_strength_score > 0


def test_recompute_company_upserts_on_second_call(db, competitor, signal_with_assessment):
    service = BenchmarkAggregationService(db)
    service.recompute_company("comp-1", "30d")
    service.recompute_company("comp-1", "30d")
    count = db.query(CompetitorCapabilityBenchmark).filter_by(company_id="comp-1", period_type="30d").count()
    assert count == len(CAPABILITY_KEYS)


def test_recompute_preserves_prev_score(db, competitor, signal_with_assessment):
    service = BenchmarkAggregationService(db)
    first = service.recompute_company("comp-1", "30d")
    original_score = next(r for r in first if r.capability_key == "shift_scheduling").relative_strength_score
    second = service.recompute_company("comp-1", "30d")
    seeded = next(r for r in second if r.capability_key == "shift_scheduling")
    assert seeded.prev_period_strength_score == original_score


def test_peer_rankings_computed(db, competitor, signal_with_assessment):
    c2 = Company(id="comp-2", name="Beta Corp", slug="beta-corp", type=CompanyType.competitor)
    db.add(c2)
    db.commit()
    service = BenchmarkAggregationService(db)
    service.recompute_all("30d")
    benchmarks = (
        db.query(CompetitorCapabilityBenchmark)
        .filter_by(capability_key="shift_scheduling", period_type="30d")
        .all()
    )
    ranks = [b.peer_rank for b in benchmarks]
    assert all(r is not None for r in ranks)
    assert sorted(ranks) == list(range(1, len(ranks) + 1))
