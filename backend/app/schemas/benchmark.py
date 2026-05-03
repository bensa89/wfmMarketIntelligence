from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class BenchmarkSubScores(BaseModel):
    capability_depth: int = Field(0, ge=0, le=5)
    execution_momentum: int = Field(0, ge=0, le=5)
    market_proof: int = Field(0, ge=0, le=5)
    strategic_focus: int = Field(0, ge=0, le=5)
    evidence_coverage: int = Field(0, ge=0, le=5)


class BenchmarkRead(BaseModel):
    id: str
    company_id: str
    capability_key: str
    period_type: str
    period_start: date
    period_end: date
    capability_depth_score: int
    execution_momentum_score: int
    market_proof_score: int
    strategic_focus_score: int
    evidence_coverage_score: int
    relative_strength_score: int
    prev_period_strength_score: Optional[int] = None
    strength_delta: Optional[int] = None
    peer_rank: Optional[int] = None
    peer_percentile: Optional[float] = None
    tier: str
    confidence: float
    source_signal_count: int
    summary_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorBrief(BaseModel):
    id: str
    name: str
    slug: str


class BenchmarkMatrixCell(BaseModel):
    score: int
    tier: str
    confidence: float
    rank: Optional[int] = None
    momentum_score: int


class BenchmarkOverviewResponse(BaseModel):
    period_type: str
    period_start: date
    period_end: date
    capabilities: list[str]
    competitors: list[CompetitorBrief]
    matrix: dict[str, dict[str, BenchmarkMatrixCell]]  # capability_key → company_id → cell


class CompetitorBenchmarkDetail(BaseModel):
    capability_key: str
    label: str
    relative_strength_score: int
    prev_period_strength_score: Optional[int] = None
    strength_delta: Optional[int] = None
    tier: str
    peer_rank: Optional[int] = None
    peer_percentile: Optional[float] = None
    confidence: float
    sub_scores: BenchmarkSubScores
    source_signal_count: int
    summary_reason: Optional[str] = None


class CompetitorBenchmarkResponse(BaseModel):
    competitor: CompetitorBrief
    period_type: str
    capabilities: list[CompetitorBenchmarkDetail]
    strongest_capabilities: list[str]
    weakest_evidenced_capabilities: list[str]


class LeaderboardEntry(BaseModel):
    company_id: str
    company_name: str
    slug: str
    score: int
    tier: str
    confidence: float
    rank: int
    momentum_score: int
    strength_delta: Optional[int] = None
    summary_reason: Optional[str] = None


class CapabilityLeaderboardResponse(BaseModel):
    capability_key: str
    label: str
    period_type: str
    leaderboard: list[LeaderboardEntry]
    strongest_competitor: Optional[LeaderboardEntry] = None
    fastest_riser: Optional[LeaderboardEntry] = None
