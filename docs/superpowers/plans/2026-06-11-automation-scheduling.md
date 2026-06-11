# Automation & Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add APScheduler-based automated crawl + digest scheduling with SMTP email notifications, configurable via a new `/admin/schedule` frontend page.

**Architecture:** `BackgroundScheduler` (APScheduler 3.x) runs inside the FastAPI process, started in a lifespan context manager. Jobs are persisted in PostgreSQL via `SQLAlchemyJobStore`. A `ScheduleConfig` singleton (always ID=1) stores user preferences. A new React page exposes all settings.

**Tech Stack:** APScheduler 3.10, smtplib (stdlib), FastAPI lifespan, React + React Query, SQLAlchemy 2.0, lucide-react

**Test commands** (always run inside Docker):
```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/<file> -v
```

---

## File Map

**New backend:**
- `backend/app/models/schedule.py` — ScheduleConfig model
- `backend/app/notifications/__init__.py` — package marker
- `backend/app/notifications/email.py` — send_crawl_report()
- `backend/app/scheduler.py` — APScheduler instance, apply_schedule, job functions
- `backend/app/schemas/schedule.py` — Pydantic v2 schemas
- `backend/app/routers/schedule.py` — GET/PUT /api/schedule, POST /api/schedule/test-email

**Modified backend:**
- `backend/requirements.txt` — add apscheduler==3.10.4
- `backend/app/models/__init__.py` — import ScheduleConfig
- `backend/app/main.py` — add lifespan, include schedule router

**New tests:**
- `backend/tests/test_email.py`
- `backend/tests/test_scheduler.py`
- `backend/tests/test_schedule_router.py`

**New frontend:**
- `frontend/src/pages/ScheduleAdmin.tsx`

**Modified frontend:**
- `frontend/src/App.tsx` — add /admin/schedule route
- `frontend/src/components/Layout.tsx` — add Automation nav entry

---

## Task 1: ScheduleConfig model + APScheduler dependency

**Files:**
- Create: `backend/app/models/schedule.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add APScheduler to requirements**

In `backend/requirements.txt`, add after `python-dotenv==1.0.1`:
```
apscheduler==3.10.4
```

- [ ] **Step 2: Create the ScheduleConfig model**

Create `backend/app/models/schedule.py`:
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ScheduleConfig(Base):
    __tablename__ = "schedule_config"

    id = Column(Integer, primary_key=True, default=1)
    crawl_enabled = Column(Boolean, nullable=False, default=False)
    crawl_day_of_week = Column(Integer, nullable=False, default=0)  # 0=Monday
    crawl_time = Column(String(5), nullable=False, default="06:00")  # HH:MM
    crawl_timezone = Column(String(50), nullable=False, default="Europe/Berlin")
    digest_after_crawl = Column(Boolean, nullable=False, default=True)
    digest_enabled = Column(Boolean, nullable=False, default=False)
    digest_day_of_week = Column(Integer, nullable=False, default=1)  # 1=Tuesday
    digest_time = Column(String(5), nullable=False, default="08:00")
    email_enabled = Column(Boolean, nullable=False, default=False)
    email_recipients = Column(JSON, nullable=False, default=list)
    smtp_host = Column(String(255), nullable=False, default="")
    smtp_port = Column(Integer, nullable=False, default=587)
    smtp_user = Column(String(255), nullable=False, default="")
    smtp_password = Column(String(255), nullable=False, default="")
    smtp_from = Column(String(255), nullable=False, default="")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

- [ ] **Step 3: Register model in models/__init__.py**

At the end of `backend/app/models/__init__.py`, add:
```python
from app.models.schedule import ScheduleConfig  # noqa: F401
```

And add `"ScheduleConfig"` to the `__all__` list.

- [ ] **Step 4: Install dependency inside Docker**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend pip install apscheduler==3.10.4
```

Expected: `Successfully installed apscheduler-3.10.4`

- [ ] **Step 5: Verify model is registered**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -c "from app.models import ScheduleConfig; print('OK:', ScheduleConfig.__tablename__)"
```

Expected: `OK: schedule_config`

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/models/schedule.py backend/app/models/__init__.py
git commit -m "feat: add ScheduleConfig model and apscheduler dependency"
```

---

## Task 2: Alembic migration

