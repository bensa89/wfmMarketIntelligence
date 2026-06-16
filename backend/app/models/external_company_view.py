import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.types import JSON
from app.database import Base


class ExternalCompanyView(Base):
    __tablename__ = "external_company_view"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    summary = Column(Text, nullable=True)
    key_messages = Column(JSON, default=list)
    observed_capabilities = Column(JSON, default=list)
    observed_differentiators = Column(JSON, default=list)
    observed_target_markets = Column(JSON, default=list)
    tone_and_positioning = Column(Text, nullable=True)
    signal_count_used = Column(Integer, default=0)
    generated_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
