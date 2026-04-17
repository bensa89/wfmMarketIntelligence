from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.schemas.discovered_page import DiscoveredPageRead, DiscoveredPageUpdate

router = APIRouter()


@router.get("", response_model=List[DiscoveredPageRead])
def list_discovered_pages(source_id: str, db: Session = Depends(get_db)):
    return (
        db.query(DiscoveredPage)
        .filter(DiscoveredPage.source_id == source_id)
        .order_by(DiscoveredPage.discovered_at.desc())
        .all()
    )


@router.patch("/{page_id}", response_model=DiscoveredPageRead)
def update_discovered_page(
    page_id: str, payload: DiscoveredPageUpdate, db: Session = Depends(get_db)
):
    page = db.query(DiscoveredPage).filter(DiscoveredPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="DiscoveredPage not found")
    page.is_active = payload.is_active
    if not payload.is_active:
        page.status = DiscoveredPageStatus.ignored
    db.commit()
    db.refresh(page)
    return page


@router.delete("/{page_id}", response_model=DiscoveredPageRead)
def delete_discovered_page(page_id: str, db: Session = Depends(get_db)):
    page = db.query(DiscoveredPage).filter(DiscoveredPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="DiscoveredPage not found")
    db.delete(page)
    db.commit()
    return page
