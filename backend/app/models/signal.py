import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    types,
)
from sqlalchemy.dialects.postgresql import TSVECTOR as PG_TSVECTOR
from sqlalchemy.orm import relationship
from app.database import Base


class TSVectorType(types.TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_TSVECTOR)
        return dialect.type_descriptor(Text)


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
    search_vector = Column(TSVectorType, nullable=True)

    document = relationship("Document", back_populates="signals")
    company = relationship("Company", back_populates="signals")
