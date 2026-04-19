from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from app.database import get_db
from app.models.signal import Signal, SignalType
from app.schemas.signal import SignalRead

router = APIRouter()


def _to_signal_read(signal: Signal) -> SignalRead:
    return SignalRead(
        id=signal.id,
        document_id=signal.document_id,
        company_id=signal.company_id,
        title=signal.title,
        signal_type=signal.signal_type,
        topic=signal.topic,
        summary=signal.summary,
        why_it_matters=signal.why_it_matters,
        relevance_score=signal.relevance_score,
        confidence_score=signal.confidence_score,
        source_url=signal.document.url if signal.document else None,
        published_at=signal.published_at,
        created_at=signal.created_at,
    )


@router.get("", response_model=List[SignalRead])
def list_signals(
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    min_relevance: Optional[float] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Signal).options(selectinload(Signal.document))
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_relevance is not None:
        query = query.filter(Signal.relevance_score >= min_relevance)
    signals = query.order_by(Signal.created_at.desc()).all()
    return [_to_signal_read(s) for s in signals]


@router.get("/{signal_id}", response_model=SignalRead)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = (
        db.query(Signal)
        .options(selectinload(Signal.document))
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _to_signal_read(signal)
