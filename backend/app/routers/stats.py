from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.signal import Signal, SignalType
from app.models.company import Company
from app.schemas.stats import (
    SignalOverTimePoint,
    SignalTypeCount,
    CompanySignalTypeCount,
    SignalDistribution,
)

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
