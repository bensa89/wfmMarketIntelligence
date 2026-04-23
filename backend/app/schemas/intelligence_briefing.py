from pydantic import BaseModel
from datetime import datetime


class IntelligenceBriefingRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    content: str
    signal_count: int
    assessment_count: int
    generated_at: datetime
