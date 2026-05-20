import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class CompetitorScorecard(Base):
    __tablename__ = "competitor_scorecards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    period_type = Column(String(10), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    overall_score = Column(Float, nullable=True)
    overall_trend = Column(String(10), nullable=True)
    dimension_scores = Column(JSON, nullable=True)
    top_capabilities = Column(JSON, nullable=True)
    top_moves = Column(JSON, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    watchpoints = Column(JSON, nullable=True)
    benchmark_position = Column(JSON, nullable=True)
    contributing_assessment_ids = Column(JSON, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)
    scorecard_version = Column(String(20), nullable=True)
    routing_version = Column(String(20), nullable=True)

    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("company_id", "period_type", "generated_at", name="uq_scorecard_snapshot"),
        Index("ix_scorecard_current", "company_id", "period_type", "is_current"),
    )
