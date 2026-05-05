import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class CrawlRunStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class CrawlRunSourceStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class CrawlRunStep(str, enum.Enum):
    fetching = "fetching"
    extracting = "extracting"
    analysing = "analysing"
    discovering = "discovering"


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(
        SAEnum(CrawlRunStatus), nullable=False, default=CrawlRunStatus.running
    )
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    total_sources = Column(Integer, default=0)
    total_new = Column(Integer, default=0)
    total_skipped = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)

    sources = relationship(
        "CrawlRunSource", back_populates="crawl_run", cascade="all, delete-orphan"
    )


class CrawlRunSource(Base):
    __tablename__ = "crawl_run_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    crawl_run_id = Column(
        String(36), ForeignKey("crawl_runs.id"), nullable=False, index=True
    )
    source_id = Column(
        String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    url = Column(String(2000), nullable=False)
    status = Column(
        SAEnum(CrawlRunSourceStatus),
        nullable=False,
        default=CrawlRunSourceStatus.pending,
    )
    current_step = Column(SAEnum(CrawlRunStep), nullable=True)
    new_documents = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    error_message = Column(String(1000), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    fetch_ms = Column(Integer, nullable=True)
    extract_ms = Column(Integer, nullable=True)
    analyse_ms = Column(Integer, nullable=True)
    discover_ms = Column(Integer, nullable=True)

    crawl_run = relationship("CrawlRun", back_populates="sources")
    source = relationship("Source", back_populates="crawl_run_sources")
