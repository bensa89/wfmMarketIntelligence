from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ScheduleConfigUpdate(BaseModel):
    crawl_enabled: bool = False
    crawl_day_of_week: int = Field(0, ge=0, le=6)
    crawl_time: str = "06:00"
    crawl_timezone: str = "Europe/Berlin"
    digest_after_crawl: bool = True
    digest_enabled: bool = False
    digest_day_of_week: int = Field(1, ge=0, le=6)
    digest_time: str = "08:00"
    email_enabled: bool = False
    email_recipients: List[str] = []
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


class ScheduleConfigRead(ScheduleConfigUpdate):
    updated_at: Optional[datetime] = None


class ScheduleStatusRead(BaseModel):
    config: ScheduleConfigRead
    next_crawl: Optional[str] = None
    next_digest: Optional[str] = None
