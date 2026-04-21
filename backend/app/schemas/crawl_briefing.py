# backend/app/schemas/crawl_briefing.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CrawlBriefingRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    crawl_run_id: Optional[str]
    content: str
    generated_at: datetime


class CrawlBriefingCreate(BaseModel):
    crawl_run_id: Optional[str] = None
