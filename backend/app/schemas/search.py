from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.search_run import SearchRunStatus
from app.models.search_result import SearchResultStatus
from app.models.source_candidate import SourceCandidateStatus
from app.models.source import SourceType


class SearchQueryRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    query_text: str
    company_id: Optional[str]
    topic: Optional[str]
    search_intent: str
    generated_at: datetime


class SearchRunRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    search_query_id: str
    executed_at: datetime
    status: SearchRunStatus
    result_count: Optional[int]
    error_message: Optional[str]
    query: Optional[SearchQueryRead] = None


class SearchResultRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    search_run_id: str
    title: Optional[str]
    url: str
    domain: Optional[str]
    snippet: Optional[str]
    discovered_at: datetime
    relevance_score: Optional[float]
    processing_status: SearchResultStatus
    linked_document_id: Optional[str]


class SourceCandidateRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    url: str
    domain: str
    title: Optional[str]
    snippet: Optional[str]
    found_via_query: Optional[str]
    company_id: Optional[str]
    source_type_guess: Optional[SourceType]
    relevance_score: Optional[float]
    status: SourceCandidateStatus
    created_at: datetime


class SourceCandidateApprove(BaseModel):
    label: Optional[str] = None
    source_type: SourceType = SourceType.news
