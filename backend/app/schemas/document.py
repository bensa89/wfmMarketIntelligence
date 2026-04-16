from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    source_id: str
    url: str
    title: Optional[str]
    content_markdown: Optional[str]
    published_at: Optional[datetime]
    crawled_at: datetime
    content_hash: Optional[str]
    is_analysed: bool
