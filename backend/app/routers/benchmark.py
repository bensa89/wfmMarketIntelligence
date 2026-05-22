from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.benchmark.aggregation import BenchmarkAggregationService
from app.benchmark.queries import BenchmarkQueryService
from app.schemas.benchmark import (
    BenchmarkOverviewResponse,
    CompetitorBenchmarkResponse,
    CapabilityLeaderboardResponse,
    CapabilityAssessmentsResponse,
)

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


@router.get("/overview", response_model=BenchmarkOverviewResponse)
def get_overview(
    period_type: str = "30d",
    db: Session = Depends(get_db),
):
    return BenchmarkQueryService(db).get_overview(period_type)


@router.get("/competitors/{slug}", response_model=CompetitorBenchmarkResponse)
def get_competitor_strengths(
    slug: str,
    period_type: str = "30d",
    db: Session = Depends(get_db),
):
    try:
        return BenchmarkQueryService(db).get_competitor_strengths(slug, period_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/competitors/{slug}/capabilities/{cap_key}/assessments", response_model=CapabilityAssessmentsResponse)
def get_capability_assessments(
    slug: str,
    cap_key: str,
    period_type: str = "30d",
    db: Session = Depends(get_db),
):
    try:
        return BenchmarkQueryService(db).get_capability_assessments(slug, cap_key, period_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/capabilities/{key}", response_model=CapabilityLeaderboardResponse)
def get_capability_leaderboard(
    key: str,
    period_type: str = "30d",
    db: Session = Depends(get_db),
):
    return BenchmarkQueryService(db).get_capability_leaderboard(key, period_type)


@router.post("/recompute")
def recompute_all(
    period_type: str = "30d",
    db: Session = Depends(get_db),
):
    results = BenchmarkAggregationService(db).recompute_all(period_type)
    return {"recomputed": len(results), "period_type": period_type}


@router.post("/recompute/{company_id}")
def recompute_company(
    company_id: str,
    period_type: str = "30d",
    db: Session = Depends(get_db),
):
    results = BenchmarkAggregationService(db).recompute_company(company_id, period_type)
    return {"recomputed": len(results), "company_id": company_id, "period_type": period_type}
