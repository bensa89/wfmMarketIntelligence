from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, String
from app.database import Base


class LlmModelPrice(Base):
    __tablename__ = "llm_model_prices"

    model = Column(String(100), primary_key=True)
    input_price_per_1m = Column(Float, nullable=False, default=0.0)
    output_price_per_1m = Column(Float, nullable=False, default=0.0)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