**Files:**
- Create: `backend/alembic/versions/<hash>_add_schedule_config.py` (generated)

- [ ] **Step 1: Generate migration**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add_schedule_config"
```

Expected: creates `backend/alembic/versions/<hash>_add_schedule_config.py`

- [ ] **Step 2: Verify generated migration**

Open the generated file. Confirm `upgrade()` contains `op.create_table("schedule_config", ...)` with all expected columns: `id`, `crawl_enabled`, `crawl_day_of_week`, `crawl_time`, `crawl_timezone`, `digest_after_crawl`, `digest_enabled`, `digest_day_of_week`, `digest_time`, `email_enabled`, `email_recipients`, `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`, `updated_at`.

- [ ] **Step 3: Apply migration**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend alembic upgrade head
```

Expected: `Running upgrade ... -> <hash>, add_schedule_config`

- [ ] **Step 4: Verify table exists**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -c "
from app.database import engine
from sqlalchemy import inspect
cols = [c['name'] for c in inspect(engine).get_columns('schedule_config')]
print(cols)
"
```

Expected: list including `crawl_enabled`, `email_recipients`, `smtp_host`.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: migration add_schedule_config table"
```

---

## Task 3: Email notification module (TDD)

**Files:**
- Create: `backend/app/notifications/__init__.py`
- Create: `backend/app/notifications/email.py`
- Create: `backend/tests/test_email.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_email.py`:
```python
import pytest
from unittest.mock import patch, MagicMock, call
from app.notifications.email import send_crawl_report


STATS = {
    "date": "11.06.2026",
    "time": "06:00",
    "sources_total": 5,
    "errors": 1,
    "duration": "2m 30s",
    "digest_generated": False,
}


def test_send_crawl_report_calls_smtp():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            crawl_stats=STATS,
        )

        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()


def test_send_crawl_report_message_contains_stats():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["a@b.com", "c@d.com"],
            crawl_stats=STATS,
        )

        msg = mock_server.send_message.call_args[0][0]
        body = msg.get_payload()
        assert "11.06.2026" in body
        assert "5" in body
        assert "2m 30s" in body
        assert msg["Subject"] == "[WFM Intel] Crawl abgeschlossen – 11.06.2026"
        assert "a@b.com" in msg["To"]


def test_send_crawl_report_includes_digest_line_when_generated():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        stats = {**STATS, "digest_generated": True}
        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            crawl_stats=stats,
        )

        msg = mock_server.send_message.call_args[0][0]
        assert "Digest" in msg.get_payload()


def test_send_crawl_report_skips_login_when_no_credentials():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            crawl_stats=STATS,
        )

        mock_server.login.assert_not_called()


def test_send_crawl_report_raises_on_smtp_failure():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.side_effect = ConnectionRefusedError("refused")

        with pytest.raises(ConnectionRefusedError):
            send_crawl_report(
                smtp_host="bad-host",
                smtp_port=587,
                smtp_user="",
                smtp_password="",
                smtp_from="from@example.com",
                recipients=["to@example.com"],
                crawl_stats=STATS,
            )
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_email.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.notifications'`

- [ ] **Step 3: Create the notifications package**

Create `backend/app/notifications/__init__.py` (empty file).

- [ ] **Step 4: Implement email module**

Create `backend/app/notifications/email.py`:
```python
import smtplib
import logging
from email.message import EmailMessage
from typing import List

logger = logging.getLogger(__name__)


def send_crawl_report(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    recipients: List[str],
    crawl_stats: dict,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"[WFM Intel] Crawl abgeschlossen – {crawl_stats['date']}"
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)

    lines = [
        f"Crawl-Bericht vom {crawl_stats['date']} {crawl_stats['time']}",
        "",
        f"Quellen gecrawlt:  {crawl_stats['sources_total']:>4}",
        f"Fehler:            {crawl_stats['errors']:>4}",
        f"Dauer:             {crawl_stats['duration']}",
    ]
    if crawl_stats.get("digest_generated"):
        lines += ["", "Weekly Digest wurde automatisch generiert."]

    msg.set_content("\n".join(lines))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        if smtp_port != 25:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_email.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/notifications/ backend/tests/test_email.py
git commit -m "feat: add email notification module for crawl status reports"
```

