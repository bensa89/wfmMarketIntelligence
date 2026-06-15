import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON
from app.database import Base


class IntelligenceBriefing(Base):
    __tablename__ = "intelligence_briefings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    signal_count = Column(Integer, nullable=False, default=0)
    assessment_count = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    curated_risks = Column(JSON, nullable=True)
    curated_opportunities = Column(JSON, nullable=True)
    curated_watchpoints = Column(JSON, nullable=True)
