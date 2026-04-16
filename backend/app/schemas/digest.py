from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class DigestRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    week_start: date
    week_end: date
    summary: Optional[str]
    key_signals: List[str]
    generated_at: datetime
    is_published: bool
