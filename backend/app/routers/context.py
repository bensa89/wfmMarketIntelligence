import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.context import InternalCompanyContext
from app.models.external_company_view import ExternalCompanyView
from app.schemas.context import ContextRead, ContextUpdate
from app.schemas.external_company_view import ExternalCompanyViewRead

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_or_create_context(db: Session) -> InternalCompanyContext:
    ctx = db.query(InternalCompanyContext).first()
    if not ctx:
        ctx = InternalCompanyContext()
        db.add(ctx)
        db.commit()
        db.refresh(ctx)
    return ctx


@router.get("", response_model=ContextRead)
def get_context(db: Session = Depends(get_db)):
    return _get_or_create_context(db)


@router.put("", response_model=ContextRead)
def update_context(payload: ContextUpdate, db: Session = Depends(get_db)):
    ctx = _get_or_create_context(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ctx, field, value)
    db.commit()
    db.refresh(ctx)
    return ctx


@router.get("/external-view", response_model=ExternalCompanyViewRead)
def get_external_view(db: Session = Depends(get_db)):
    view = db.query(ExternalCompanyView).first()
    if not view:
        logger.info("GET /context/external-view — no external view found")
        raise HTTPException(status_code=404, detail="No external view synthesized yet")
    logger.info(
        "GET /context/external-view — returning view [signals_used=%d generated_at=%s]",
        view.signal_count_used or 0,
        view.generated_at,
    )
    return view


@router.post("/synthesize-external-view", response_model=ExternalCompanyViewRead)
def synthesize_external_view(db: Session = Depends(get_db)):
    from app.synthesizer.pipeline import run_synthesis
    logger.info("POST /context/synthesize-external-view — synthesis triggered")
    try:
        view = run_synthesis(db)
    except ValueError as exc:
        logger.warning("POST /context/synthesize-external-view — failed: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    logger.info(
        "POST /context/synthesize-external-view — done [signals_used=%d id=%s]",
        view.signal_count_used or 0,
        view.id,
    )
    return view
