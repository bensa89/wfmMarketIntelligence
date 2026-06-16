from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, selectinload

from app.models.signal import Signal, SignalType
from app.models.document import Document
from app.models.company import Company, CompanyType


def _build_event_item(signal: Signal, is_new: bool = False) -> dict:
    doc = signal.document
    return {
        "signal_id": signal.id,
        "event_name": signal.event_name or signal.title,
        "event_date": signal.event_date.date().isoformat() if signal.event_date else None,
        "event_location": signal.event_location,
        "event_type": signal.event_type,
        "company": signal.company.name if signal.company else "Unknown",
        "source_url": doc.url if doc else None,
        "is_new": is_new,
    }


def build_event_calendar_section(db: Session, week_start: date) -> dict | None:
    today = date.today()
    cutoff_14 = today + timedelta(days=14)

    all_future = (
        db.query(Signal)
        .join(Signal.company)
        .join(Signal.document)
        .options(
            selectinload(Signal.company),
            selectinload(Signal.document),
        )
        .filter(
            Signal.signal_type == SignalType.event_or_thought_leadership,
            Company.type.in_([CompanyType.competitor, CompanyType.own_company]),
            Signal.event_date.isnot(None),
            Signal.event_date >= datetime.combine(today, time.min),
        )
        .order_by(Signal.event_date.asc())
        .all()
    )

    new_ids = {
        s.id for s in all_future
        if s.created_at and s.created_at.date() >= week_start
    }

    upcoming: list[dict] = []
    newly_discovered: list[dict] = []

    for signal in all_future:
        event_date = signal.event_date.date() if signal.event_date else None
        is_new = signal.id in new_ids

        if event_date and event_date <= cutoff_14:
            upcoming.append(_build_event_item(signal, is_new=is_new))
        elif is_new:
            newly_discovered.append(_build_event_item(signal, is_new=False))

    newly_discovered = newly_discovered[:5]

    if not upcoming and not newly_discovered:
        return None

    return {
        "key": "events_calendar",
        "title": "Events",
        "items": [],
        "upcoming": upcoming,
        "newly_discovered": newly_discovered,
    }