---

## Task 4: Scheduler module (TDD)

**Files:**
- Create: `backend/app/scheduler.py`
- Create: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_scheduler.py`:
```python
import pytest
from unittest.mock import MagicMock, patch, call
from app.models.schedule import ScheduleConfig


def _make_config(**kwargs) -> ScheduleConfig:
    defaults = dict(
        crawl_enabled=False,
        crawl_day_of_week=0,
        crawl_time="06:00",
        crawl_timezone="Europe/Berlin",
        digest_after_crawl=True,
        digest_enabled=False,
        digest_day_of_week=1,
        digest_time="08:00",
        email_enabled=False,
        email_recipients=[],
        smtp_host="",
        smtp_port=587,
        smtp_user="",
        smtp_password="",
        smtp_from="",
    )
    defaults.update(kwargs)
    return ScheduleConfig(**defaults)


def test_apply_schedule_adds_crawl_job_when_enabled():
    config = _make_config(crawl_enabled=True, crawl_day_of_week=0, crawl_time="06:00")

    mock_sched = MagicMock()
    mock_sched.running = True
    mock_sched.get_job.return_value = None

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    add_calls = mock_sched.add_job.call_args_list
    assert len(add_calls) == 1
    assert add_calls[0][1]["id"] == "job_crawl"


def test_apply_schedule_no_jobs_when_all_disabled():
    config = _make_config(crawl_enabled=False, digest_enabled=False)

    mock_sched = MagicMock()
    mock_sched.running = True
    mock_sched.get_job.return_value = None

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    mock_sched.add_job.assert_not_called()


def test_apply_schedule_adds_digest_job_when_independent_schedule():
    config = _make_config(
        crawl_enabled=False,
        digest_after_crawl=False,
        digest_enabled=True,
        digest_day_of_week=2,
        digest_time="08:00",
    )

    mock_sched = MagicMock()
    mock_sched.running = True
    mock_sched.get_job.return_value = None

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    add_calls = mock_sched.add_job.call_args_list
    assert len(add_calls) == 1
    assert add_calls[0][1]["id"] == "job_digest"


def test_apply_schedule_removes_existing_jobs_before_readding():
    config = _make_config(crawl_enabled=True)

    mock_sched = MagicMock()
    mock_sched.running = True
    # Simulate existing job
    mock_sched.get_job.return_value = MagicMock()

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    remove_calls = [c for c in mock_sched.remove_job.call_args_list]
    assert any(c[0][0] == "job_crawl" for c in remove_calls)


def test_apply_schedule_no_op_when_scheduler_not_running():
    config = _make_config(crawl_enabled=True)

    mock_sched = MagicMock()
    mock_sched.running = False

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    mock_sched.add_job.assert_not_called()


def test_apply_schedule_no_op_when_scheduler_is_none():
    config = _make_config(crawl_enabled=True)

    with patch("app.scheduler._scheduler", None):
        from app.scheduler import apply_schedule
        apply_schedule(config)  # must not raise
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_scheduler.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.scheduler'`

- [ ] **Step 3: Implement scheduler module**

Create `backend/app/scheduler.py`:
```python
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
    if config and config.digest_after_crawl:
        try:
            from app.digester.pipeline import generate_digest
            with SessionLocal() as digest_db:
                generate_digest(digest_db)
                digest_generated = True
            logger.info("Post-crawl digest generated")
        except Exception as exc:
            logger.warning("Post-crawl digest failed: %s", exc)

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
            logger.warning("Failed to send crawl report email: %s", exc)


def scheduled_digest_job() -> None:
    from app.database import SessionLocal
    from app.digester.pipeline import generate_digest

    logger.info("Scheduled digest job started")
    with SessionLocal() as db:
        generate_digest(db)
    logger.info("Scheduled digest job finished")


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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_scheduler.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: add APScheduler module with crawl and digest job functions"
```

---

## Task 5: Schedule API router + lifespan + wire into main.py (TDD)

**Files:**
- Create: `backend/app/schemas/schedule.py`
- Create: `backend/app/routers/schedule.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_schedule_router.py`

- [ ] **Step 1: Create Pydantic schemas**

