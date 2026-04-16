from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.signal import Signal, SignalType
from app.schemas.signal import SignalRead

router = APIRouter()


@router.get("", response_model=List[SignalRead])
def list_signals(
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    min_relevance: Optional[float] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Signal)
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_relevance is not None:
        query = query.filter(Signal.relevance_score >= min_relevance)
    return query.order_by(Signal.created_at.desc()).all()


@router.get("/{signal_id}", response_model=SignalRead)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
