from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.signal_assessment import SignalAssessment
from app.models.competitor_scorecard import CompetitorScorecard
from app.schemas.scorecard import (
    ScorecardRead, ScorecardHistoryItem, ScorecardExplain, ScorecardExplainDimension,
    ScorecardExplainAssessment, ScorecardKPIValue, ScorecardRecomputeAck,
    BenchmarkScorecardItem, BenchmarkScorecardView, ScorecardDimension,
)
from app.scorecard.builder import ScorecardBuilder
from app.scorecard.constants import VALID_PERIOD_TYPES, DIMENSION_WEIGHTS
from app.assessor.capabilities import CAPABILITIES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scorecards", tags=["scorecards"])


def _require_period(period_type: Optional[str] = Query(default=None)) -> str:
    if period_type not in VALID_PERIOD_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"period_type is required. Valid values: {', '.join(VALID_PERIOD_TYPES)}",
        )
    return period_type


def _get_company(slug: str, db: Session) -> Company:
    company = db.query(Company).filter_by(slug=slug).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{slug}' not found")
    return company


def _get_current_scorecard(company_id: str, period_type: str, db: Session) -> CompetitorScorecard:
    sc = db.query(CompetitorScorecard).filter_by(
        company_id=company_id, period_type=period_type, is_current=True
    ).first()
    if not sc:
        raise HTTPException(status_code=404, detail="No scorecard for this company and period")
    return sc


# --- Benchmark routes must be defined before /{company_slug} to avoid path conflict ---