Create `backend/app/schemas/schedule.py`:
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ScheduleConfigUpdate(BaseModel):
    crawl_enabled: bool = False
    crawl_day_of_week: int = Field(0, ge=0, le=6)
    crawl_time: str = "06:00"
    crawl_timezone: str = "Europe/Berlin"
    digest_after_crawl: bool = True
    digest_enabled: bool = False
    digest_day_of_week: int = Field(1, ge=0, le=6)
    digest_time: str = "08:00"
    email_enabled: bool = False
    email_recipients: List[str] = []
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


class ScheduleConfigRead(ScheduleConfigUpdate):
    updated_at: Optional[datetime] = None


class ScheduleStatusRead(BaseModel):
    config: ScheduleConfigRead
    next_crawl: Optional[str] = None
    next_digest: Optional[str] = None
```

- [ ] **Step 2: Write failing router tests**

Create `backend/tests/test_schedule_router.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


FULL_PAYLOAD = {
    "crawl_enabled": False,
    "crawl_day_of_week": 0,
    "crawl_time": "06:00",
    "crawl_timezone": "Europe/Berlin",
    "digest_after_crawl": True,
    "digest_enabled": False,
    "digest_day_of_week": 1,
    "digest_time": "08:00",
    "email_enabled": False,
    "email_recipients": [],
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
}


def test_get_schedule_returns_defaults(client):
    with patch("app.routers.schedule.apply_schedule"):
        response = client.get("/api/schedule")
    assert response.status_code == 200
    data = response.json()
    assert "config" in data
    assert data["config"]["crawl_enabled"] is False
    assert data["next_crawl"] is None
    assert data["next_digest"] is None


def test_put_schedule_saves_config(client):
    payload = {**FULL_PAYLOAD, "crawl_enabled": True, "crawl_time": "07:30"}

    with patch("app.routers.schedule.apply_schedule") as mock_apply:
        response = client.put("/api/schedule", json=payload)
        assert response.status_code == 200
        mock_apply.assert_called_once()

    # Verify persisted
    with patch("app.routers.schedule.apply_schedule"):
        get_response = client.get("/api/schedule")
    assert get_response.json()["config"]["crawl_enabled"] is True
    assert get_response.json()["config"]["crawl_time"] == "07:30"


def test_put_schedule_returns_updated_config(client):
    payload = {**FULL_PAYLOAD, "crawl_day_of_week": 4}

    with patch("app.routers.schedule.apply_schedule"):
        response = client.put("/api/schedule", json=payload)
    assert response.json()["config"]["crawl_day_of_week"] == 4


def test_put_schedule_rejects_invalid_day(client):
    payload = {**FULL_PAYLOAD, "crawl_day_of_week": 7}  # invalid: 0-6 only

    with patch("app.routers.schedule.apply_schedule"):
        response = client.put("/api/schedule", json=payload)
    assert response.status_code == 422


def test_test_email_returns_400_on_smtp_failure(client):
    # First configure email
    payload = {
        **FULL_PAYLOAD,
        "email_enabled": True,
        "email_recipients": ["test@example.com"],
        "smtp_host": "bad-host",
        "smtp_from": "from@example.com",
    }
    with patch("app.routers.schedule.apply_schedule"):
        client.put("/api/schedule", json=payload)

    with patch("app.notifications.email.send_crawl_report", side_effect=Exception("SMTP failed")):
        response = client.post("/api/schedule/test-email")
    assert response.status_code == 400
    assert "SMTP failed" in response.json()["detail"]


def test_test_email_returns_200_on_success(client):
    payload = {
        **FULL_PAYLOAD,
        "email_enabled": True,
        "email_recipients": ["test@example.com"],
        "smtp_host": "smtp.example.com",
        "smtp_from": "from@example.com",
    }
    with patch("app.routers.schedule.apply_schedule"):
        client.put("/api/schedule", json=payload)

    with patch("app.notifications.email.send_crawl_report"):
        response = client.post("/api/schedule/test-email")
    assert response.status_code == 200


def test_test_email_returns_400_when_no_recipients(client):
    with patch("app.routers.schedule.apply_schedule"):
        client.put("/api/schedule", json={**FULL_PAYLOAD, "email_enabled": True, "email_recipients": []})

    response = client.post("/api/schedule/test-email")
    assert response.status_code == 400
