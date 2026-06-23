# backend/app/schemas/llm_usage.py
from typing import List
from pydantic import BaseModel


class LlmUsageTotals(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class LlmUsageSummary(BaseModel):
    today: LlmUsageTotals
    last_7_days: LlmUsageTotals
    last_30_days: LlmUsageTotals
    all_time: LlmUsageTotals


class LlmUsageTimeseriesPoint(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class LlmUsageBreakdownRow(BaseModel):
    caller: str
    provider: str
    model: str
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class LlmModelPriceRead(BaseModel):
    model: str
    input_price_per_1m: float
    output_price_per_1m: float

    class Config:
        from_attributes = True


class LlmModelPriceUpdate(BaseModel):
    input_price_per_1m: float
    output_price_per_1m: float
