from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models.source import Source
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate

router = APIRouter()


def _attach_summary(source: Source, db: Session) -> dict:
    rows = (
        db.query(DiscoveredPage.status, func.count(DiscoveredPage.id))
        .filter(DiscoveredPage.source_id == source.id)
        .group_by(DiscoveredPage.status)
        .all()
    )
    summary = {status.value: count for status, count in rows}
    for s in DiscoveredPageStatus:
        if s.value not in summary:
            summary[s.value] = 0
    return summary


@router.get("", response_model=List[SourceRead])
def list_sources(company_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Source)
    if company_id:
        query = query.filter(Source.company_id == company_id)
    sources = query.all()
    sources_with_summary = []
    for source in sources:
        source_dict = SourceRead.model_validate(source).model_dump()
        source_dict["discovered_pages_summary"] = _attach_summary(source, db)
        sources_with_summary.append(source_dict)
    return sources_with_summary


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="URL already exists")
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    result = SourceRead.model_validate(source).model_dump()
    result["discovered_pages_summary"] = {}
    return result


@router.put("/{source_id}", response_model=SourceRead)
def update_source(source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    result = SourceRead.model_validate(source).model_dump()
    result["discovered_pages_summary"] = _attach_summary(source, db)
    return result


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