```

- [ ] **Step 3: Run tests — expect failure (router not yet created)**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_schedule_router.py -v
```

Expected: `FAILED` (import error or 404).

- [ ] **Step 4: Create the schedule router**

Create `backend/app/routers/schedule.py`:
```python
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
```

- [ ] **Step 5: Add lifespan to main.py**

In `backend/app/main.py`, add at the top (after existing imports):
```python
from contextlib import asynccontextmanager
```

Before the `app = FastAPI(...)` line, add:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, SessionLocal
    from app.models.schedule import ScheduleConfig
    from app import scheduler as sched_module

    db = SessionLocal()
    config = None
    try:
        config = db.query(ScheduleConfig).filter(ScheduleConfig.id == 1).first()
        if config is None:
            config = ScheduleConfig()
            db.add(config)
            db.commit()
            db.refresh(config)
    finally:
        db.close()

    sched_module.startup_scheduler(engine)
    sched_module.apply_schedule(config)

    yield

    sched_module.shutdown_scheduler()
```

Change the `app = FastAPI(...)` line to:
```python
app = FastAPI(
    title="WFM Market Intelligence Hub",
    version="1.0.0",
    dependencies=[Depends(verify_credentials)],
    lifespan=lifespan,
)
```

- [ ] **Step 6: Wire schedule router into main.py**

In `backend/app/main.py`, add to the router imports block:
```python
from app.routers import (
    ...existing...,
    schedule,
)
```

And add after the other `app.include_router(...)` calls:
```python
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
```

- [ ] **Step 7: Run tests — expect pass**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_schedule_router.py -v
```

Expected: `7 passed`

- [ ] **Step 8: Run full test suite to check for regressions**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/schedule.py backend/app/routers/schedule.py backend/app/main.py backend/tests/test_schedule_router.py
git commit -m "feat: add schedule API router with GET/PUT config and test-email endpoints"
```

---

## Task 6: Frontend ScheduleAdmin page + routing + nav

**Files:**
- Create: `frontend/src/pages/ScheduleAdmin.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Verify the API fetch pattern used in the project**

Read `frontend/src/pages/SourcesAdmin.tsx` and `frontend/src/api/client.ts` (or `client.tsx`) to identify the correct function for authenticated API calls (e.g., `apiFetch`, `apiCall`, `fetchWithAuth`). The ScheduleAdmin page below uses `apiFetch` — replace with the actual function name if different.

- [ ] **Step 2: Create ScheduleAdmin page**

Create `frontend/src/pages/ScheduleAdmin.tsx`:
```tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../api/client';

const DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

const TIMEZONES = [
  'Europe/Berlin',
  'Europe/London',
  'Europe/Paris',
  'Europe/Zurich',
  'UTC',
];

interface ScheduleConfig {
  crawl_enabled: boolean;
  crawl_day_of_week: number;
  crawl_time: string;
  crawl_timezone: string;
  digest_after_crawl: boolean;
  digest_enabled: boolean;
  digest_day_of_week: number;
  digest_time: string;
  email_enabled: boolean;
  email_recipients: string[];
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  smtp_from: string;
  updated_at?: string;
}

interface ScheduleStatus {
  config: ScheduleConfig;
  next_crawl: string | null;
  next_digest: string | null;
}

const DEFAULT_CONFIG: ScheduleConfig = {
  crawl_enabled: false,
  crawl_day_of_week: 0,
  crawl_time: '06:00',
  crawl_timezone: 'Europe/Berlin',
  digest_after_crawl: true,
  digest_enabled: false,
  digest_day_of_week: 1,
  digest_time: '08:00',
  email_enabled: false,
  email_recipients: [],
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  smtp_from: '',
};

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
      <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">{title}</h2>
      {children}
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${
        checked ? 'bg-blue-600' : 'bg-slate-200'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

function DayPicker({ value, onChange, disabled }: { value: number; onChange: (v: number) => void; disabled?: boolean }) {
  return (
    <div className="flex gap-1">
      {DAYS.map((day, i) => (
        <button
          key={day}
          type="button"
          disabled={disabled}
          onClick={() => onChange(i)}
          className={`w-9 h-9 rounded-lg text-xs font-medium transition-colors ${
            value === i
              ? 'bg-blue-600 text-white'
              : disabled
              ? 'bg-slate-50 text-slate-300 cursor-not-allowed'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          {day}
        </button>
      ))}
    </div>
  );
}

