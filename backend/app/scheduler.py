import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def startup_scheduler(engine) -> BackgroundScheduler:
    global _scheduler
    jobstores = {"default": SQLAlchemyJobStore(engine=engine)}
    _scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
    _scheduler.start()
    logger.info("APScheduler started")
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("APScheduler stopped")


def apply_schedule(config) -> None:
    if _scheduler is None or not _scheduler.running:
        return

    # --- Crawl job ---
    if _scheduler.get_job("job_crawl"):
        _scheduler.remove_job("job_crawl")

    if config.crawl_enabled:
        hour, minute = map(int, config.crawl_time.split(":"))
        _scheduler.add_job(
            scheduled_crawl_job,
            CronTrigger(
                day_of_week=config.crawl_day_of_week,
                hour=hour,
                minute=minute,
                timezone=config.crawl_timezone,
            ),
            id="job_crawl",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Crawl job scheduled: day=%s time=%s", config.crawl_day_of_week, config.crawl_time)

    # --- Digest job (only when not tied to crawl) ---
    if _scheduler.get_job("job_digest"):
        _scheduler.remove_job("job_digest")

    if config.digest_enabled and not config.digest_after_crawl:
        hour, minute = map(int, config.digest_time.split(":"))
        _scheduler.add_job(
            scheduled_digest_job,
            CronTrigger(
                day_of_week=config.digest_day_of_week,
                hour=hour,
                minute=minute,
                timezone=config.crawl_timezone,
            ),
            id="job_digest",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Digest job scheduled: day=%s time=%s", config.digest_day_of_week, config.digest_time)


def get_next_run(job_id: str) -> Optional[str]:
    if _scheduler is None or not _scheduler.running:
        return None
    job = _scheduler.get_job(job_id)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None


def scheduled_crawl_job() -> None:
    from app.database import SessionLocal
    from app.models.source import Source
    from app.models.schedule import ScheduleConfig
    from app.models.crawl_run import CrawlRun
    from app.routers.crawl import _create_crawl_run, _run_crawl_background

    logger.info("Scheduled crawl job started")

    db = SessionLocal()
    crawl_run_id = None
    source_ids = []
    config = None
    try:
        active_sources = (
            db.query(Source)
            .filter(Source.is_active == True)  # noqa: E712
            .order_by(Source.last_crawled_at.asc().nullsfirst())
            .all()
        )
        if not active_sources:
            logger.info("Scheduled crawl: no active sources, skipping")
            return
        source_ids = [s.id for s in active_sources]
        crawl_run = _create_crawl_run(source_ids, db)
        crawl_run_id = crawl_run.id
        config = db.query(ScheduleConfig).filter(ScheduleConfig.id == 1).first()
    finally:
        db.close()

    if not crawl_run_id:
        return

    # Run crawl synchronously — APScheduler executes jobs in a threadpool
    _run_crawl_background(crawl_run_id, source_ids)
    logger.info("Scheduled crawl job finished: run_id=%s", crawl_run_id)

    # Generate digest if configured
    digest_generated = False
    post_crawl_digest = None
    if config and config.digest_after_crawl:
        try:
            from app.digester.pipeline import generate_digest
            with SessionLocal() as digest_db:
                post_crawl_digest = generate_digest(digest_db)
                digest_generated = True
            logger.info("Post-crawl digest generated: id=%s", post_crawl_digest.id)
        except Exception as exc:
            logger.exception("Post-crawl digest failed: %s", exc)

    # Send email report
    if config and config.email_enabled and config.email_recipients:
        try:
            db2 = SessionLocal()
            try:
                crawl_run = db2.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
                stats = _build_crawl_stats(crawl_run)
            finally:
                db2.close()

            stats["digest_generated"] = digest_generated
            from app.notifications.email import send_crawl_report
            send_crawl_report(
                smtp_host=config.smtp_host,
                smtp_port=config.smtp_port,
                smtp_user=config.smtp_user,
                smtp_password=config.smtp_password,
                smtp_from=config.smtp_from,
                recipients=config.email_recipients,
                crawl_stats=stats,
            )
            logger.info("Crawl report email sent to %d recipients", len(config.email_recipients))
        except Exception as exc:
            logger.exception("Failed to send crawl report email: %s", exc)

        if post_crawl_digest:
            logger.info("Sending post-crawl digest email: digest_id=%s to %d recipients",
                        post_crawl_digest.id, len(config.email_recipients))
            try:
                from app.notifications.email import send_digest_email
                from app.config import settings
                extras = _build_digest_email_extras(post_crawl_digest, settings.app_base_url)
                send_digest_email(
                    smtp_host=config.smtp_host,
                    smtp_port=config.smtp_port,
                    smtp_user=config.smtp_user,
                    smtp_password=config.smtp_password,
                    smtp_from=config.smtp_from,
                    recipients=config.email_recipients,
                    digest=post_crawl_digest,
                    app_base_url=settings.app_base_url,
                    **extras,
                )
                logger.info("Post-crawl digest email sent to %d recipients", len(config.email_recipients))
            except Exception as exc:
                logger.exception("Failed to send post-crawl digest email: %s", exc)
        elif digest_generated is False and config.digest_after_crawl:
            logger.warning("digest_after_crawl enabled but post_crawl_digest is None — digest generation likely failed")


def scheduled_digest_job() -> None:
    from app.database import SessionLocal
    from app.digester.pipeline import generate_digest
    from app.models.schedule import ScheduleConfig

    logger.info("Scheduled digest job started")
    digest = None
    config = None
    with SessionLocal() as db:
        digest = generate_digest(db)
        config = db.query(ScheduleConfig).filter(ScheduleConfig.id == 1).first()
    logger.info("Scheduled digest job finished")

    if config and config.email_enabled and config.email_recipients and digest:
        logger.info("Sending scheduled digest email: digest_id=%s to %d recipients",
                    digest.id, len(config.email_recipients))
        try:
            from app.notifications.email import send_digest_email
            from app.config import settings
            extras = _build_digest_email_extras(digest, settings.app_base_url)
            send_digest_email(
                smtp_host=config.smtp_host,
                smtp_port=config.smtp_port,
                smtp_user=config.smtp_user,
                smtp_password=config.smtp_password,
                smtp_from=config.smtp_from,
                recipients=config.email_recipients,
                digest=digest,
                app_base_url=settings.app_base_url,
                **extras,
            )
            logger.info("Digest email sent to %d recipients", len(config.email_recipients))
        except Exception as exc:
            logger.exception("Failed to send digest email: %s", exc)


def _build_digest_email_extras(digest, app_base_url: str) -> dict:
    from datetime import datetime, time as dt_time
    from app.database import SessionLocal
    from app.models.company import Company
    from app.models.signal import Signal
    with SessionLocal() as db:
        companies = db.query(Company).filter(Company.logo_path.isnot(None)).all()
        company_logos = {
            c.name: f"{app_base_url}/static/{c.logo_path}"
            for c in companies if c.logo_path
        }
        new_signals_count = db.query(Signal).filter(
            Signal.created_at >= datetime.combine(digest.week_start, dt_time.min),
            Signal.created_at <= datetime.combine(digest.week_end, dt_time.max),
        ).count()
    return {"company_logos": company_logos, "new_signals_count": new_signals_count}


def _build_crawl_stats(crawl_run) -> dict:
    from datetime import datetime, timezone

    started = crawl_run.started_at
    finished = crawl_run.finished_at or datetime.now(timezone.utc)

    if started and finished:
        # started_at may be naive (no timezone), normalise
        if hasattr(started, "tzinfo") and started.tzinfo is None:
            from datetime import timezone as tz
            finished_naive = finished.replace(tzinfo=None) if hasattr(finished, "tzinfo") else finished
            secs = int((finished_naive - started).total_seconds())
        else:
            secs = int((finished - started).total_seconds())
        mins, s = divmod(abs(secs), 60)
        duration_str = f"{mins}m {s:02d}s"
    else:
        duration_str = "?"

    return {
        "date": started.strftime("%d.%m.%Y") if started else "?",
        "time": started.strftime("%H:%M") if started else "?",
        "sources_total": crawl_run.total_sources or 0,
        "errors": crawl_run.total_errors or 0,
        "duration": duration_str,
    }
