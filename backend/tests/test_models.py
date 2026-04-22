import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import (
    Company,
    Source,
    Document,
    Signal,
    WeeklyDigest,
    InternalCompanyContext,
    DiscoveredPage,
)
from app.models.company import CompanyType
from app.models.source import SourceType
from app.models.signal import SignalType
from app.models.discovered_page import DiscoveredPageStatus


@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite:///./test_models.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    import os

    os.remove("test_models.db") if os.path.exists("test_models.db") else None


def test_company_creation(db):
    company = Company(name="ATOSS", slug="atoss", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    assert company.id is not None
    assert len(company.id) == 36


def test_source_belongs_to_company(db):
    company = Company(name="ATOSS", slug="atoss", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/news", source_type=SourceType.news
    )
    db.add(source)
    db.commit()
    assert source.company_id == company.id


def test_document_content_hash(db):
    company = Company(name="ATOSS", slug="atoss2", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/blog", source_type=SourceType.blog
    )
    db.add(source)
    db.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/blog/post-1",
        title="Test Post",
        content_markdown="# Test",
        content_hash="abc123",
    )
    db.add(doc)
    db.commit()
    assert doc.is_analysed is False


def test_signal_linked_to_document(db):
    company = Company(name="ATOSS", slug="atoss3", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/press",
        source_type=SourceType.press,
    )
    db.add(source)
    db.commit()
    doc = Document(
        source_id=source.id, url="https://atoss.com/press/1", content_hash="x"
    )
    db.add(doc)
    db.commit()
    signal = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="New AI Feature",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    db.add(signal)
    db.commit()
    assert signal.document_id == doc.id


def test_context_singleton_fields(db):
    ctx = InternalCompanyContext(
        company_name="WFM Corp",
        target_industries=["Retail", "Logistics"],
    )
    db.add(ctx)
    db.commit()
    assert ctx.target_industries == ["Retail", "Logistics"]


def test_discovered_page_model(db):
    from app.models.company import CompanyType
    from app.models.source import SourceType
    from datetime import datetime, timezone

    company = Company(name="Test", slug="test-dp-model", type=CompanyType.competitor)
    db.add(company)
    db.commit()

    source = Source(
        company_id=company.id, url="https://example.com/dp", source_type=SourceType.news
    )
    db.add(source)
    db.commit()

    page = DiscoveredPage(
        source_id=source.id,
        url="https://example.com/blog/article-1",
        title="Article 1",
        depth=1,
        status=DiscoveredPageStatus.new,
        content_hash="abc123",
        discovered_at=datetime.now(timezone.utc),
    )
    db.add(page)
    db.commit()
    db.refresh(page)

    assert page.id is not None
    assert page.status == DiscoveredPageStatus.new
    assert page.is_active is True
    assert page.source_id == source.id


def test_signal_assessment_model_exists():
    from app.models.signal_assessment import SignalAssessment
    assert SignalAssessment.__tablename__ == "signal_assessments"

def test_competitor_summary_model_exists():
    from app.models.competitor_summary import CompetitorSummary
    assert CompetitorSummary.__tablename__ == "competitor_summaries"
