from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.signal import Signal, SignalType
from app.models.company import Company
from app.models.document import Document
from app.models.crawl_run import CrawlRun, CrawlRunStatus
from app.schemas.stats import (
    SignalOverTimePoint,
    SignalTypeCount,
    CompanySignalTypeCount,
    SignalDistribution,
    LastCrawlSummary,
)

HIGH_RELEVANCE_THRESHOLD = 0.7

router = APIRouter()


@router.get("/signals/over-time", response_model=List[SignalOverTimePoint])
def signals_over_time(
    days: int = Query(14, ge=1, le=90),
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(
        cast(Signal.created_at, Date).label("date"),
        Signal.company_id,
        func.count(Signal.id).label("count"),
    ).filter(Signal.created_at >= cutoff)

    if company_id:
        query = query.filter(Signal.company_id == company_id)

    query = query.group_by(cast(Signal.created_at, Date), Signal.company_id).order_by(
        cast(Signal.created_at, Date)
    )

    results = query.all()

    company_cache = {}
    points = []
    for date, comp_id, count in results:
        if comp_id not in company_cache:
            company = db.query(Company).filter(Company.id == comp_id).first()
            company_cache[comp_id] = company.name if company else "Unknown"
        points.append(
            SignalOverTimePoint(
                date=date.isoformat() if hasattr(date, "isoformat") else str(date),
                company_id=comp_id,
                company_name=company_cache[comp_id],
                count=count,
            )
        )
    return points


@router.get("/signals/distribution", response_model=SignalDistribution)
def signal_distribution(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    type_query = db.query(Signal.signal_type, func.count(Signal.id).label("count"))
    if company_id:
        type_query = type_query.filter(Signal.company_id == company_id)
    type_counts = type_query.group_by(Signal.signal_type).all()

    by_type = [
        SignalTypeCount(signal_type=st.value, count=count) for st, count in type_counts
    ]

    company_type_query = db.query(
        Signal.company_id,
        Signal.signal_type,
        func.count(Signal.id).label("count"),
    )
    if company_id:
        company_type_query = company_type_query.filter(Signal.company_id == company_id)
    company_type_counts = company_type_query.group_by(
        Signal.company_id, Signal.signal_type
    ).all()

    company_cache = {}
    by_company_and_type = []
    for comp_id, st, count in company_type_counts:
        if comp_id not in company_cache:
            company = db.query(Company).filter(Company.id == comp_id).first()
            company_cache[comp_id] = company.name if company else "Unknown"
        by_company_and_type.append(
            CompanySignalTypeCount(
                company_id=comp_id,
                company_name=company_cache[comp_id],
                signal_type=st.value if hasattr(st, "value") else str(st),
                count=count,
            )
        )

    return SignalDistribution(by_type=by_type, by_company_and_type=by_company_and_type)


@router.get("/last-crawl-summary", response_model=LastCrawlSummary)
def last_crawl_summary(db: Session = Depends(get_db)):
    unanalysed_backlog = (
        db.query(func.count(Document.id)).filter(Document.is_analysed.is_(False)).scalar()
    )

    # Heuristic: a "global" crawl run covers more than one source. Single-source
    # runs (triggered via POST /api/crawl/run/{source_id}) always have total_sources == 1.
    last_run = (
        db.query(CrawlRun)
        .filter(CrawlRun.status == CrawlRunStatus.completed, CrawlRun.total_sources > 1)
        .order_by(CrawlRun.started_at.desc())
        .first()
    )

    if not last_run:
        return LastCrawlSummary(
            crawl_run=None,
            new_signals=0,
            new_documents=0,
            high_relevance_signals=0,
            unanalysed_backlog=unanalysed_backlog,
        )

    window_start = last_run.started_at
    window_end = last_run.finished_at or datetime.now(timezone.utc)

    new_signals = (
        db.query(func.count(Signal.id))
        .filter(Signal.created_at >= window_start, Signal.created_at <= window_end)
        .scalar()
    )
    new_documents = (
        db.query(func.count(Document.id))
        .filter(Document.crawled_at >= window_start, Document.crawled_at <= window_end)
        .scalar()
    )
    high_relevance_signals = (
        db.query(func.count(Signal.id))
        .filter(
            Signal.created_at >= window_start,
            Signal.created_at <= window_end,
            Signal.relevance_score >= HIGH_RELEVANCE_THRESHOLD,
        )
        .scalar()
    )

    return LastCrawlSummary(
        crawl_run=last_run,
        new_signals=new_signals,
        new_documents=new_documents,
        high_relevance_signals=high_relevance_signals,
        unanalysed_backlog=unanalysed_backlog,
    )
