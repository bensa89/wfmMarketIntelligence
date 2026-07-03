from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SignalOverTimePoint(BaseModel):
    date: str
    company_id: str
    company_name: str
    count: int


class SignalTypeCount(BaseModel):
    signal_type: str
    count: int


class CompanySignalTypeCount(BaseModel):
    company_id: str
    company_name: str
    signal_type: str
    count: int


class SignalDistribution(BaseModel):
    by_type: List[SignalTypeCount]
    by_company_and_type: List[CompanySignalTypeCount]


class LastCrawlRunInfo(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    total_sources: int
    total_errors: int
    total_analysis_errors: int


class LastCrawlSummary(BaseModel):
    crawl_run: Optional[LastCrawlRunInfo]
    new_signals: int
    new_documents: int
    high_relevance_signals: int
    unanalysed_backlog: int
