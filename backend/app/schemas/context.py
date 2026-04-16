from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ContextUpdate(BaseModel):
    company_name: Optional[str] = None
    short_description: Optional[str] = None
    target_industries: Optional[List[str]] = None
    target_segments: Optional[List[str]] = None
    core_capabilities: Optional[List[str]] = None
    strategic_priorities: Optional[List[str]] = None
    differentiators: Optional[List[str]] = None
    relevant_competitive_areas: Optional[List[str]] = None
    non_focus_areas: Optional[List[str]] = None


class ContextRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_name: Optional[str]
    short_description: Optional[str]
    target_industries: List[str]
    target_segments: List[str]
    core_capabilities: List[str]
    strategic_priorities: List[str]
    differentiators: List[str]
    relevant_competitive_areas: List[str]
    non_focus_areas: List[str]
    updated_at: datetime
