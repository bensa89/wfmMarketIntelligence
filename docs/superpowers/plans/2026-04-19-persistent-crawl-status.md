# Persistent Crawl Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make crawl progress survive page refresh by persisting it in the database and reconnecting SSE streams with state replay.

**Architecture:** Add `CrawlRun` and `CrawlRunSource` models to persist crawl state. Modify the SSE crawl endpoint to create/run a CrawlRun and update DB at each step. On SSE connect, replay existing state from any running CrawlRun. Add REST endpoints for querying CrawlRuns. Frontend reconnects on page load by checking for active runs and re-subscribing to the SSE stream.

**Tech Stack:** Python, SQLAlchemy 2.0, Alembic, FastAPI, React 19, TanStack React Query 5, TypeScript

---

## File Structure

### Backend — New files
- `backend/app/models/crawl_run.py` — CrawlRun and CrawlRunSource models + enums
- `backend/app/schemas/crawl_run.py` — Pydantic schemas for CrawlRun REST API
- `backend/app/routers/crawl_runs.py` — REST endpoints for querying CrawlRuns
- `backend/tests/test_crawl_runs.py` — Tests for CrawlRun models + API endpoints + SSE reconnect

### Backend — Modified files
- `backend/app/models/__init__.py` — Register new models
- `backend/app/schemas/__init__.py` — Register new schemas
- `backend/app/routers/crawl.py` — SSE endpoints create/update CrawlRun, emit crawl_run_id, replay state on connect
- `backend/app/crawler/pipeline.py` — No changes needed (progress_callback already emits steps)
- `backend/app/main.py` — Mount crawl_runs router
- `backend/alembic/versions/` — New migration for crawl_runs + crawl_run_sources tables

### Frontend — Modified files
- `frontend/src/types/index.ts` — Add CrawlRun + CrawlRunSource types, update CrawlEvent with crawl_run_id
- `frontend/src/api/client.ts` — Add apiGet helpers (already has apiGet)
- `frontend/src/hooks/useCrawlStream.ts` — Check for active CrawlRun on mount, reconnect SSE with initial_state, store crawl_run_id
- `frontend/src/hooks/useActiveCrawlRun.ts` — New hook for Dashboard polling
- `frontend/src/components/CrawlProgressPanel.tsx` — No major changes (already handles state correctly)
- `frontend/src/pages/Dashboard.tsx` — Add active crawl banner via useActiveCrawlRun

---

### Task 1: CrawlRun and CrawlRunSource models

**Files:**
- Create: `backend/app/models/crawl_run.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the CrawlRun models**

Create `backend/app/models/crawl_run.py`:

```python
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class CrawlRunStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class CrawlRunSourceStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class CrawlRunStep(str, enum.Enum):
    fetching = "fetching"
    extracting = "extracting"
    analysing = "analysing"
    discovering = "discovering"


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(SAEnum(CrawlRunStatus), nullable=False, default=CrawlRunStatus.running)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    total_sources = Column(Integer, default=0)
    total_new = Column(Integer, default=0)
    total_skipped = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)

    sources = relationship(
        "CrawlRunSource", back_populates="crawl_run", cascade="all, delete-orphan"
    )


