from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.discovered_page import DiscoveredPageStatus


class DiscoveredPageRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    source_id: str
    url: str
    title: Optional[str]
    depth: int
    status: DiscoveredPageStatus
    is_active: bool
    content_hash: Optional[str]
    discovered_at: datetime
    last_crawled_at: Optional[datetime]
    last_changed_at: Optional[datetime]
    last_signal_relevance: Optional[float] = None


class DiscoveredPageUpdate(BaseModel):
    is_active: bool


class DiscoveredPagesStats(BaseModel):
    total: int
    new: int
    changed: int
    known: int
