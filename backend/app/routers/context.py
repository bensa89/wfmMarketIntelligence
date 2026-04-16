from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.context import InternalCompanyContext
from app.schemas.context import ContextRead, ContextUpdate

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
