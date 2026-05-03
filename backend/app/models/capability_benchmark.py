import enum
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Column, String, Integer, SmallInteger, Float, Text, Date, DateTime,
    ForeignKey, UniqueConstraint, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base


class PeriodTypeEnum(str, enum.Enum):
    d30 = "30d"
    d90 = "90d"
    d180 = "180d"


class BenchmarkTierEnum(str, enum.Enum):
    leader = "leader"
    strong = "strong"
    emerging = "emerging"
    weakly_evidenced = "weakly_evidenced"


class CompetitorCapabilityBenchmark(Base):
    __tablename__ = "competitor_capability_benchmarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    capability_key = Column(String(100), nullable=False)
    period_type = Column(SAEnum(PeriodTypeEnum, name="periodtypeenum", create_constraint=True), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    capability_depth_score = Column(SmallInteger, nullable=False, default=0)
    execution_momentum_score = Column(SmallInteger, nullable=False, default=0)
    market_proof_score = Column(SmallInteger, nullable=False, default=0)
    strategic_focus_score = Column(SmallInteger, nullable=False, default=0)
    evidence_coverage_score = Column(SmallInteger, nullable=False, default=0)

    relative_strength_score = Column(Integer, nullable=False, default=0)
    prev_period_strength_score = Column(Integer, nullable=True)
    strength_delta = Column(Integer, nullable=True)
    peer_rank = Column(Integer, nullable=True)
    peer_percentile = Column(Float, nullable=True)
    tier = Column(SAEnum(BenchmarkTierEnum, name="benchmarktiereneum", create_constraint=True), nullable=False, default=BenchmarkTierEnum.weakly_evidenced)
    confidence = Column(Float, nullable=False, default=0.0)

    source_signal_count = Column(Integer, nullable=False, default=0)
    summary_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    company = relationship("Company", backref="capability_benchmarks")

    __table_args__ = (
        UniqueConstraint(
            "company_id", "capability_key", "period_type",
            name="uq_benchmark_company_cap_period",
        ),
        Index("ix_benchmark_company", "company_id"),
        Index("ix_benchmark_cap_period", "capability_key", "period_type"),
        Index("ix_benchmark_period_tier", "period_type", "tier"),
    )
