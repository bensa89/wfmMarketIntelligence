import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.types import JSON
from app.database import Base


class InternalCompanyContext(Base):
    __tablename__ = "internal_company_context"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(255), nullable=True)
    short_description = Column(Text, nullable=True)
    target_industries = Column(JSON, default=list)
    target_segments = Column(JSON, default=list)
    core_capabilities = Column(JSON, default=list)
    strategic_priorities = Column(JSON, default=list)
    differentiators = Column(JSON, default=list)
    relevant_competitive_areas = Column(JSON, default=list)
    non_focus_areas = Column(JSON, default=list)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
