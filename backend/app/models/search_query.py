import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_text = Column(String(500), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    topic = Column(String(255), nullable=True)
    search_intent = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    runs = relationship("SearchRun", back_populates="query")
    company = relationship("Company", foreign_keys=[company_id])
