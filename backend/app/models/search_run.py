import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SearchRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class SearchRun(Base):
    __tablename__ = "search_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_query_id = Column(
        String(36), ForeignKey("search_queries.id"), nullable=False
    )
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(
        SAEnum(SearchRunStatus), nullable=False, default=SearchRunStatus.pending
    )
    result_count = Column(Integer, nullable=True)
    error_message = Column(String(1000), nullable=True)

    query = relationship("SearchQuery", back_populates="runs")
    results = relationship("SearchResult", back_populates="run")
