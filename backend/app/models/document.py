import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    url = Column(String(2000), unique=True, nullable=False)
    title = Column(String(500), nullable=True)
    content_markdown = Column(Text, nullable=True)
    content_raw_html = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    content_hash = Column(String(64), nullable=True, index=True)
    is_analysed = Column(Boolean, default=False)

    source = relationship("Source", back_populates="documents")
    signals = relationship("Signal", back_populates="document")
