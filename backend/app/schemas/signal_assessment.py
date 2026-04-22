from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class SignalAssessmentRead(BaseModel):
    id: str
    signal_id: str
    company_id: str
    capability_primary: Optional[str] = None
    capability_secondary: List[str] = []
    signal_class: Optional[str] = None
    evidence_strength: Optional[int] = None
    visibility_impact: Optional[str] = None
    strategic_weight: Optional[int] = None
    movement_score: Optional[int] = None
    movement_strength: Optional[str] = None
    confidence: Optional[float] = None
    strategic_intent_guess: Optional[str] = None
    gameplay_tags: List[str] = []
    assessment_summary: Optional[str] = None
    implication_for_us: Optional[str] = None
    watch_items: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
