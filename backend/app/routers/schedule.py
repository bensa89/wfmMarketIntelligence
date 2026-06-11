import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schedule import ScheduleConfig
from app.schemas.schedule import ScheduleConfigUpdate, ScheduleConfigRead, ScheduleStatusRead
from app.scheduler import apply_schedule, get_next_run

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_or_create_config(db: Session) -> ScheduleConfig:
    config = db.query(ScheduleConfig).filter(ScheduleConfig.id == 1).first()
    if config is None:
        config = ScheduleConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("", response_model=ScheduleStatusRead)
def get_schedule(db: Session = Depends(get_db)):
    config = _get_or_create_config(db)
    return ScheduleStatusRead(
        config=ScheduleConfigRead.model_validate(config, from_attributes=True),
        next_crawl=get_next_run("job_crawl"),
        next_digest=get_next_run("job_digest"),
    )


@router.put("", response_model=ScheduleStatusRead)
def update_schedule(payload: ScheduleConfigUpdate, db: Session = Depends(get_db)):
    config = _get_or_create_config(db)
    for field, value in payload.model_dump().items():
        setattr(config, field, value)
    db.commit()
    db.refresh(config)
    apply_schedule(config)
    return ScheduleStatusRead(
        config=ScheduleConfigRead.model_validate(config, from_attributes=True),
        next_crawl=get_next_run("job_crawl"),
        next_digest=get_next_run("job_digest"),
    )


@router.post("/test-email")
def test_email(db: Session = Depends(get_db)):
    from app.notifications.email import send_crawl_report

    config = _get_or_create_config(db)

    if not config.email_recipients:
        raise HTTPException(status_code=400, detail="Keine Empfänger konfiguriert")

    try:
        send_crawl_report(
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password,
            smtp_from=config.smtp_from,
            recipients=config.email_recipients,
            crawl_stats={
                "date": "Test",
                "time": "00:00",
                "sources_total": 0,
                "errors": 0,
                "duration": "0m 00s",
                "digest_generated": False,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"status": "sent", "recipients": config.email_recipients}
