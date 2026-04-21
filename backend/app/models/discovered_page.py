import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base


class DiscoveredPageStatus(str, enum.Enum):
    new = "new"
    known = "known"
    changed = "changed"
    ignored = "ignored"


class DiscoveredPage(Base):
    __tablename__ = "discovered_pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False, index=True)
    url = Column(String(2000), unique=True, nullable=False)
    title = Column(String(500), nullable=True)
    depth = Column(Integer, nullable=False, default=1)
    status = Column(
        SAEnum(DiscoveredPageStatus), nullable=False, default=DiscoveredPageStatus.new
    )
    content_hash = Column(String(64), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_crawled_at = Column(DateTime, nullable=True)
    last_changed_at = Column(DateTime, nullable=True)
    last_signal_relevance = Column(Float, nullable=True)

    source = relationship("Source", back_populates="discovered_pages")
