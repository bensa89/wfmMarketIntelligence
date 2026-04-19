import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class SearchResultStatus(str, enum.Enum):
    pending = "pending"
    fetched = "fetched"
    skipped = "skipped"
    error = "error"


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_run_id = Column(String(36), ForeignKey("search_runs.id"), nullable=False)
    title = Column(String(500), nullable=True)
    url = Column(String(2000), nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    snippet = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    relevance_score = Column(Float, nullable=True)
    processing_status = Column(
        SAEnum(SearchResultStatus),
        nullable=False,
        default=SearchResultStatus.pending,
    )
    linked_document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)

    run = relationship("SearchRun", back_populates="results")
    linked_document = relationship("Document", foreign_keys=[linked_document_id])
