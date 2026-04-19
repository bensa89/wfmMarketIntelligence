from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.signal import SignalType


class DigestSignalRead(BaseModel):
    id: str
    title: str
    signal_type: SignalType
    topic: Optional[str]
    summary: Optional[str]
    relevance_score: Optional[float]
    confidence_score: Optional[float]
    source_url: Optional[str]
    company_name: Optional[str]


class DigestRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    week_start: date
    week_end: date
    summary: Optional[str]
    key_signals: List[DigestSignalRead]
    generated_at: datetime
    is_published: bool
