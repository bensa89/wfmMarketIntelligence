from pydantic import BaseModel
from typing import List


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
