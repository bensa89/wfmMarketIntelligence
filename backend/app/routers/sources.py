from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.source import Source
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate


class SourceSearchResult(BaseModel):
    source: SourceRead
    matching_subsites: List[str] = []


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


@router.get("/search", response_model=List[SourceSearchResult])
def search_sources(q: str, db: Session = Depends(get_db)):
    pattern = f"%{q}%"
    matching_sources = db.query(Source).filter(Source.url.ilike(pattern)).all()
    source_ids_with_subsite_match = (
        db.query(DiscoveredPage.source_id)
        .filter(DiscoveredPage.url.ilike(pattern))
        .distinct()
        .subquery()
    )
    subsite_sources = (
        db.query(Source)
        .filter(Source.id.in_(db.query(source_ids_with_subsite_match.c.source_id)))
        .all()
    )
    all_sources = {s.id: s for s in matching_sources}
    for s in subsite_sources:
        all_sources.setdefault(s.id, s)

    subsite_urls_by_source = {}
    if subsite_sources:
        rows = (
            db.query(DiscoveredPage.source_id, DiscoveredPage.url)
            .filter(
                DiscoveredPage.source_id.in_([s.id for s in subsite_sources]),
                DiscoveredPage.url.ilike(pattern),
            )
            .all()
        )
        for source_id, url in rows:
            subsite_urls_by_source.setdefault(source_id, []).append(url)

    results = []
    for source in all_sources.values():
        source_dict = SourceRead.model_validate(source).model_dump()
        source_dict["discovered_pages_summary"] = _attach_summary(source, db)
        results.append(
            SourceSearchResult(
                source=source_dict,
                matching_subsites=subsite_urls_by_source.get(source.id, []),
            )
        )
    return results


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