class CrawlRunSource(Base):
    __tablename__ = "crawl_run_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    crawl_run_id = Column(String(36), ForeignKey("crawl_runs.id"), nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    url = Column(String(2000), nullable=False)
    status = Column(SAEnum(CrawlRunSourceStatus), nullable=False, default=CrawlRunSourceStatus.pending)
    current_step = Column(SAEnum(CrawlRunStep), nullable=True)
    new_documents = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    error_message = Column(String(1000), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    crawl_run = relationship("CrawlRun", back_populates="sources")
    source = relationship("Source")
```

- [ ] **Step 2: Register models in `__init__.py`**

Modify `backend/app/models/__init__.py`:

```python
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.digest import WeeklyDigest
from app.models.context import InternalCompanyContext
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.models.search_query import SearchQuery
from app.models.search_run import SearchRun, SearchRunStatus
from app.models.search_result import SearchResult, SearchResultStatus
from app.models.source_candidate import SourceCandidate, SourceCandidateStatus
from app.models.crawl_run import CrawlRun, CrawlRunStatus, CrawlRunSource, CrawlRunSourceStatus, CrawlRunStep

__all__ = [
    "Company",
    "CompanyType",
    "Source",
    "SourceType",
    "Document",
    "Signal",
    "SignalType",
    "WeeklyDigest",
    "InternalCompanyContext",
    "DiscoveredPage",
    "DiscoveredPageStatus",
    "SearchQuery",
    "SearchRun",
    "SearchRunStatus",
    "SearchResult",
    "SearchResultStatus",
    "SourceCandidate",
    "SourceCandidateStatus",
    "CrawlRun",
    "CrawlRunStatus",
    "CrawlRunSource",
    "CrawlRunSourceStatus",
    "CrawlRunStep",
]
```

- [ ] **Step 3: Run tests to verify models register correctly**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS (existing model tests still pass)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/crawl_run.py backend/app/models/__init__.py
git commit -m "feat: add CrawlRun and CrawlRunSource models"
```

---

### Task 2: Alembic migration for crawl_runs tables

**Files:**
- Create: `backend/alembic/versions/<auto>_add_crawl_runs.py`

- [ ] **Step 1: Generate migration**

Run: `cd backend && alembic revision --autogenerate -m "add crawl_runs and crawl_run_sources"`

- [ ] **Step 2: Inspect the generated migration**

Read the generated file and verify it creates both `crawl_runs` and `crawl_run_sources` tables with all columns, enums, foreign keys, and the index on `crawl_run_sources.crawl_run_id`.

- [ ] **Step 3: Run migration**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add Alembic migration for crawl_runs tables"
```

---

### Task 3: CrawlRun schemas + REST endpoints

**Files:**
- Create: `backend/app/schemas/crawl_run.py`
- Create: `backend/app/routers/crawl_runs.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write CrawlRun schemas**

Create `backend/app/schemas/crawl_run.py`:

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CrawlRunSourceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    crawl_run_id: str
    source_id: str
    url: str
    status: str
    current_step: Optional[str] = None
    new_documents: int = 0
    skipped: int = 0
    errors: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class CrawlRunRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_sources: int = 0
    total_new: int = 0
    total_skipped: int = 0
    total_errors: int = 0
    sources: List[CrawlRunSourceRead] = []


class CrawlRunListRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_sources: int = 0
    total_new: int = 0
    total_skipped: int = 0
    total_errors: int = 0
```

- [ ] **Step 2: Write crawl_runs router**

Create `backend/app/routers/crawl_runs.py`:

```python
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.crawl_run import CrawlRun, CrawlRunStatus
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="CrawlRun not found")
    return crawl_run
```

- [ ] **Step 3: Register schemas in `__init__.py`**

Modify `backend/app/schemas/__init__.py` — add:

```python
from app.schemas.crawl_run import CrawlRunRead, CrawlRunListRead, CrawlRunSourceRead
```

- [ ] **Step 4: Mount router in `main.py`**

Add to `backend/app/main.py` router imports and mount:

```python
from app.routers import crawl_runs  # noqa: E402 — add to existing imports block
```

And add after existing router mounts:

```python
app.include_router(crawl_runs.router, prefix="/api/crawl-runs", tags=["crawl-runs"])
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/crawl_run.py backend/app/schemas/__init__.py backend/app/routers/crawl_runs.py backend/app/main.py
git commit -m "feat: add CrawlRun REST endpoints and schemas"
```

---

### Task 4: Modify SSE crawl endpoint to create/update CrawlRun + replay state on reconnect

**Files:**
- Modify: `backend/app/routers/crawl.py`

This is the core change. The SSE endpoint must:
1. On stream start: cancel any existing running CrawlRun, create a new CrawlRun + CrawlRunSource rows
2. During crawl: update CrawlRunSource status/step in DB at each event
3. On stream connect (GET): check if a running CrawlRun exists — if so, send `initial_state` event then attach to live stream

- [ ] **Step 1: Rewrite `crawl.py` with CrawlRun persistence and reconnect support**

Replace the entire content of `backend/app/routers/crawl.py`:

```python
import asyncio
import json
import threading
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.source import Source
from app.models.crawl_run import CrawlRun, CrawlRunStatus, CrawlRunSource, CrawlRunSourceStatus, CrawlRunStep
from app.crawler.pipeline import run_crawl_source

