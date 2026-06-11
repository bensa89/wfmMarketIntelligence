# Automation & Scheduling — Design Spec

**Date:** 2026-06-11  
**Status:** Approved  
**Scope:** Automated crawl scheduling, digest generation, and e-mail status notifications

---

## Overview

Add a configurable automation layer to the WFM Market Intelligence Hub so that crawling and digest generation run on a recurring schedule without manual intervention. Admins configure the schedule via a new Admin page. After each crawl, an optional e-mail status report is sent via SMTP.

---

## 1. Architecture

### Scheduler: APScheduler (embedded in FastAPI)

- Library: `apscheduler>=3.10` added to `requirements.txt`
- Job store: `SQLAlchemyJobStore` using the existing PostgreSQL connection — schedule jobs survive restarts
- Scheduler lifecycle: started and shut down via FastAPI `lifespan` context manager in `main.py`
- Two registered jobs:
  - `job_crawl` — triggers `POST /api/crawl/start` logic directly (calls the same function used by the endpoint, not an HTTP call)
  - `job_digest` — triggers `POST /api/digests/generate` logic directly
- On startup: scheduler reads `ScheduleConfig` from DB and registers/reschedules jobs as needed
- On config save (`PUT /api/schedule`): jobs are immediately rescheduled via `scheduler.reschedule_job()`

### E-Mail: Python `smtplib` (stdlib, no new dependency)

- Module: `backend/app/notifications/email.py`
- Called at the end of `job_crawl` if `email_enabled=True`
- Content: plain-text crawl status report (sources crawled, new documents, errors, duration)
- SMTP credentials stored in `ScheduleConfig` (password stored as-is in DB, internal tool)

---

## 2. Data Model

### New model: `ScheduleConfig` (`backend/app/models/schedule.py`)

Single row in DB (singleton pattern: always ID=1, upserted on save).

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | int PK | 1 | Always 1 |
| `crawl_enabled` | bool | false | Automated crawl active |
| `crawl_day_of_week` | int (0–6) | 0 | Monday=0 … Sunday=6 |
| `crawl_time` | str (HH:MM) | "06:00" | Time of crawl |
| `crawl_timezone` | str | "Europe/Berlin" | Timezone for crawl job |
| `digest_after_crawl` | bool | true | Auto-generate digest after crawl |
| `digest_enabled` | bool | false | Digest has own independent schedule |
| `digest_day_of_week` | int (0–6) | 1 | Tuesday=1 |
| `digest_time` | str (HH:MM) | "08:00" | Time of digest job |
| `email_enabled` | bool | false | Send e-mail notifications |
| `email_recipients` | JSON (list[str]) | [] | List of recipient addresses |
| `smtp_host` | str | "" | SMTP server hostname |
| `smtp_port` | int | 587 | SMTP port |
| `smtp_user` | str | "" | SMTP username |
| `smtp_password` | str | "" | SMTP password |
| `smtp_from` | str | "" | Sender address |
| `updated_at` | datetime | now() | Last config save |

### Alembic migration

New migration: `add_schedule_config` — creates `schedule_config` table and inserts default row (ID=1, all disabled).

APScheduler also creates its own `apscheduler_jobs` table automatically via `SQLAlchemyJobStore`.

---

## 3. Backend API

New router: `backend/app/routers/schedule.py`, mounted at `/api/schedule`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/schedule` | Return current config + next scheduled run times for both jobs |
| `PUT` | `/api/schedule` | Save config, immediately reschedule jobs |
| `POST` | `/api/schedule/test-email` | Send test e-mail to configured recipients |

Response for `GET` includes:
```json
{
  "config": { ... all ScheduleConfig fields ... },
  "next_crawl": "2026-06-16T06:00:00+02:00",
  "next_digest": "2026-06-17T08:00:00+02:00"
}
```

`next_crawl` / `next_digest` are `null` if the respective job is disabled.

### Scheduler module: `backend/app/scheduler.py`

```
scheduler = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(...)})

def apply_schedule(config: ScheduleConfig):
    # Remove existing jobs, re-add based on config

def get_scheduler() -> BackgroundScheduler:
    return scheduler
```

Integrated into `main.py` lifespan:
```python
@asynccontextmanager
async def lifespan(app):
    scheduler.start()
    apply_schedule(load_config_from_db())
    yield
    scheduler.shutdown()
```

---

## 4. Frontend

### New page: `frontend/src/pages/ScheduleAdmin.tsx`

Route: `/admin/schedule`

Four sections rendered as cards:

**Section 1 — Crawl-Zeitplan**
- Toggle: "Automatischer Crawl aktiv"
- 7-Button Wochentag-Picker (Mo–So), disabled when toggle off
- Time input HH:MM, disabled when toggle off
- Timezone select (list of common European zones), default `Europe/Berlin`
- Info line: "Nächste Ausführung: …" (from API, null = "nicht geplant")

**Section 2 — Digest-Einstellungen**
- Checkbox: "Digest direkt nach Crawl generieren"
- When checked: `digest_enabled` independent schedule is ignored entirely (no double-run)
- When unchecked: shows own Wochentag-Picker + Uhrzeit (same pattern as Section 1), with own toggle "Digest-Zeitplan aktiv"
- Info line: "Nächste Digest-Generierung: …"

**Section 3 — E-Mail-Benachrichtigungen**
- Toggle: "E-Mail-Versand nach Crawl aktiv"
- Textarea: "Empfänger" (one address per line), disabled when toggle off
- SMTP fields (shown when toggle on): Host, Port, Absender, Benutzername, Passwort (type=password)
- Button: "Test-E-Mail senden" → calls `POST /api/schedule/test-email`, shows success/error toast

**Section 4 — Speichern**
- "Einstellungen speichern" button → `PUT /api/schedule`
- Shows last saved timestamp ("Zuletzt gespeichert: …")

### Navigation update: `frontend/src/components/Layout.tsx`

Add sidebar entry "Automation" under the existing "Admin" section, pointing to `/admin/schedule`.

---

## 5. E-Mail Notification Content

Plain-text e-mail sent after each automated crawl:

```
Subject: [WFM Intel] Crawl abgeschlossen – <date>

Crawl-Bericht vom <date> <time>

Quellen gecrawlt:   12
Neue Dokumente:      5
Fehler:              1
Dauer:             4m 32s

Details: http://<app-url>/crawl-runs/<run-id>
```

If `digest_after_crawl=True`, an additional line is appended:
```
Weekly Digest wurde automatisch generiert.
```

---

## 6. Error Handling

- If a scheduled crawl job fails entirely: log the error, do not send e-mail (no partial report)
- If SMTP send fails: log warning, do not crash the crawl job
- If `test-email` SMTP fails: return 400 with error message to frontend
- APScheduler `misfire_grace_time=3600` — if the server was down during the scheduled time, the job fires once within 1 hour of coming back online

---

## 7. Dependencies Added

- `apscheduler>=3.10` — to `backend/requirements.txt`
- No other new dependencies (smtplib is stdlib)

---

## 8. Out of Scope

- Per-source scheduling (all active sources crawled together)
- Retry logic for individual failed sources within a crawl
- E-mail HTML templates (plain text only)
- Multiple schedule profiles
- Webhook / Slack notifications