@router.get("/benchmark", response_model=BenchmarkScorecardView)
def get_benchmark(
    period_type: str = Depends(_require_period),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(CompetitorScorecard).filter_by(period_type=period_type, is_current=True)
    total = query.count()
    rows = query.order_by(CompetitorScorecard.overall_score.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for sc in rows:
        company = sc.company
        items.append(BenchmarkScorecardItem(
            company_id=sc.company_id, slug=company.slug, name=company.name,
            overall_score=sc.overall_score, rank=sc.benchmark_position.get("rank", 0) if sc.benchmark_position else 0,
            percentile=sc.benchmark_position.get("percentile", 0) if sc.benchmark_position else 0,
            dimension_scores={
                k: ScorecardDimension(
                    score=v.get("score"), trend=v.get("trend"),
                    kpis={ki: ScorecardKPIValue(value=kv.get("value"), contributing_ids=kv.get("contributing_ids", []))
                          for ki, kv in v.get("kpis", {}).items()}
                )
                for k, v in (sc.dimension_scores or {}).items()
            },
            overall_trend=sc.overall_trend, scorecard_version=sc.scorecard_version,
        ))

    all_current = db.query(CompetitorScorecard).filter_by(period_type=period_type, is_current=True).all()
    threat_flags: list[dict] = []
    for sc in all_current:
        for rf in (sc.risk_flags or []):
            threat_flags.append({
                "company_slug": sc.company.slug,
                "capability": rf.get("capability_key"),
                "movement_strength": rf.get("movement_strength"),
            })

    highest = max(
        (sc for sc in all_current if sc.dimension_scores and sc.dimension_scores.get("momentum", {}).get("kpis", {}).get("mom_period_delta", {}).get("value") is not None),
        key=lambda sc: sc.dimension_scores["momentum"]["kpis"]["mom_period_delta"]["value"],
        default=None,
    )
    highest_momentum = None
    if highest:
        delta = highest.dimension_scores["momentum"]["kpis"]["mom_period_delta"]["value"]
        highest_momentum = {"company_slug": highest.company.slug, "mom_period_delta": delta}

    cap_leaders: dict[str, dict] = {}
    for cap_key in CAPABILITIES:
        best = max(
            (sc for sc in all_current if sc.dimension_scores and
             sc.dimension_scores.get("capability_strength", {}).get("score") is not None),
            key=lambda sc: sc.dimension_scores.get("capability_strength", {}).get("score", 0),
            default=None,
        )
        if best:
            cap_leaders[cap_key] = {
                "company_slug": best.company.slug,
                "score": best.dimension_scores["capability_strength"]["score"],
            }
        break  # simplified: one entry for all caps — extend later per-capability

    return BenchmarkScorecardView(
        items=items, total=total, page=page, page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
        period_type=period_type,
        capability_leaders=cap_leaders,
        highest_momentum=highest_momentum,
        threat_flags=threat_flags,
    )


@router.get("/benchmark/capability/{capability_key}")
def get_benchmark_capability(
    capability_key: str,
    period_type: str = Depends(_require_period),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    cap_meta = CAPABILITIES.get(capability_key)
    if not cap_meta:
        raise HTTPException(status_code=404, detail=f"Unknown capability: {capability_key}")
    rows = db.query(CompetitorScorecard).filter_by(period_type=period_type, is_current=True).all()
    scored = sorted(
        rows,
        key=lambda sc: (sc.dimension_scores or {}).get("capability_strength", {}).get("score") or 0,
        reverse=True,
    )
    total = len(scored)
    page_rows = scored[(page - 1) * page_size: page * page_size]
    return {
        "capability_key": capability_key,
        "wardley_band": cap_meta.get("default_evolution_band"),
        "period_type": period_type,
        "total": total, "page": page, "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
        "items": [
            {
                "company_slug": sc.company.slug,
                "company_name": sc.company.name,
                "capability_score": (sc.dimension_scores or {}).get("capability_strength", {}).get("score"),
                "rank": idx + 1,
            }
            for idx, sc in enumerate(page_rows)
        ],
    }


# --- Per-competitor routes ---

@router.get("/{company_slug}", response_model=ScorecardRead)
def get_scorecard(
    company_slug: str,
    period_type: str = Depends(_require_period),
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    return _get_current_scorecard(company.id, period_type, db)


@router.get("/{company_slug}/history", response_model=list[ScorecardHistoryItem])
def get_scorecard_history(
    company_slug: str,
    period_type: str = Depends(_require_period),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    return (
        db.query(CompetitorScorecard)
        .filter_by(company_id=company.id, period_type=period_type)
        .order_by(CompetitorScorecard.generated_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{company_slug}/explain", response_model=ScorecardExplain)
def get_scorecard_explain(
    company_slug: str,
    period_type: str = Depends(_require_period),
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    sc = _get_current_scorecard(company.id, period_type, db)

    non_null_dims = [k for k, v in (sc.dimension_scores or {}).items() if v.get("score") is not None]
    null_dims = [k for k in DIMENSION_WEIGHTS if k not in non_null_dims]
    total_raw = sum(DIMENSION_WEIGHTS[k] for k in non_null_dims) or 1.0

    breakdown = []
    for dim_key, dim_data in (sc.dimension_scores or {}).items():
        score = dim_data.get("score")
        raw_weight = DIMENSION_WEIGHTS.get(dim_key, 0)
        eff_weight = round(raw_weight / total_raw, 4) if score is not None else 0.0
        contribution = round(score * eff_weight, 2) if score is not None else None
        contributing_ids = sc.contributing_assessment_ids or []

        assessments = (
            db.query(SignalAssessment)
            .filter(SignalAssessment.id.in_(contributing_ids[:50]))
            .all()
        )
        dim_assessments = [
            a for a in assessments
            if dim_key in ((a.dimension_targets or {}) if isinstance(a.dimension_targets, dict) else {})
        ]
        top5 = sorted(
            dim_assessments,
            key=lambda a: (a.movement_score or 0) * (a.assessment_weight or 1.0),
            reverse=True,
        )[:5]

        breakdown.append(ScorecardExplainDimension(
            dimension=dim_key,
            score=score,
            dimension_weight=raw_weight,
            effective_weight=eff_weight,
            weighted_contribution=contribution,
            assessment_count=len(dim_assessments),
            top_contributing_assessments=[
                ScorecardExplainAssessment(
                    assessment_id=a.id, signal_id=a.signal_id,
                    title=a.signal.title if a.signal else "",
                    movement_score=a.movement_score or 0,
                    signal_class=(a.signal_class.value if hasattr(a.signal_class, "value") else a.signal_class) or "",
                )
                for a in top5
            ],
            kpi_detail={
                ki: ScorecardKPIValue(value=kv.get("value"), contributing_ids=kv.get("contributing_ids", []))
                for ki, kv in dim_data.get("kpis", {}).items()
            },
        ))

    return ScorecardExplain(
        overall_score=sc.overall_score,
        dimension_breakdown=breakdown,
        null_dimensions=null_dims,
        score_formula="Weighted average of non-null dimensions. Weights re-normalised: shown as effective_weight.",
        routing_version=sc.routing_version,
        scorecard_version=sc.scorecard_version,
    )


@router.post("/{company_slug}/recompute", response_model=ScorecardRecomputeAck)
def recompute_scorecard(
    company_slug: str,
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    builder = ScorecardBuilder(db)
    scorecard_ids: dict[str, str] = {}
    generated_at = datetime.now(timezone.utc)
    for period_type in VALID_PERIOD_TYPES:
        try:
            sc = builder.build(company.id, period_type)
            scorecard_ids[period_type] = sc.id
        except Exception as exc:
            logger.warning("Recompute failed for %s/%s: %s", company_slug, period_type, exc)
    return ScorecardRecomputeAck(
        status="ok",
        company_slug=company_slug,
        recomputed_periods=list(scorecard_ids.keys()),
        scorecard_ids=scorecard_ids,
        generated_at=generated_at,
    )


@router.post("/recompute-all")
def recompute_all(
    period_type: str = Depends(_require_period),
    db: Session = Depends(get_db),
):
    from app.models.company import CompanyType
    companies = db.query(Company).filter_by(type=CompanyType.competitor).all()
    builder = ScorecardBuilder(db)
    recomputed = 0
    errors = []
    for company in companies:
        try:
            builder.build(company.id, period_type)
            recomputed += 1
        except Exception as exc:
            errors.append({"company_slug": company.slug, "error": str(exc)})
    return {"recomputed": recomputed, "errors": errors}
