from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ExternalCompanyViewRead(BaseModel):
    id: str
    summary: Optional[str] = None
    key_messages: list[str] = []
    observed_capabilities: list[str] = []
    observed_differentiators: list[str] = []
    observed_target_markets: list[str] = []
    tone_and_positioning: Optional[str] = None
    signal_count_used: int = 0
    generated_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
