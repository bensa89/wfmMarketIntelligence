import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, SmallInteger, DateTime, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class SignalClass(str, enum.Enum):
    product_capability_move = "product_capability_move"
    positioning_move = "positioning_move"
    ecosystem_move = "ecosystem_move"
    thought_leadership_signal = "thought_leadership_signal"
    hiring_signal = "hiring_signal"
    weak_signal = "weak_signal"
    market_expansion_move = "market_expansion_move"


class VisibilityImpact(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class MovementStrength(str, enum.Enum):
    weak = "weak"
    relevant = "relevant"
    strong = "strong"
    market_shaping = "market_shaping"


class SignalAssessment(Base):
    __tablename__ = "signal_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id = Column(String(36), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    capability_primary = Column(String(100), nullable=True)
    capability_secondary = Column(JSON, nullable=True)
    signal_class = Column(SAEnum(SignalClass), nullable=True)
    evidence_strength = Column(SmallInteger, nullable=True)
    visibility_impact = Column(SAEnum(VisibilityImpact), nullable=True)
    strategic_weight = Column(SmallInteger, nullable=True)
    movement_score = Column(SmallInteger, nullable=True)
    movement_strength = Column(SAEnum(MovementStrength), nullable=True)
    confidence = Column(Float, nullable=True)
    strategic_intent_guess = Column(Text, nullable=True)
    gameplay_tags = Column(JSON, nullable=True)
    assessment_summary = Column(Text, nullable=True)
    implication_for_us = Column(Text, nullable=True)
    watch_items = Column(JSON, nullable=True)
    dimension_targets = Column(JSON, nullable=True)   # {dimension_key: dimension_modifier}
    kpi_targets = Column(JSON, nullable=True)          # [kpi_id, ...]
    assessment_weight = Column(Float, nullable=True, default=1.0)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    buyer_relevance = Column(SmallInteger, nullable=True)
    routing_version = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    signal = relationship("Signal", back_populates="assessment", uselist=False)
    company = relationship("Company")