router = APIRouter()


def _cancel_running_crawl_runs(db: Session) -> None:
    running = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).all()
    for run in running:
        run.status = CrawlRunStatus.cancelled
        run.finished_at = datetime.now(timezone.utc)
        db.commit()


def _create_crawl_run(source_ids: List[str], db: Session) -> CrawlRun:
    _cancel_running_crawl_runs(db)
    crawl_run = CrawlRun(
        status=CrawlRunStatus.running,
        total_sources=len(source_ids),
    )
    db.add(crawl_run)
    db.flush()

    for source_id in source_ids:
        source = db.query(Source).filter(Source.id == source_id).first()
        if source:
            crs = CrawlRunSource(
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                url=source.url,
                status=CrawlRunSourceStatus.pending,
            )
            db.add(crs)
    db.commit()
    return crawl_run


def _run_sources_in_thread(
    crawl_run_id: str,
    source_ids: List[str],
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> None:
    thread_db = SessionLocal()
    try:
        total = len(source_ids)
        loop.call_soon_threadsafe(
            queue.put_nowait, {"type": "crawl_start", "crawl_run_id": crawl_run_id, "total": total}
        )
        total_new = 0
        total_skipped = 0
        total_errors = 0

        for i, source_id in enumerate(source_ids):
            source = thread_db.query(Source).filter(Source.id == source_id).first()
            if not source:
                continue

            crs = (
                thread_db.query(CrawlRunSource)
                .filter(
                    CrawlRunSource.crawl_run_id == crawl_run_id,
                    CrawlRunSource.source_id == source_id,
                )
                .first()
            )
            if not crs:
                continue

            crs.status = CrawlRunSourceStatus.running
            crs.started_at = datetime.now(timezone.utc)
            thread_db.commit()

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_start",
                    "crawl_run_id": crawl_run_id,
                    "source_id": source.id,
                    "url": source.url,
                    "index": i + 1,
                    "total": total,
                },
            )

            def make_callback(sid: str, crs_id: str):
                def callback(event: dict) -> None:
                    event_copy = dict(event)
                    event_copy["crawl_run_id"] = crawl_run_id
                    event_copy["source_id"] = sid
                    if event["type"] == "step":
                        crs_obj = (
                            thread_db.query(CrawlRunSource)
                            .filter(CrawlRunSource.id == crs_id)
                            .first()
                        )
                        if crs_obj:
                            step_name = event.get("step")
                            if step_name and step_name in [e.value for e in CrawlRunStep]:
                                crs_obj.current_step = CrawlRunStep(step_name)
                                thread_db.commit()
                    loop.call_soon_threadsafe(queue.put_nowait, event_copy)

                return callback

            try:
                result = run_crawl_source(
                    source,
                    thread_db,
                    analyse=True,
                    progress_callback=make_callback(source.id, crs.id),
                )
            except Exception as e:
                thread_db.rollback()
                result = {"new_documents": 0, "skipped": 0, "errors": 1}
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "error",
                        "crawl_run_id": crawl_run_id,
                        "source_id": source.id,
                        "message": str(e),
                    },
                )

            total_new += result.get("new_documents", 0)
            total_skipped += result.get("skipped", 0)
            total_errors += result.get("errors", 0)

            crs.status = CrawlRunSourceStatus.completed
            crs.current_step = None
            crs.new_documents = result.get("new_documents", 0)
            crs.skipped = result.get("skipped", 0)
            crs.errors = result.get("errors", 0)
            crs.finished_at = datetime.now(timezone.utc)
            if result.get("errors", 0) > 0 and not result.get("new_documents") and not result.get("skipped"):
                crs.status = CrawlRunSourceStatus.failed
            thread_db.commit()

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_done",
                    "crawl_run_id": crawl_run_id,
                    "source_id": source.id,
                    "new_documents": result["new_documents"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
            )

        crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        if crawl_run:
            crawl_run.status = CrawlRunStatus.completed
            crawl_run.finished_at = datetime.now(timezone.utc)
            crawl_run.total_new = total_new
            crawl_run.total_skipped = total_skipped
            crawl_run.total_errors = total_errors
            thread_db.commit()

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "crawl_done",
                "crawl_run_id": crawl_run_id,
                "sources_processed": total,
                "total_new": total_new,
                "total_errors": total_errors,
            },
        )
    except Exception as e:
        crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        if crawl_run:
            crawl_run.status = CrawlRunStatus.failed
            crawl_run.finished_at = datetime.now(timezone.utc)
            thread_db.commit()
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"type": "error", "crawl_run_id": crawl_run_id, "source_id": None, "message": str(e)},
        )
    finally:
        thread_db.close()
        loop.call_soon_threadsafe(queue.put_nowait, None)


