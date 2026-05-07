from datetime import datetime
from typing import Optional, List, Dict
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
    fetch_ms: Optional[int] = None
    extract_ms: Optional[int] = None
    analyse_ms: Optional[int] = None
    discover_ms: Optional[int] = None
    discover_pages_crawled: Optional[int] = None
    discover_pages_found: Optional[int] = None
    analyse_started_at: Optional[datetime] = None
    analyse_finished_at: Optional[datetime] = None
    analyse_docs_done: int = 0
    analyse_docs_total: int = 0
    analyse_current_url: Optional[str] = None


class CrawlRunRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    status: str
    started_at: Optional[datetime] = None
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
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_sources: int = 0
    total_new: int = 0
    total_skipped: int = 0
    total_errors: int = 0


class CrawlQueuedRunStatus(BaseModel):
    id: str
    sources: List[Dict[str, str]]


class CrawlStatusResponse(BaseModel):
    active_run: Optional[CrawlRunRead] = None
    queued_run: Optional[CrawlQueuedRunStatus] = None
