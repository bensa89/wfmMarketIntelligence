from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta
from app.database import get_db
from app.models.digest import WeeklyDigest
from app.models.signal import Signal
from app.schemas.digest import DigestRead

router = APIRouter()


@router.get("", response_model=List[DigestRead])
def list_digests(db: Session = Depends(get_db)):
    return db.query(WeeklyDigest).order_by(WeeklyDigest.week_start.desc()).all()


@router.get("/{digest_id}", response_model=DigestRead)
def get_digest(digest_id: str, db: Session = Depends(get_db)):
    digest = db.query(WeeklyDigest).filter(WeeklyDigest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest


@router.post(
    "/generate", response_model=DigestRead, status_code=status.HTTP_201_CREATED
)
def generate_digest(db: Session = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    signals = (
        db.query(Signal)
        .filter(Signal.created_at >= week_start)
        .order_by(Signal.relevance_score.desc())
        .limit(10)
        .all()
    )
    key_signal_ids = [s.id for s in signals]

    summary_parts = []
    for s in signals[:5]:
        summary_parts.append(
            f"- {s.title} ({s.signal_type.value}, relevance: {s.relevance_score:.1f})"
        )
    summary = (
        f"Week {week_start} – {week_end}. Top signals:\n" + "\n".join(summary_parts)
        if summary_parts
        else f"No signals for week {week_start}."
    )

    digest = WeeklyDigest(
        week_start=week_start,
        week_end=week_end,
        summary=summary,
        key_signals=key_signal_ids,
        is_published=False,
    )
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return digest
