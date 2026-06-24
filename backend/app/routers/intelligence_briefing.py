from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intelligence_briefing import IntelligenceBriefing
from app.schemas.intelligence_briefing import IntelligenceBriefingRead
from app.assessor.intel_briefing import generate_intelligence_briefing, curate_risks_opportunities_watchpoints

router = APIRouter()


@router.get("/latest", response_model=IntelligenceBriefingRead)
def get_latest(db: Session = Depends(get_db)):
    briefing = (
        db.query(IntelligenceBriefing)
        .order_by(IntelligenceBriefing.generated_at.desc())
        .first()
    )
    if not briefing:
        raise HTTPException(status_code=404, detail="No intelligence briefing found")
    return briefing


@router.post("/generate", response_model=IntelligenceBriefingRead)
def generate(db: Session = Depends(get_db)):
    content, recommendations, signal_count, assessment_count = generate_intelligence_briefing(db)
    curated_risks, curated_opportunities, curated_watchpoints = curate_risks_opportunities_watchpoints(db)
    briefing = IntelligenceBriefing(
        content=content,
        signal_count=signal_count,
        assessment_count=assessment_count,
        generated_at=datetime.now(timezone.utc),
        curated_risks=curated_risks or None,
        curated_opportunities=curated_opportunities or None,
        curated_watchpoints=curated_watchpoints or None,
        curated_recommendations=recommendations or None,
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing
