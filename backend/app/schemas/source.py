from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
from app.models.source import SourceType, CrawlStatus


class SourceCreate(BaseModel):
    company_id: str
    url: str
    label: Optional[str] = None
    source_type: SourceType = SourceType.news
    is_active: bool = True


class SourceUpdate(BaseModel):
    label: Optional[str] = None
    source_type: Optional[SourceType] = None
    is_active: Optional[bool] = None


class SourceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    url: str
    label: Optional[str]
    source_type: SourceType
    is_active: bool
    crawl_status: CrawlStatus
    content_hash: Optional[str]
    last_crawled_at: Optional[datetime]
    last_changed_at: Optional[datetime]
    created_at: datetime
    discovered_pages_summary: Dict[str, int] = {}
