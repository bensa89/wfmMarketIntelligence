from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.crawl_run import CrawlRun
from app.schemas.crawl_run import CrawlRunRead, CrawlRunListRead

router = APIRouter()


@router.get("/", response_model=List[CrawlRunListRead])
def list_crawl_runs(
    status: Optional[str] = Query(None),
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    query = db.query(CrawlRun).order_by(CrawlRun.started_at.desc())
    if status:
        query = query.filter(CrawlRun.status == status)
    return query.offset(offset).limit(limit).all()


@router.get("/{crawl_run_id}", response_model=CrawlRunRead)
def get_crawl_run(crawl_run_id: str, db: Session = Depends(get_db)):
    crawl_run = (
        db.query(CrawlRun)
        .options(joinedload(CrawlRun.sources))
        .filter(CrawlRun.id == crawl_run_id)
        .first()
    )
    if not crawl_run:
        raise HTTPException(status_code=404, detail="CrawlRun not found")
    return crawl_run
