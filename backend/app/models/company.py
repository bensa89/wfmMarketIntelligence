import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class CompanyType(str, enum.Enum):
    competitor = "competitor"
    market_source = "market_source"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    type = Column(SAEnum(CompanyType), nullable=False)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sources = relationship(
        "Source", back_populates="company", cascade="all, delete-orphan"
    )
    signals = relationship("Signal", back_populates="company")
