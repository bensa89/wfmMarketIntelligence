import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from app.database import Base


class SignalType(str, enum.Enum):
    product_update = "product_update"
    ai_announcement = "ai_announcement"
    partnership = "partnership"
    positioning_change = "positioning_change"
    target_market_change = "target_market_change"
    event_or_thought_leadership = "event_or_thought_leadership"
    hiring_signal = "hiring_signal"
    other = "other"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    title = Column(String(500), nullable=False)
    signal_type = Column(SAEnum(SignalType), nullable=False)
    topic = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    why_it_matters = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    search_vector = Column(TSVECTOR, nullable=True)

    document = relationship("Document", back_populates="signals")
    company = relationship("Company", back_populates="signals")