async def _sse_generator(source_ids: List[str], db: Session) -> AsyncGenerator[str, None]:
    crawl_run = _create_crawl_run(source_ids, db)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    thread = threading.Thread(
        target=_run_sources_in_thread,
        args=(crawl_run.id, source_ids, loop, queue),
        daemon=True,
    )
    thread.start()

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"


@router.post("/run")
def crawl_all_sources(db: Session = Depends(get_db)) -> Dict[str, Any]:
    active_sources = db.query(Source).filter(Source.is_active == True).all()  # noqa: E712
    results = []
    for source in active_sources:
        result = run_crawl_source(source, db, analyse=True)
        results.append(result)
    return {"sources_processed": len(active_sources), "results": results}


@router.post("/run/{source_id}")
def crawl_single_source(
    source_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return run_crawl_source(source, db, analyse=True)


@router.get("/stream")
async def stream_all_sources(db: Session = Depends(get_db)) -> StreamingResponse:
    source_ids = [
        s.id for s in db.query(Source).filter(Source.is_active == True).all()  # noqa: E712
    ]
    return StreamingResponse(
        _sse_generator(source_ids, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/{source_id}")
async def stream_single_source(
    source_id: str, db: Session = Depends(get_db)
) -> StreamingResponse:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return StreamingResponse(
        _sse_generator([source_id], db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests pass. The SSE endpoint tests may need adjustment.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/crawl.py
git commit -m "feat: persist CrawlRun in DB during SSE crawl, add crawl_run_id to events"
```

---

### Task 5: Add SSE reconnect with initial_state replay

**Files:**
- Modify: `backend/app/routers/crawl.py`

When a client connects to the stream endpoint, if there's already a running CrawlRun, the endpoint should first send an `initial_state` event with all accumulated CrawlRunSource data, then attach to the live stream for new events.

- [ ] **Step 1: Add reconnect endpoint**

Add a new endpoint `GET /api/crawl/stream/reconnect` to `backend/app/routers/crawl.py` that:
1. Looks for a running CrawlRun
2. If found, sends `initial_state` event with all CrawlRunSource data
3. Then streams live events from that run

Add this to `crawl.py`, after the existing stream endpoints:

```python
@router.get("/reconnect")
async def reconnect_crawl(db: Session = Depends(get_db)) -> StreamingResponse:
    running_run = (
        db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).first()
    )
    if not running_run:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'no_active_run'})}\n\n"]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    sources_data = []
    for crs in running_run.sources:
        sources_data.append({
            "source_id": crs.source_id,
            "url": crs.url,
            "status": crs.status.value if crs.status else "pending",
            "current_step": crs.current_step.value if crs.current_step else None,
            "new_documents": crs.new_documents,
            "skipped": crs.skipped,
            "errors": crs.errors,
            "error_message": crs.error_message,
        })

    initial_event = {
        "type": "initial_state",
        "crawl_run_id": running_run.id,
        "total": running_run.total_sources,
        "sources": sources_data,
    }

    async def generate():
        yield f"data: {json.dumps(initial_event)}\n\n"
        yield f"data: {json.dumps({'type': 'reconnect_complete'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/crawl.py
git commit -m "feat: add SSE reconnect endpoint with initial_state replay"
```

---

### Task 6: Backend tests for CrawlRun persistence + SSE reconnect

**Files:**
- Create: `backend/tests/test_crawl_runs.py`

- [ ] **Step 1: Write tests for CrawlRun model + API + reconnect**

Create `backend/tests/test_crawl_runs.py`:

```python
import pytest
from app.models.crawl_run import CrawlRun, CrawlRunStatus, CrawlRunSource, CrawlRunSourceStatus


def test_crawl_run_create(db_session):
    run = CrawlRun(status=CrawlRunStatus.running, total_sources=3)
    db_session.add(run)
    db_session.commit()
    assert run.id is not None
    assert run.status == CrawlRunStatus.running
    assert run.total_sources == 3


def test_crawl_run_source_create(db_session):
    run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
    db_session.add(run)
    db_session.flush()
    crs = CrawlRunSource(
        crawl_run_id=run.id,
        source_id="test-source-id",
        url="https://example.com",
        status=CrawlRunSourceStatus.pending,
    )
    db_session.add(crs)
    db_session.commit()
    assert crs.id is not None
    assert crs.crawl_run_id == run.id


def test_crawl_run_completion(db_session):
    run = CrawlRun(status=CrawlRunStatus.running, total_sources=2)
    db_session.add(run)
    db_session.commit()

    run.status = CrawlRunStatus.completed
    run.total_new = 5
    run.total_errors = 0
    db_session.commit()

    db_session.refresh(run)
    assert run.status == CrawlRunStatus.completed
    assert run.total_new == 5


def test_list_crawl_runs_endpoint(client):
    response = client.get("/api/crawl-runs/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_crawl_runs_filter_by_status(client):
    response = client.get("/api/crawl-runs/?status=running")
    assert response.status_code == 200


def test_get_crawl_run_not_found(client):
    response = client.get("/api/crawl-runs/nonexistent-id")
    assert response.status_code == 404


def test_reconnect_no_active_run(client):
    response = client.get("/api/crawl/reconnect")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "no_active_run"
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_crawl_runs.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_crawl_runs.py
git commit -m "test: add CrawlRun model and API endpoint tests"
```

---

### Task 7: Frontend — Update TypeScript types and API client

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add CrawlRun types and update CrawlEvent types**

In `frontend/src/types/index.ts`, add after the `CrawlErrorEvent` interface (around line 209) and before `export type CrawlEvent`:

```typescript
export interface CrawlInitialStateEvent {
  type: 'initial_state';
  crawl_run_id: string;
  total: number;
  sources: CrawlRunSourceState[];
}

export interface CrawlReconnectCompleteEvent {
  type: 'reconnect_complete';
}

export interface CrawlNoActiveRunEvent {
  type: 'no_active_run';
}
```

Update `CrawlStartEvent` to include `crawl_run_id`:

```typescript
export interface CrawlStartEvent {
  type: 'crawl_start';
  crawl_run_id: string;
  total: number;
}
```

Update `CrawlSourceStartEvent` to include `crawl_run_id`:

```typescript
export interface CrawlSourceStartEvent {
  type: 'source_start';
  crawl_run_id: string;
  source_id: string;
  url: string;
  index: number;
  total: number;
}
```

Update `CrawlStepEvent` to include `crawl_run_id`:

```typescript
export interface CrawlStepEvent {
  type: 'step';
  crawl_run_id: string;
  source_id: string;
  step: CrawlStep;
}
```

Update `CrawlSourceDoneEvent` to include `crawl_run_id`:

```typescript
export interface CrawlSourceDoneEvent {
  type: 'source_done';
  crawl_run_id: string;
  source_id: string;
  new_documents: number;
  skipped: number;
  errors: number;
}
```

Update `CrawlDoneEvent` to include `crawl_run_id`:

```typescript
export interface CrawlDoneEvent {
  type: 'crawl_done';
  crawl_run_id: string;
  sources_processed: number;
  total_new: number;
  total_errors: number;
}
```

Update `CrawlErrorEvent` to include `crawl_run_id`:

```typescript
export interface CrawlErrorEvent {
  type: 'error';
  crawl_run_id?: string;
  source_id: string | null;
  message: string;
}
```

Update `CrawlEvent` union type to include new event types:

```typescript
export type CrawlEvent =
  | CrawlStartEvent
  | CrawlSourceStartEvent
  | CrawlStepEvent
  | CrawlSourceDoneEvent
  | CrawlDoneEvent
  | CrawlErrorEvent
  | CrawlInitialStateEvent
  | CrawlReconnectCompleteEvent
  | CrawlNoActiveRunEvent;
```

Add `CrawlRunSourceState` interface:

```typescript
export interface CrawlRunSourceState {
  source_id: string;
  url: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  current_step?: string;
  new_documents: number;
  skipped: number;
  errors: number;
  error_message?: string;
}
```

Add `CrawlRun` and `CrawlRunList` interfaces (for REST API):

```typescript
export interface CrawlRunList {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_sources: number;
  total_new: number;
  total_skipped: number;
  total_errors: number;
}

export interface CrawlRun extends CrawlRunList {
  sources: CrawlRunSourceState[];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add CrawlRun types and update CrawlEvent with crawl_run_id"
```

---

### Task 8: Frontend — Update useCrawlStream hook for reconnect + persistence

**Files:**
- Modify: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 1: Rewrite useCrawlStream with reconnect logic**

Replace the entire content of `frontend/src/hooks/useCrawlStream.ts`:

```typescript
import { useState, useRef, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type {
  CrawlEvent,
  CrawlStreamSummary,
  SourceCrawlState,
  CrawlRunSourceState,
} from '../types';

function getAuthHeader(): Record<string, string> {
  const stored = localStorage.getItem('wfm_credentials');
  if (!stored) return {};
  try {
    const { username, password } = JSON.parse(stored);
    return { Authorization: `Basic ${btoa(`${username}:${password}`)}` };
  } catch {
    return {};
  }
}

function mapSourceStatus(status: string): SourceCrawlState['status'] {
  switch (status) {
    case 'completed': return 'done';
    case 'failed': return 'error';
    case 'running': return 'running';
    case 'skipped': return 'done';
    default: return 'waiting';
  }
}

export function useCrawlStream() {
  const qc = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const isRunningRef = useRef(false);
  const [sourceStates, setSourceStates] = useState<SourceCrawlState[]>([]);
  const [summary, setSummary] = useState<CrawlStreamSummary | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [crawlTotal, setCrawlTotal] = useState(0);
  const [crawlRunId, setCrawlRunId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback(
    (event: CrawlEvent) => {
      switch (event.type) {
        case 'crawl_start':
          setCrawlRunId(event.crawl_run_id);
          setCrawlTotal(event.total);
          break;
        case 'initial_state':
          setCrawlRunId(event.crawl_run_id);
          setCrawlTotal(event.total);
          const restored: SourceCrawlState[] = event.sources.map((s: CrawlRunSourceState) => ({
            source_id: s.source_id,
            url: s.url,
            status: mapSourceStatus(s.status),
            currentStep: s.current_step as SourceCrawlState['currentStep'] | undefined,
            result: (s.new_documents > 0 || s.skipped > 0 || s.errors > 0)
              ? { new_documents: s.new_documents, skipped: s.skipped, errors: s.errors }
              : undefined,
            errorMessage: s.error_message,
          }));
          setSourceStates(restored);
          break;
        case 'reconnect_complete':
          break;
        case 'no_active_run':
          setIsRunning(false);
          isRunningRef.current = false;
          break;
        case 'source_start':
          setSourceStates((prev) => [
            ...prev.filter((s) => s.source_id !== event.source_id),
            {
              source_id: event.source_id,
              url: event.url,
              status: 'running',
            },
          ]);
          break;
        case 'step':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? { ...s, currentStep: event.step }
                : s,
            ),
          );
          break;
        case 'source_done':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    status: event.errors > 0 ? 'error' : 'done',
                    currentStep: undefined,
                    errorMessage: event.errors > 0 ? s.errorMessage : undefined,
                    result: {
                      new_documents: event.new_documents,
                      skipped: event.skipped,
                      errors: event.errors,
                    },
                  }
                : s,
            ),
          );
          break;
        case 'error':
          if (event.source_id) {
            setSourceStates((prev) =>
              prev.map((s) =>
                s.source_id === event.source_id
                  ? { ...s, status: 'error', errorMessage: event.message }
                  : s,
              ),
            );
          } else {
            setConnectionError(event.message);
          }
          break;
        case 'crawl_done':
          setSummary({
            sources_processed: event.sources_processed,
            total_new: event.total_new,
            total_errors: event.total_errors,
          });
          qc.invalidateQueries({ queryKey: ['documents'] });
          qc.invalidateQueries({ queryKey: ['signals'] });
          qc.invalidateQueries({ queryKey: ['sources'] });
          break;
      }
    },
    [qc],
  );

  useEffect(() => {
    if (!isRunning && !summary && sourceStates.length === 0) {
      const checkActiveRun = async () => {
        try {
          const runs = await apiGet<CrawlRunList[]>('/crawl-runs/?status=running');
          if (runs && runs.length > 0) {
            const run = runs[0];
            setIsRunning(true);
            isRunningRef.current = true;
            setCrawlRunId(run.id);
            setCrawlTotal(run.total_sources);

            const res = await fetch('/api/crawl/reconnect', {
              headers: getAuthHeader(),
            });
            if (!res.ok || !res.body) return;

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop()!;

              for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                  const event: CrawlEvent = JSON.parse(line.slice(6));
                  handleEvent(event);
                  if (event.type === 'reconnect_complete') {
                    break;
                  }
                } catch {
                  // ignore malformed lines
                }
              }
            }

            setIsRunning(false);
            isRunningRef.current = false;
          }
        } catch {
          // No active run or error — that's fine
        }
      };
      checkActiveRun();
    }
  }, []);

  const start = useCallback(
    async (sourceId?: string) => {
      if (isRunningRef.current) return;
      isRunningRef.current = true;
      setIsRunning(true);

      abortRef.current = new AbortController();
      setSourceStates([]);
      setSummary(null);
      setConnectionError(null);
      setCrawlTotal(0);

      const path = sourceId
        ? `/api/crawl/stream/${sourceId}`
        : '/api/crawl/stream';

      try {
        const res = await fetch(path, {
          headers: getAuthHeader(),
          signal: abortRef.current.signal,
        });

        if (!res.ok) {
          setConnectionError(`Request failed: ${res.status}`);
          return;
        }

        if (!res.body) {
          setConnectionError('Streaming not supported');
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop()!;

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const event: CrawlEvent = JSON.parse(line.slice(6));
              handleEvent(event);
            } catch {
              // ignore malformed lines
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setConnectionError(err.message);
        }
      } finally {
        isRunningRef.current = false;
        setIsRunning(false);
      }
    },
    [handleEvent],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSourceStates([]);
    setSummary(null);
    setConnectionError(null);
    setCrawlTotal(0);
    setCrawlRunId(null);
  }, []);

  return { start, cancel, reset, isRunning, sourceStates, summary, connectionError, crawlTotal, crawlRunId };
}
```

Note: The `CrawlRunList` type import needs to be added from types. The types file already defines it.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useCrawlStream.ts
git commit -m "feat: useCrawlStream reconnects to active CrawlRun on page load"
```

