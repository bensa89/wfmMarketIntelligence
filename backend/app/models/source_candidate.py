import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.source import SourceType


class SourceCandidateStatus(str, enum.Enum):
    candidate = "candidate"
    approved = "approved"
    rejected = "rejected"
    monitored = "monitored"


class SourceCandidate(Base):
    __tablename__ = "source_candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String(2000), nullable=False)
    domain = Column(String(255), nullable=False)
    title = Column(String(500), nullable=True)
    snippet = Column(Text, nullable=True)
    found_via_query = Column(String(500), nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    source_type_guess = Column(SAEnum(SourceType), nullable=True)
    relevance_score = Column(Float, nullable=True)
    status = Column(
        SAEnum(SourceCandidateStatus),
        nullable=False,
        default=SourceCandidateStatus.candidate,
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", foreign_keys=[company_id])
