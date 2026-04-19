from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.signal import SignalType


class SignalRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    document_id: str
    company_id: str
    title: str
    signal_type: SignalType
    topic: Optional[str]
    summary: Optional[str]
    why_it_matters: Optional[str]
    relevance_score: Optional[float]
    confidence_score: Optional[float]
    source_url: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
