import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, Date
from sqlalchemy.types import JSON
from app.database import Base


class WeeklyDigest(Base):
    __tablename__ = "weekly_digests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    summary = Column(Text, nullable=True)
    key_signals = Column(JSON, default=list)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_published = Column(Boolean, default=False)
