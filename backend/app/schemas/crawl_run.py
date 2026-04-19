from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CrawlRunSourceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    crawl_run_id: str
    source_id: str
    url: str
    status: str
    current_step: Optional[str] = None
    new_documents: int = 0
    skipped: int = 0
    errors: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class CrawlRunRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_sources: int = 0
    total_new: int = 0
    total_skipped: int = 0
    total_errors: int = 0
    sources: List[CrawlRunSourceRead] = []


class CrawlRunListRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_sources: int = 0
    total_new: int = 0
    total_skipped: int = 0
    total_errors: int = 0
