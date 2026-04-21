# backend/app/routers/briefings.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.crawl_briefing import CrawlBriefing
from app.schemas.crawl_briefing import CrawlBriefingRead, CrawlBriefingCreate
from app.analyser.briefing import generate_briefing_content

router = APIRouter()


@router.get("/latest", response_model=CrawlBriefingRead)
def get_latest_briefing(db: Session = Depends(get_db)):
    briefing = (
        db.query(CrawlBriefing)
        .order_by(CrawlBriefing.generated_at.desc())
        .first()
    )
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefing found")
    return briefing


@router.post("/generate", response_model=CrawlBriefingRead)
def generate_briefing(payload: CrawlBriefingCreate, db: Session = Depends(get_db)):
    content = generate_briefing_content(db, crawl_run_id=payload.crawl_run_id)
    briefing = CrawlBriefing(
        crawl_run_id=payload.crawl_run_id,
        content=content,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing
