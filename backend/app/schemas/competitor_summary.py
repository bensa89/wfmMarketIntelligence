from typing import Optional, List, Any
from datetime import datetime, date
from pydantic import BaseModel


class CompetitorSummaryRead(BaseModel):
    id: str
    company_id: str
    period_type: str
    period_start: date
    period_end: date
    strategic_posture: Optional[str] = None
    positioning_summary: Optional[str] = None
    top_capabilities: List[str] = []
    capability_assessment: List[Any] = []
    top_risks: List[str] = []
    top_opportunities: List[str] = []
    watchpoints: List[str] = []
    avg_movement_score: Optional[float] = None
    signal_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
