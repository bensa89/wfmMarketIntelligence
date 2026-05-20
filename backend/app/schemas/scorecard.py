from __future__ import annotations
from typing import Any, Optional
from datetime import date, datetime
from pydantic import BaseModel


class ScorecardKPIValue(BaseModel):
    value: Optional[float]
    contributing_ids: list[str]


class ScorecardDimension(BaseModel):
    score: Optional[float]
    trend: Optional[str]
    kpis: dict[str, ScorecardKPIValue]


class ScorecardTopMove(BaseModel):
    assessment_id: str
    signal_id: str
    title: str
    movement_score: int
    signal_class: str


class ScorecardRiskFlag(BaseModel):
    assessment_id: str
    capability_key: str
    movement_strength: str
    title: str


class ScorecardBenchmarkPosition(BaseModel):
    rank: int
    percentile: float
    total_competitors: int


class ScorecardRead(BaseModel):
    id: str
    company_id: str
    period_type: str
    period_start: date
    period_end: date
    generated_at: datetime
    overall_score: Optional[float]
    overall_trend: Optional[str]
    dimension_scores: dict[str, ScorecardDimension]
    top_capabilities: list[dict[str, Any]]
    top_moves: list[ScorecardTopMove]
    risk_flags: list[ScorecardRiskFlag]
    watchpoints: list[str]
    benchmark_position: Optional[ScorecardBenchmarkPosition]
    contributing_assessment_ids: list[str]
    is_current: bool
    scorecard_version: Optional[str]
    routing_version: Optional[str]

    model_config = {"from_attributes": True}


class ScorecardHistoryItem(BaseModel):
    id: str
    overall_score: Optional[float]
    overall_trend: Optional[str]
    generated_at: datetime
    scorecard_version: Optional[str]

    model_config = {"from_attributes": True}


class ScorecardExplainAssessment(BaseModel):
    assessment_id: str
    signal_id: str
    title: str
    movement_score: int
    signal_class: str


class ScorecardExplainDimension(BaseModel):
    dimension: str
    score: Optional[float]
    dimension_weight: float
    effective_weight: float
    weighted_contribution: Optional[float]
    assessment_count: int
    top_contributing_assessments: list[ScorecardExplainAssessment]
    kpi_detail: dict[str, ScorecardKPIValue]


class ScorecardExplain(BaseModel):
    overall_score: Optional[float]
    dimension_breakdown: list[ScorecardExplainDimension]
    null_dimensions: list[str]
    score_formula: str
    routing_version: Optional[str]
    scorecard_version: Optional[str]


class ScorecardRecomputeAck(BaseModel):
    status: str
    company_slug: str
    recomputed_periods: list[str]
    scorecard_ids: dict[str, str]
    generated_at: datetime


class BenchmarkScorecardItem(BaseModel):
    company_id: str
    slug: str
    name: str
    overall_score: Optional[float]
    rank: int
    percentile: float
    dimension_scores: dict[str, ScorecardDimension]
    overall_trend: Optional[str]
    scorecard_version: Optional[str]


class BenchmarkScorecardView(BaseModel):
    items: list[BenchmarkScorecardItem]
    total: int
    page: int
    page_size: int
    pages: int
    period_type: str
    capability_leaders: dict[str, dict[str, Any]]
    highest_momentum: Optional[dict[str, Any]]
    threat_flags: list[dict[str, Any]]