function NextRunBadge({ label, time }: { label: string; time: string | null }) {
  if (!time) return <p className="text-xs text-slate-400">{label}: nicht geplant</p>;
  const d = new Date(time);
  return (
    <p className="text-xs text-slate-500">
      {label}:{' '}
      <span className="font-medium text-slate-700">
        {d.toLocaleDateString('de-DE', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' })}{' '}
        {d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}
      </span>
    </p>
  );
}

export default function ScheduleAdmin() {
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [testEmailLoading, setTestEmailLoading] = useState(false);

  const { data: status, isLoading } = useQuery<ScheduleStatus>({
    queryKey: ['schedule'],
    queryFn: () => apiFetch('/api/schedule'),
  });

  const [form, setForm] = useState<ScheduleConfig>(DEFAULT_CONFIG);

  // Sync form from API on first load
  const [synced, setSynced] = useState(false);
  if (status && !synced) {
    setForm(status.config);
    setSynced(true);
  }

  const saveMutation = useMutation({
    mutationFn: (payload: ScheduleConfig) =>
      apiFetch('/api/schedule', { method: 'PUT', body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
      setSynced(false);
      showToast('success', 'Einstellungen gespeichert');
    },
    onError: (err: Error) => showToast('error', err.message),
  });

  function showToast(type: 'success' | 'error', msg: string) {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3000);
  }

  async function handleTestEmail() {
    setTestEmailLoading(true);
    try {
      await apiFetch('/api/schedule/test-email', { method: 'POST' });
      showToast('success', 'Test-E-Mail gesendet');
    } catch (err: any) {
      showToast('error', err.message || 'Fehler beim Senden');
    } finally {
      setTestEmailLoading(false);
    }
  }

  const set = (key: keyof ScheduleConfig, value: any) =>
    setForm((f) => ({ ...f, [key]: value }));

  if (isLoading) return <div className="p-8 text-slate-400 text-sm">Lade…</div>;

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Automation</h1>
        <p className="text-sm text-slate-500 mt-1">Automatische Crawl- und Digest-Zeitpläne konfigurieren</p>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-lg text-sm font-medium shadow-lg ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Section 1: Crawl Schedule */}
      <SectionCard title="Crawl-Zeitplan">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700">Automatischer Crawl aktiv</span>
          <Toggle checked={form.crawl_enabled} onChange={(v) => set('crawl_enabled', v)} />
        </div>

        <div className={form.crawl_enabled ? '' : 'opacity-40 pointer-events-none'}>
          <label className="block text-xs font-medium text-slate-500 mb-2">Wochentag</label>
          <DayPicker
            value={form.crawl_day_of_week}
            onChange={(v) => set('crawl_day_of_week', v)}
            disabled={!form.crawl_enabled}
          />

          <div className="flex gap-4 mt-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Uhrzeit</label>
              <input
                type="time"
                value={form.crawl_time}
                onChange={(e) => set('crawl_time', e.target.value)}
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Zeitzone</label>
              <select
                value={form.crawl_timezone}
                onChange={(e) => set('crawl_timezone', e.target.value)}
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <NextRunBadge label="Nächste Ausführung" time={status?.next_crawl ?? null} />
      </SectionCard>

      {/* Section 2: Digest */}
      <SectionCard title="Digest-Einstellungen">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700">Digest direkt nach Crawl generieren</span>
          <Toggle checked={form.digest_after_crawl} onChange={(v) => set('digest_after_crawl', v)} />
        </div>

        {!form.digest_after_crawl && (
          <div className="border-t border-slate-100 pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-700">Eigener Digest-Zeitplan aktiv</span>
              <Toggle checked={form.digest_enabled} onChange={(v) => set('digest_enabled', v)} />
            </div>

            <div className={form.digest_enabled ? '' : 'opacity-40 pointer-events-none'}>
              <label className="block text-xs font-medium text-slate-500 mb-2">Wochentag</label>
              <DayPicker
                value={form.digest_day_of_week}
                onChange={(v) => set('digest_day_of_week', v)}
                disabled={!form.digest_enabled}
              />
              <div className="mt-3">
                <label className="block text-xs font-medium text-slate-500 mb-1">Uhrzeit</label>
                <input
                  type="time"
                  value={form.digest_time}
                  onChange={(e) => set('digest_time', e.target.value)}
                  className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        <NextRunBadge label="Nächste Digest-Generierung" time={status?.next_digest ?? null} />
      </SectionCard>

      {/* Section 3: Email */}
      <SectionCard title="E-Mail-Benachrichtigungen">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700">E-Mail-Versand nach Crawl aktiv</span>
          <Toggle checked={form.email_enabled} onChange={(v) => set('email_enabled', v)} />
        </div>

        {form.email_enabled && (
          <div className="space-y-3 border-t border-slate-100 pt-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Empfänger (eine Adresse pro Zeile)</label>
              <textarea
                rows={3}
                value={form.email_recipients.join('\n')}
                onChange={(e) =>
                  set(
                    'email_recipients',
                    e.target.value
                      .split('\n')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  )
                }
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="max@example.com&#10;lisa@example.com"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">SMTP-Host</label>
                <input
                  value={form.smtp_host}
                  onChange={(e) => set('smtp_host', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="smtp.example.com"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Port</label>
                <input
                  type="number"
                  value={form.smtp_port}
                  onChange={(e) => set('smtp_port', parseInt(e.target.value) || 587)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Absender</label>
                <input
                  value={form.smtp_from}
                  onChange={(e) => set('smtp_from', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="intel@example.com"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Benutzername</label>
                <input
                  value={form.smtp_user}
                  onChange={(e) => set('smtp_user', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">Passwort</label>
                <input
                  type="password"
                  value={form.smtp_password}
                  onChange={(e) => set('smtp_password', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={handleTestEmail}
              disabled={testEmailLoading}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
            >
              {testEmailLoading ? 'Sende…' : 'Test-E-Mail senden'}
            </button>
          </div>
        )}
      </SectionCard>

      {/* Section 4: Save */}
      <div className="flex items-center justify-between">
        <div>
          {form.updated_at && (
            <p className="text-xs text-slate-400">
              Zuletzt gespeichert:{' '}
              {new Date(form.updated_at).toLocaleString('de-DE')}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => saveMutation.mutate(form)}
          disabled={saveMutation.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {saveMutation.isPending ? 'Speichere…' : 'Einstellungen speichern'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add route in App.tsx**

In `frontend/src/App.tsx`, add the import:
```tsx
import ScheduleAdmin from './pages/ScheduleAdmin';
```

Add the route inside the authenticated `<Route>` block, after the `admin/sources` route:
```tsx
<Route path="admin/schedule" element={<ScheduleAdmin />} />
```

- [ ] **Step 4: Add nav entry in Layout.tsx**

In `frontend/src/components/Layout.tsx`, add `Clock` to the lucide-react import:
```tsx
import {
  LayoutDashboard,
  Users,
  TrendingUp,
  FileText,
  Settings,
  Search,
  Globe,
  LogOut,
  BarChart2,
  Zap,
  BookOpen,
  Clock,
} from 'lucide-react';
```

In the `navSections` array, under `label: 'Admin'`, add the Automation entry:
```tsx
{
  label: 'Admin',
  items: [
    { to: '/admin/sources', label: 'Quellen', icon: Settings },
    { to: '/admin/schedule', label: 'Automation', icon: Clock },
    { to: '/context', label: 'Kontext', icon: Globe },
    { to: '/how-it-works', label: "Wie funktioniert's?", icon: BookOpen },
  ],
},
```

- [ ] **Step 5: Verify the app starts and the page loads**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml up -d
```

Open `http://localhost:5173/admin/schedule` in the browser. Verify:
- Page loads without errors
- "Automation" appears in sidebar under Admin
- All four card sections are visible
- Save button sends PUT request (check browser DevTools Network tab)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ScheduleAdmin.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add ScheduleAdmin page with crawl, digest and email configuration"
```

---

## Final verification

- [ ] Run full backend test suite one last time:

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v
```

Expected: all tests pass (no regressions).

- [ ] Smoke-test the scheduler start by checking the backend logs after restart:

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml logs backend | grep -i scheduler
```

Expected: `APScheduler started`