---

### Task 9: Frontend — useActiveCrawlRun hook for Dashboard

**Files:**
- Create: `frontend/src/hooks/useActiveCrawlRun.ts`
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Create useActiveCrawlRun hook**

Create `frontend/src/hooks/useActiveCrawlRun.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRunList } from '../types';

export function useActiveCrawlRun() {
  const { data, isLoading } = useQuery({
    queryKey: ['activeCrawlRun'],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/?status=running'),
    refetchInterval: 5000,
    select: (runs) => (runs && runs.length > 0 ? runs[0] : null),
  });

  return { activeRun: data ?? null, isLoading };
}
```

- [ ] **Step 2: Add active crawl banner to Dashboard**

Modify `frontend/src/pages/Dashboard.tsx` — add import for `useActiveCrawlRun` and `Link` from react-router-dom, then add the banner component and integrate it.

Add imports at the top:

```typescript
import { useActiveCrawlRun } from '../hooks/useActiveCrawlRun';
import { Link } from 'react-router-dom';
```

Inside the `Dashboard` function, after `const crawlAll = useCrawlAll();` add:

```typescript
const { activeRun } = useActiveCrawlRun();
```

Then, inside the JSX, after the existing error/success banner blocks (after `{crawlAll.isError && (...)}`), add:

```tsx
{activeRun && (
  <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border"
    style={{ background: '#eff6ff', color: '#1d4ed8', borderColor: '#bfdbfe' }}>
    <Link to="/admin/sources" className="underline hover:no-underline">
      Crawl läuft
    </Link>
    {' '}— {activeRun.total_sources} Quellen werden verarbeitet
  </div>
)}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useActiveCrawlRun.ts frontend/src/pages/Dashboard.tsx
git commit -m "feat: add active crawl banner to Dashboard"
```

