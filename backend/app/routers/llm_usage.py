# backend/app/routers/llm_usage.py
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_call import LlmCall
from app.models.llm_model_price import LlmModelPrice
from app.schemas.llm_usage import (
    LlmModelPriceRead,
    LlmModelPriceUpdate,
    LlmUsageBreakdownRow,
    LlmUsageSummary,
    LlmUsageTimeseriesPoint,
    LlmUsageTotals,
)

router = APIRouter()


def _price_map(db: Session) -> dict:
    return {p.model: p for p in db.query(LlmModelPrice).all()}


def _cost_usd(model: str, input_tokens: int, output_tokens: int, prices: dict) -> float:
    price = prices.get(model)
    if price is None:
        return 0.0
    return (input_tokens / 1_000_000 * price.input_price_per_1m) + (
        output_tokens / 1_000_000 * price.output_price_per_1m
    )


def _totals_since(db: Session, since: datetime, prices: dict) -> LlmUsageTotals:
    rows = db.query(LlmCall.model, LlmCall.input_tokens, LlmCall.output_tokens).filter(
        LlmCall.created_at >= since
    ).all()
    input_tokens = sum(r.input_tokens for r in rows)
    output_tokens = sum(r.output_tokens for r in rows)
    cost = sum(_cost_usd(r.model, r.input_tokens, r.output_tokens, prices) for r in rows)
    return LlmUsageTotals(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=round(cost, 4),
    )


@router.get("/summary", response_model=LlmUsageSummary)
def get_summary(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    prices = _price_map(db)
    return LlmUsageSummary(
        today=_totals_since(db, today_start, prices),
        last_7_days=_totals_since(db, now - timedelta(days=7), prices),
        last_30_days=_totals_since(db, now - timedelta(days=30), prices),
        all_time=_totals_since(db, datetime.min.replace(tzinfo=timezone.utc), prices),
    )


@router.get("/timeseries", response_model=List[LlmUsageTimeseriesPoint])
def get_timeseries(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    prices = _price_map(db)
    rows = db.query(LlmCall.created_at, LlmCall.model, LlmCall.input_tokens, LlmCall.output_tokens).filter(
        LlmCall.created_at >= since
    ).all()

    by_day: dict = {}
    for r in rows:
        day_key = r.created_at.date().isoformat()
        bucket = by_day.setdefault(day_key, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
        bucket["input_tokens"] += r.input_tokens
        bucket["output_tokens"] += r.output_tokens
        bucket["cost_usd"] += _cost_usd(r.model, r.input_tokens, r.output_tokens, prices)

    return [
        LlmUsageTimeseriesPoint(
            date=day,
            input_tokens=v["input_tokens"],
            output_tokens=v["output_tokens"],
            total_tokens=v["input_tokens"] + v["output_tokens"],
            cost_usd=round(v["cost_usd"], 4),
        )
        for day, v in sorted(by_day.items())
    ]


@router.get("/breakdown", response_model=List[LlmUsageBreakdownRow])
def get_breakdown(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    prices = _price_map(db)
    rows = db.query(
        LlmCall.caller, LlmCall.provider, LlmCall.model,
        func.count(LlmCall.id).label("call_count"),
        func.sum(LlmCall.input_tokens).label("input_tokens"),
        func.sum(LlmCall.output_tokens).label("output_tokens"),
    ).filter(LlmCall.created_at >= since).group_by(
        LlmCall.caller, LlmCall.provider, LlmCall.model
    ).all()

    result = []
    for r in rows:
        input_tokens = r.input_tokens or 0
        output_tokens = r.output_tokens or 0
        result.append(LlmUsageBreakdownRow(
            caller=r.caller,
            provider=r.provider,
            model=r.model,
            call_count=r.call_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=round(_cost_usd(r.model, input_tokens, output_tokens, prices), 4),
        ))
    return result


@router.get("/prices", response_model=List[LlmModelPriceRead])
def get_prices(db: Session = Depends(get_db)):
    return db.query(LlmModelPrice).order_by(LlmModelPrice.model).all()


@router.put("/prices/{model}", response_model=LlmModelPriceRead)
def upsert_price(model: str, payload: LlmModelPriceUpdate, db: Session = Depends(get_db)):
    price = db.query(LlmModelPrice).filter(LlmModelPrice.model == model).first()
    if price is None:
        price = LlmModelPrice(model=model)
        db.add(price)
    price.input_price_per_1m = payload.input_price_per_1m
    price.output_price_per_1m = payload.output_price_per_1m
    db.commit()
    db.refresh(price)
    return price
