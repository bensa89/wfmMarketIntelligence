import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db, SessionLocal
from app.models.signal import Signal, SignalType
from app.schemas.signal import SignalRead, DedupResult
from app.analyser.dedup import deduplicate_signals

router = APIRouter()

_reanalysis_jobs: Dict[str, Dict[str, Any]] = {}


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
        from_search=signal.document.from_search if signal.document else False,
    )


def _run_reanalysis(
    job_id: str,
    doc_ids: List[str],
    company_id_by_doc: Dict[str, str],
) -> None:
    from app.models.document import Document
    from app.analyser.pipeline import analyse_document

    db = SessionLocal()
    try:
        done = 0
        errors = 0
        for doc_id in doc_ids:
            try:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    analyse_document(doc, company_id_by_doc[doc_id], db)
                done += 1
            except Exception:
                errors += 1
            _reanalysis_jobs[job_id]["done"] = done
            _reanalysis_jobs[job_id]["errors"] = errors
        _reanalysis_jobs[job_id]["status"] = "completed"
    except Exception:
        _reanalysis_jobs[job_id]["status"] = "failed"
    finally:
        db.close()


@router.delete("/purge")
def purge_old_signals(
    older_than_days: int = 365,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    old_signals = db.query(Signal).filter(Signal.created_at < cutoff).all()
    deleted_count = len(old_signals)
    for signal in old_signals:
        db.delete(signal)
    db.commit()
    return {"deleted_signals": deleted_count, "older_than_days": older_than_days}


@router.post("/deduplicate", response_model=DedupResult)
def deduplicate(
    company_id: str,
    max_age_days: int = 90,
    db: Session = Depends(get_db),
):
    result = deduplicate_signals(db, company_id=company_id, max_age_days=max_age_days)
    return result


@router.get("", response_model=List[SignalRead])
def list_signals(
    q: Optional[str] = None,
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    min_relevance: Optional[float] = None,
    min_confidence: Optional[float] = None,
    max_age_days: Optional[int] = 365,
    db: Session = Depends(get_db),
):
    query = db.query(Signal).options(selectinload(Signal.document)).distinct()
    if q:
        query_expr = func.plainto_tsquery("german", func.unaccent(q))
        query = query.filter(Signal.search_vector.op("@@")(query_expr))
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_relevance is not None:
        query = query.filter(Signal.relevance_score >= min_relevance)
    if min_confidence is not None:
        query = query.filter(Signal.confidence_score >= min_confidence)
    if max_age_days and max_age_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        query = query.filter(Signal.created_at >= cutoff)
    if q:
        query_expr = func.plainto_tsquery("german", func.unaccent(q))
        query = query.order_by(
            func.ts_rank(Signal.search_vector, query_expr).desc(),
            Signal.created_at.desc(),
        )
    else:
        query = query.order_by(Signal.created_at.desc())
    signals = query.all()
    return [_to_signal_read(s) for s in signals]


@router.post("/reanalyse", status_code=202)
def start_reanalysis(
    days: int = 30,
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    from app.models.document import Document

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(Signal).filter(Signal.created_at >= cutoff)
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)

    signals = query.all()
    doc_ids = [s.document_id for s in signals]
    company_id_by_doc = {s.document_id: s.company_id for s in signals}

    for signal in signals:
        db.delete(signal)
    db.flush()

    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.is_analysed = False
    db.commit()

    job_id = str(uuid.uuid4())
    _reanalysis_jobs[job_id] = {
        "status": "running",
        "queued": len(doc_ids),
        "done": 0,
        "errors": 0,
    }

    threading.Thread(
        target=_run_reanalysis,
        args=(job_id, doc_ids, company_id_by_doc),
        daemon=True,
    ).start()

    return {"job_id": job_id, "documents_queued": len(doc_ids)}


@router.get("/reanalyse/{job_id}")
def get_reanalysis_status(job_id: str) -> Dict[str, Any]:
    job = _reanalysis_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


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
