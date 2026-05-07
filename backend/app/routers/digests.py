from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from app.database import get_db
from app.models.digest import WeeklyDigest
from app.models.signal import Signal
from app.schemas.digest import DigestRead, DigestSignalRead, DigestSection

router = APIRouter()


def _expand_key_signals(digest: WeeklyDigest, db: Session) -> List[DigestSignalRead]:
    if not digest.key_signals:
        return []
    signals = (
        db.query(Signal)
        .options(selectinload(Signal.document), selectinload(Signal.company))
        .filter(Signal.id.in_(digest.key_signals))
        .all()
    )
    signal_map = {s.id: s for s in signals}
    result = []
    for sid in digest.key_signals:
        s = signal_map.get(sid)
        if s:
            result.append(
                DigestSignalRead(
                    id=s.id,
                    title=s.title,
                    signal_type=s.signal_type,
                    topic=s.topic,
                    summary=s.summary,
                    relevance_score=s.relevance_score,
                    confidence_score=s.confidence_score,
                    source_url=s.document.url if s.document else None,
                    company_name=s.company.name if s.company else None,
                )
            )
    return result


def _to_digest_read(digest: WeeklyDigest, db: Session) -> DigestRead:
    expanded = _expand_key_signals(digest, db)
    raw_sections = digest.sections or []
    sections = [DigestSection(**s) for s in raw_sections]
    return DigestRead(
        id=digest.id,
        week_start=digest.week_start,
        week_end=digest.week_end,
        summary=digest.summary,
        key_signals=expanded,
        sections=sections,
        generated_at=digest.generated_at,
        is_published=digest.is_published,
    )


@router.get("", response_model=List[DigestRead])
def list_digests(db: Session = Depends(get_db)):
    digests = db.query(WeeklyDigest).order_by(WeeklyDigest.week_start.desc()).all()
    return [_to_digest_read(d, db) for d in digests]


@router.get("/{digest_id}", response_model=DigestRead)
def get_digest(digest_id: str, db: Session = Depends(get_db)):
    digest = db.query(WeeklyDigest).filter(WeeklyDigest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return _to_digest_read(digest, db)


@router.post(
    "/generate", response_model=DigestRead, status_code=status.HTTP_201_CREATED
)
def generate_digest(db: Session = Depends(get_db)):
    from app.digester.pipeline import generate_digest as run_pipeline

    digest = run_pipeline(db)
    return _to_digest_read(digest, db)
