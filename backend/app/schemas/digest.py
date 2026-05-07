from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class DigestSignalRead(BaseModel):
    id: str
    title: Optional[str] = None
    signal_type: Optional[str] = None
    topic: Optional[str] = None
    summary: Optional[str] = None
    relevance_score: Optional[float] = None
    confidence_score: Optional[float] = None
    source_url: Optional[str] = None
    company_name: Optional[str] = None

    model_config = {"from_attributes": True}


class DigestSectionItem(BaseModel):
    signal_id: str
    company: str
    title: str
    narrative: str
    implication_for_us: str
    movement_strength: Optional[str] = None
    source_url: Optional[str] = None
    source_domain: Optional[str] = None
    source_title: Optional[str] = None

    model_config = {"from_attributes": True}


class DigestSection(BaseModel):
    key: str
    title: str
    items: list[DigestSectionItem] = []

    model_config = {"from_attributes": True}


class DigestRead(BaseModel):
    id: str
    week_start: date
    week_end: date
    summary: Optional[str] = None
    key_signals: list[DigestSignalRead] = []
    sections: list[DigestSection] = []
    generated_at: datetime
    is_published: bool

    model_config = {"from_attributes": True}
