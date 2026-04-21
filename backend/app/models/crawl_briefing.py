import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class CrawlBriefing(Base):
    __tablename__ = "crawl_briefings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    crawl_run_id = Column(String(36), ForeignKey("crawl_runs.id"), nullable=True)
    content = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
