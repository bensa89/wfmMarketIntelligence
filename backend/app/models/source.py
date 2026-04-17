import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class SourceType(str, enum.Enum):
    news = "news"
    blog = "blog"
    product = "product"
    press = "press"
    jobs = "jobs"


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    url = Column(String(2000), unique=True, nullable=False)
    label = Column(String(255), nullable=True)
    source_type = Column(SAEnum(SourceType), nullable=False, default=SourceType.news)
    is_active = Column(Boolean, default=True)
    last_crawled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="sources")
    documents = relationship("Document", back_populates="source")
    discovered_pages = relationship("DiscoveredPage", back_populates="source")
