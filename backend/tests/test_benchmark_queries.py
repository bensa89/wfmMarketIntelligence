import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models  # noqa: F401
from app.database import Base
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.signal_assessment import SignalAssessment, SignalClass
from app.benchmark.queries import BenchmarkQueryService


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
def seeded_db(db):
    company = Company(id="comp-1", name="Acme WFM", slug="acme-wfm", type=CompanyType.competitor)
    db.add(company)
    source = Source(id="src-1", company_id="comp-1", url="https://acme.com", source_type=SourceType.blog)
    db.add(source)
    doc = Document(id="doc-1", source_id="src-1", url="https://acme.com/post")
    db.add(doc)
    sig = Signal(id="sig-1", document_id="doc-1", company_id="comp-1", title="Acme launches AI scheduling", signal_type=SignalType.product_update)
    db.add(sig)
    assessment = SignalAssessment(
        id="asmt-1",
        signal_id="sig-1",
        company_id="comp-1",
        capability_primary="ai_scheduling",
        signal_class=SignalClass.product_capability_move,
        movement_score=75,
        created_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.commit()
    return db


def test_get_capability_assessments_returns_matching_assessments(seeded_db):
    svc = BenchmarkQueryService(seeded_db)
    result = svc.get_capability_assessments("acme-wfm", "ai_scheduling", "30d")

    assert result.capability_key == "ai_scheduling"
    assert result.total_count == 1
    assert len(result.assessments) == 1
    item = result.assessments[0]
    assert item.assessment_id == "asmt-1"
    assert item.signal_id == "sig-1"
    assert item.title == "Acme launches AI scheduling"
    assert item.movement_score == 75
    assert item.signal_class == "product_capability_move"


def test_get_capability_assessments_wrong_capability_returns_empty(seeded_db):
    svc = BenchmarkQueryService(seeded_db)
    result = svc.get_capability_assessments("acme-wfm", "workforce_management", "30d")

    assert result.total_count == 0
    assert result.assessments == []


def test_get_capability_assessments_unknown_slug_raises(seeded_db):
    svc = BenchmarkQueryService(seeded_db)
    with pytest.raises(ValueError, match="Company not found"):
        svc.get_capability_assessments("does-not-exist", "ai_scheduling", "30d")


def test_get_capability_assessments_ordered_by_movement_score_desc(db):
    company = Company(id="comp-2", name="Beta", slug="beta", type=CompanyType.competitor)
    db.add(company)
    source = Source(id="src-2", company_id="comp-2", url="https://beta.com", source_type=SourceType.blog)
    db.add(source)
    doc = Document(id="doc-2", source_id="src-2", url="https://beta.com/p")
    db.add(doc)

    for i, score in enumerate([30, 90, 60]):
        sig = Signal(id=f"sig-{i}", document_id="doc-2", company_id="comp-2", title=f"Signal {i}", signal_type=SignalType.product_update)
        db.add(sig)
        asmt = SignalAssessment(
            id=f"asmt-{i}",
            signal_id=f"sig-{i}",
            company_id="comp-2",
            capability_primary="ai_scheduling",
            movement_score=score,
            created_at=datetime.now(timezone.utc),
        )
        db.add(asmt)
    db.commit()

    svc = BenchmarkQueryService(db)
    result = svc.get_capability_assessments("beta", "ai_scheduling", "30d")

    scores = [a.movement_score for a in result.assessments]
    assert scores == sorted(scores, reverse=True)
