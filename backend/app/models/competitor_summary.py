import uuid
import enum
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Text, Float, Integer, Date, DateTime, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class PeriodType(str, enum.Enum):
    seven_days = "7d"
    thirty_days = "30d"
    ninety_days = "90d"
    quarter = "quarter"


class CompetitorSummary(Base):
    __tablename__ = "competitor_summaries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    period_type = Column(SAEnum(PeriodType), nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    strategic_posture = Column(String(200), nullable=True)
    positioning_summary = Column(Text, nullable=True)
    top_capabilities = Column(JSON, nullable=True)
    capability_assessment = Column(JSON, nullable=True)
    top_risks = Column(JSON, nullable=True)
    top_opportunities = Column(JSON, nullable=True)
    watchpoints = Column(JSON, nullable=True)
    what_changed = Column(Text, nullable=True)
    avg_movement_score = Column(Float, nullable=True)
    signal_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company")