---

### Task 10: Frontend — CrawlProgressPanel stays open after completion

**Files:**
- Modify: `frontend/src/components/CrawlProgressPanel.tsx`

The CrawlProgressPanel already stays open until dismissed (it uses `onDismiss`). The change needed is to show the `crawl_run_id` or status more clearly. No major changes needed — the panel already handles the "done, don't auto-hide" behavior correctly with the existing `isRunning`/`summary` logic.

However, we should ensure the panel shows when reconnecting with `initial_state` data (i.e., when `isRunning` transitions from false to true via reconnect, the sourceStates are populated but `isRunning` might briefly be false).

- [ ] **Step 1: Verify CrawlProgressPanel works with reconnect data**

The current `CrawlProgressPanel` returns `null` when `!isRunning && !summary && !connectionError`. After reconnect, `sourceStates` will be populated but `isRunning` will be false until the SSE stream is established. We need to also show the panel when `sourceStates.length > 0`.

Modify the condition in `CrawlProgressPanel`:

Change:
```tsx
if (!isRunning && !summary && !connectionError) return null;
```

To:
```tsx
if (!isRunning && !summary && !connectionError && sourceStates.length === 0) return null;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CrawlProgressPanel.tsx
git commit -m "fix: show CrawlProgressPanel when sourceStates exist from reconnect"
```

---

### Task 11: End-to-end verification

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Manual integration test**

Start the dev stack and verify:
1. Trigger a crawl from SourcesAdmin
2. Refresh the page → the progress panel should reappear with accumulated state
3. Check the Dashboard for the active crawl banner
4. After completion, the panel should stay visible until dismissed

---

## Self-Review Checklist

- [x] **Spec coverage:** Every section of the design doc maps to tasks
- [x] **Placeholder scan:** No TBDs, TODOs, or vague steps
- [x] **Type consistency:** CrawlRunSourceStatus enum values match between Python and TypeScript; CrawlStep values match between backend and frontend; crawl_run_id field present in all SSE events both sides