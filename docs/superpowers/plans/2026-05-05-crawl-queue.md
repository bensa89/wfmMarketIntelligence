# Crawl Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to enqueue additional sources while a crawl is running; the queued batch starts automatically after the active run and survives page reloads.

**Architecture:** A new `queued` CrawlRun status persists the queue in the DB. Two new endpoints handle enqueueing (`POST /enqueue/{source_id}`) and starting the queued run as an SSE stream (`GET /stream/queued`). The frontend calls `enqueue` when a run is active, then automatically opens `/stream/queued` once `crawl_done` fires (or on reconnect if the page was reloaded).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL / SQLite (tests), React 18 + TypeScript, TanStack Query

---

## File Map

| File | Change |
|------|--------|
| `backend/app/models/crawl_run.py` | Add `queued` to `CrawlRunStatus` |
| `backend/alembic/versions/XXXX_add_queued_to_crawlrunstatus.py` | Migration: ALTER TYPE |
| `backend/app/routers/crawl.py` | `_sse_generator` accepts `existing_run_id`; new `enqueue` + `stream/queued` endpoints; `reconnect` returns `queued_state` |
| `backend/tests/test_crawl_router.py` | Tests for enqueue, stream/queued, reconnect queued_state |
| `frontend/src/types/index.ts` | Add `CrawlQueuedStateEvent`; add to `CrawlEvent` union |
| `frontend/src/hooks/useCrawlStream.ts` | `queuedSources` state, enqueue logic, auto-start queued stream |
| `frontend/src/components/CrawlProgressPanel.tsx` | Queued section, updated header counter |

---

## Task 1: Add `queued` to `CrawlRunStatus` model + migration

**Files:**
- Modify: `backend/app/models/crawl_run.py`
- Create: `backend/alembic/versions/XXXX_add_queued_to_crawlrunstatus.py`

- [ ] **Step 1: Write a failing test confirming the enum value doesn't exist yet**

```python
# In backend/tests/test_crawl_router.py, add at the top of the file after imports:
def test_crawl_run_status_has_queued():
    from app.models.crawl_run import CrawlRunStatus
    assert CrawlRunStatus.queued == "queued"
```

Run: `cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_run_status_has_queued -v`
Expected: FAIL — `AttributeError: 'queued' is not a valid CrawlRunStatus`

- [ ] **Step 2: Add `queued` to the model**

In `backend/app/models/crawl_run.py`, change:

```python
class CrawlRunStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
```

to:

```python
class CrawlRunStatus(str, enum.Enum):
    running = "running"
    queued = "queued"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_run_status_has_queued -v`
Expected: PASS

- [ ] **Step 4: Generate and clean the migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision -m "add_queued_to_crawlrunstatus"
```

The generated file will be empty. Fill it in:

```python
"""add_queued_to_crawlrunstatus

Revision ID: <generated>
Revises: 7c1829582bbd
Create Date: <generated>
"""
from typing import Sequence, Union
from alembic import op

revision: str = '<generated>'
down_revision: Union[str, Sequence[str], None] = '7c1829582bbd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE crawlrunstatus ADD VALUE IF NOT EXISTS 'queued'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type
    pass
```

- [ ] **Step 5: Apply the migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Expected: `Running upgrade 7c1829582bbd -> <revision>, add_queued_to_crawlrunstatus`

- [ ] **Step 6: Run all crawl router tests to confirm nothing broke**

```bash
cd backend && python -m pytest tests/test_crawl_router.py -v
```

Expected: all existing tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/crawl_run.py backend/alembic/versions/
git commit -m "feat: add queued status to CrawlRunStatus"
```

---

## Task 2: `POST /api/crawl/enqueue/{source_id}` endpoint

**Files:**
- Modify: `backend/app/routers/crawl.py`
- Modify: `backend/tests/test_crawl_router.py`

- [ ] **Step 1: Write failing tests for the enqueue endpoint**

Add to `backend/tests/test_crawl_router.py`:

```python
def test_enqueue_creates_queued_run(client, seed_source, db_engine):
    """Enqueue a source when no queued run exists — creates one."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    # Create a running run first so enqueue is valid
    setup_db = TestSessionLocal()
    try:
        running_run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running_run)
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.post(f"/api/crawl/enqueue/{seed_source.id}")
    assert response.status_code == 202
    data = response.json()
    assert data["queued"] is True
    assert data["position"] == 1

    verify_db = TestSessionLocal()
    try:
        queued = verify_db.query(CrawlRun).filter(
            CrawlRun.status == CrawlRunStatus.queued
        ).first()
        assert queued is not None
        assert len(queued.sources) == 1
        assert queued.sources[0].source_id == seed_source.id
    finally:
        verify_db.close()


def test_enqueue_appends_to_existing_queued_run(client, db_session, db_engine):
    """Enqueueing a second source appends to the existing queued run."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    company = Company(name="Co2", slug="co2-enqueue", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    source_a = Source(company_id=company.id, url="https://a.com", source_type=SourceType.news, is_active=True)
    source_b = Source(company_id=company.id, url="https://b.com", source_type=SourceType.news, is_active=True)
    db_session.add_all([source_a, source_b])
    db_session.commit()

    # Seed a running run + queued run with source_a already in it
    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=queued.id,
            source_id=source_a.id,
            url=source_a.url,
            status=CrawlRunSourceStatus.pending,
        ))
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.post(f"/api/crawl/enqueue/{source_b.id}")
    assert response.status_code == 202
    data = response.json()
    assert data["position"] == 2

    verify_db = TestSessionLocal()
    try:
        queued_runs = verify_db.query(CrawlRun).filter(
            CrawlRun.status == CrawlRunStatus.queued
        ).all()
        assert len(queued_runs) == 1  # still only one queued run
        assert len(queued_runs[0].sources) == 2
    finally:
        verify_db.close()


def test_enqueue_noop_for_duplicate_source(client, db_session, db_engine):
    """Enqueueing a source already in the queue returns current position."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    company = Company(name="Co3", slug="co3-enqueue", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://dup.com", source_type=SourceType.news, is_active=True)
    db_session.add(source)
    db_session.commit()

    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=queued.id,
            source_id=source.id,
            url=source.url,
            status=CrawlRunSourceStatus.pending,
        ))
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.post(f"/api/crawl/enqueue/{source.id}")
    assert response.status_code == 202
    assert response.json()["position"] == 1  # still 1, not added twice

    verify_db = TestSessionLocal()
    try:
        queued = verify_db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()
        assert len(queued.sources) == 1
    finally:
        verify_db.close()


def test_enqueue_nonexistent_source_returns_404(client):
    response = client.post("/api/crawl/enqueue/nonexistent-id")
    assert response.status_code == 404
```

Run: `cd backend && python -m pytest tests/test_crawl_router.py::test_enqueue_creates_queued_run tests/test_crawl_router.py::test_enqueue_appends_to_existing_queued_run tests/test_crawl_router.py::test_enqueue_noop_for_duplicate_source tests/test_crawl_router.py::test_enqueue_nonexistent_source_returns_404 -v`
Expected: FAIL — `404 Not Found` (endpoint doesn't exist yet)

- [ ] **Step 2: Implement the enqueue endpoint**

Add to `backend/app/routers/crawl.py` after the `stream_single_source` endpoint (around line 433):

```python
@router.post("/enqueue/{source_id}", status_code=202)
def enqueue_source(source_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    queued_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()

    if queued_run is None:
        queued_run = CrawlRun(
            status=CrawlRunStatus.queued,
            total_sources=0,
        )
        db.add(queued_run)
        db.flush()

    # No-op if source already queued
    already_queued = any(crs.source_id == source_id for crs in queued_run.sources)
    if not already_queued:
        crs = CrawlRunSource(
            crawl_run_id=queued_run.id,
            source_id=source_id,
            url=source.url,
            status=CrawlRunSourceStatus.pending,
        )
        db.add(crs)
        queued_run.total_sources = len(queued_run.sources) + 1
        db.commit()

    position = len(queued_run.sources)
    return {"queued": True, "position": position, "crawl_run_id": queued_run.id}
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_enqueue_creates_queued_run tests/test_crawl_router.py::test_enqueue_appends_to_existing_queued_run tests/test_crawl_router.py::test_enqueue_noop_for_duplicate_source tests/test_crawl_router.py::test_enqueue_nonexistent_source_returns_404 -v
```

Expected: all 4 PASS

- [ ] **Step 4: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/crawl.py backend/tests/test_crawl_router.py
git commit -m "feat: add POST /api/crawl/enqueue/{source_id} endpoint"
```

---

## Task 3: `GET /api/crawl/stream/queued` endpoint

**Files:**
- Modify: `backend/app/routers/crawl.py`
- Modify: `backend/tests/test_crawl_router.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_crawl_router.py`:

```python
def test_stream_queued_returns_404_when_no_queue(client):
    response = client.get("/api/crawl/stream/queued")
    assert response.status_code == 404


def test_stream_queued_runs_queued_sources(client, seed_source, db_engine):
    """Starting stream/queued transitions the queued run to running and streams events."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    setup_db = TestSessionLocal()
    try:
        queued_run = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued_run)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=queued_run.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.pending,
        ))
        setup_db.commit()
        queued_run_id = queued_run.id
    finally:
        setup_db.close()

    def mock_run(source, db, analyse=True, progress_callback=None):
        return {"source_id": source.id, "new_documents": 1, "skipped": 0, "errors": 0, "discovery": {}}

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run),
    ):
        response = client.get("/api/crawl/stream/queued")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert "crawl_start" in event_types
    assert "crawl_done" in event_types

    # Verify the queued run is now completed in DB
    verify_db = TestSessionLocal()
    try:
        run = verify_db.query(CrawlRun).filter(CrawlRun.id == queued_run_id).first()
        assert run.status == CrawlRunStatus.completed
    finally:
        verify_db.close()
```

Run: `cd backend && python -m pytest tests/test_crawl_router.py::test_stream_queued_returns_404_when_no_queue tests/test_crawl_router.py::test_stream_queued_runs_queued_sources -v`
Expected: FAIL — 404 endpoint not found

- [ ] **Step 2: Modify `_sse_generator` to accept an existing run ID**

In `backend/app/routers/crawl.py`, change the signature and first lines of `_sse_generator`:

```python
async def _sse_generator(
    source_ids: List[str], db: Session, existing_run_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    if existing_run_id is not None:
        crawl_run = db.query(CrawlRun).filter(CrawlRun.id == existing_run_id).first()
        crawl_run.status = CrawlRunStatus.running
        crawl_run.started_at = datetime.now(timezone.utc)  # datetime/timezone already imported at top of file
        db.commit()
    else:
        crawl_run = _create_crawl_run(source_ids, db)
    # rest of function unchanged ...
```

Also add `Optional` to the imports at the top of the file:
```python
from typing import AsyncGenerator, Dict, Any, List, Optional
```

- [ ] **Step 3: Add `GET /api/crawl/stream/queued` endpoint**

Add to `backend/app/routers/crawl.py` **before** `GET /api/crawl/stream/{source_id}` (important — FastAPI routes are matched in order; `stream/queued` must be registered before `stream/{source_id}` or it will be captured by the wildcard):

```python
@router.get("/stream/queued")
async def stream_queued_run(db: Session = Depends(get_db)) -> StreamingResponse:
    queued_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()
    if not queued_run:
        raise HTTPException(status_code=404, detail="No queued run found")

    source_ids = [crs.source_id for crs in queued_run.sources]
    return StreamingResponse(
        _sse_generator(source_ids, db, existing_run_id=queued_run.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_stream_queued_returns_404_when_no_queue tests/test_crawl_router.py::test_stream_queued_runs_queued_sources -v
```

Expected: both PASS

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/crawl.py backend/tests/test_crawl_router.py
git commit -m "feat: add GET /api/crawl/stream/queued endpoint"
```

---

## Task 4: Modify `GET /api/crawl/reconnect` to return `queued_state`

**Files:**
- Modify: `backend/app/routers/crawl.py`
- Modify: `backend/tests/test_crawl_router.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_crawl_router.py`:

```python
def test_reconnect_returns_queued_state(client, seed_source, db_engine):
    """Reconnect includes queued_state event when a queued run exists."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=running.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.running,
        ))
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=queued.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.pending,
        ))
        setup_db.commit()
        queued_id = queued.id
    finally:
        setup_db.close()

    response = client.get("/api/crawl/reconnect")
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    types = [e["type"] for e in events]
    assert "initial_state" in types
    assert "queued_state" in types

    qs = next(e for e in events if e["type"] == "queued_state")
    assert qs["crawl_run_id"] == queued_id
    assert len(qs["sources"]) == 1
    assert qs["sources"][0]["source_id"] == seed_source.id


def test_reconnect_queued_state_only_when_no_running_run(client, seed_source, db_engine):
    """When no running run exists but a queued one does, only queued_state is sent."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    setup_db = TestSessionLocal()
    try:
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=queued.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.pending,
        ))
        setup_db.commit()
        queued_id = queued.id
    finally:
        setup_db.close()

    response = client.get("/api/crawl/reconnect")
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    types = [e["type"] for e in events]
    assert "initial_state" not in types
    assert "no_active_run" not in types
    assert "queued_state" in types
    assert types[-1] == "reconnect_complete"
```

Run: `cd backend && python -m pytest tests/test_crawl_router.py::test_reconnect_returns_queued_state tests/test_crawl_router.py::test_reconnect_queued_state_only_when_no_running_run -v`
Expected: FAIL

- [ ] **Step 2: Modify the reconnect endpoint**

Replace the current `reconnect_crawl` function in `backend/app/routers/crawl.py` with:

```python
@router.get("/reconnect")
async def reconnect_crawl(db: Session = Depends(get_db)) -> StreamingResponse:
    running_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).first()
    queued_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()

    events: list[dict] = []

    if running_run:
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
                "fetch_ms": crs.fetch_ms,
                "extract_ms": crs.extract_ms,
                "analyse_ms": crs.analyse_ms,
                "discover_ms": crs.discover_ms,
                "discover_pages_crawled": crs.discover_pages_crawled,
                "discover_pages_found": crs.discover_pages_found,
            })
        events.append({
            "type": "initial_state",
            "crawl_run_id": running_run.id,
            "total": running_run.total_sources,
            "sources": sources_data,
        })

    if queued_run:
        queued_sources = [
            {"source_id": crs.source_id, "url": crs.url}
            for crs in queued_run.sources
        ]
        events.append({
            "type": "queued_state",
            "crawl_run_id": queued_run.id,
            "sources": queued_sources,
        })

    if not running_run and not queued_run:
        events.append({"type": "no_active_run"})

    events.append({"type": "reconnect_complete"})

    async def generate():
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"

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

- [ ] **Step 3: Update existing `test_reconnect_no_active_run` test**

The test currently asserts `len(events) == 1`. Now `no_active_run` is followed by `reconnect_complete` (2 events). Update:

```python
def test_reconnect_no_active_run(client):
    response = client.get("/api/crawl/reconnect")
    assert response.status_code == 200
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events[0]["type"] == "no_active_run"
    assert events[-1]["type"] == "reconnect_complete"
```

Also update `test_reconnect_with_active_run` — it currently asserts `events[1]["type"] == "reconnect_complete"`. That still holds (no queued run in that test), so no change needed there.

- [ ] **Step 4: Run all reconnect tests**

```bash
cd backend && python -m pytest tests/test_crawl_router.py -k "reconnect" -v
```

Expected: all pass

- [ ] **Step 5: Run full suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/crawl.py backend/tests/test_crawl_router.py
git commit -m "feat: reconnect returns queued_state for pending queue"
```

---

## Task 5: Frontend types — add `CrawlQueuedStateEvent`

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add the new event type and update the union**

In `frontend/src/types/index.ts`, add after `CrawlNoActiveRunEvent`:

```typescript
export interface CrawlQueuedStateEvent {
  type: 'queued_state';
  crawl_run_id: string;
  sources: { source_id: string; url: string }[];
}
```

Update the `CrawlEvent` union to include it:

```typescript
export type CrawlEvent =
  | CrawlStartEvent
  | CrawlSourceStartEvent
  | CrawlStepEvent
  | CrawlDiscoveryProgressEvent
  | CrawlStepTimingEvent
  | CrawlSourceDoneEvent
  | CrawlDoneEvent
  | CrawlErrorEvent
  | CrawlInitialStateEvent
  | CrawlReconnectCompleteEvent
  | CrawlNoActiveRunEvent
  | CrawlQueuedStateEvent;
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add CrawlQueuedStateEvent type"
```

---

## Task 6: `useCrawlStream` — enqueue logic and auto-start queued stream

**Files:**
- Modify: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 1: Add `queuedSources` state, `queuedRunIdRef`, and `queued_state` handler**

At the top of the `useCrawlStream` function, add two new pieces of state after the existing state declarations:

```typescript
const [queuedSources, setQueuedSources] = useState<{ source_id: string; url: string }[]>([]);
const queuedRunIdRef = useRef<string | null>(null);
```

In `handleEvent`, add a case for `queued_state` (before the closing `}`):

```typescript
case 'queued_state':
  setQueuedSources(event.sources);
  queuedRunIdRef.current = event.crawl_run_id;
  break;
```

Also clear `queuedSources` when a new run starts by adding to the `crawl_start` case:

```typescript
case 'crawl_start':
  setCrawlRunId(event.crawl_run_id);
  setCrawlTotal(event.total);
  setQueuedSources([]);
  queuedRunIdRef.current = null;
  break;
```

- [ ] **Step 2: Add `startQueuedStreamRef` and `startQueuedStream` helper**

`handleEvent` calls `startQueuedStream` (in `crawl_done`) and `startQueuedStream` calls `handleEvent`. A direct `useCallback` circular dependency causes infinite re-renders. Break the cycle with a ref:

Add immediately after the `queuedRunIdRef` declaration:

```typescript
const startQueuedStreamRef = useRef<() => Promise<void>>(() => Promise.resolve());
```

Add the following `useCallback` **before** the `start` callback:

```typescript
const startQueuedStream = useCallback(async () => {
  if (isRunningRef.current) return;
  isRunningRef.current = true;
  setIsRunning(true);
  setSourceStates([]);
  setSummary(null);
  setConnectionError(null);
  setCrawlTotal(0);

  abortRef.current = new AbortController();

  try {
    const res = await fetch('/api/crawl/stream/queued', {
      headers: getAuthHeader(),
      signal: abortRef.current.signal,
    });

    if (!res.ok) {
      if (res.status === 404) {
        queuedRunIdRef.current = null;
        setQueuedSources([]);
      } else {
        setConnectionError(`Request failed: ${res.status}`);
      }
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
}, [handleEvent]);

// Keep the ref in sync so handleEvent can call it without a direct dependency
startQueuedStreamRef.current = startQueuedStream;
```

- [ ] **Step 3: Auto-start queued stream after `crawl_done`**

In the `crawl_done` case inside `handleEvent`, after `setIsRunning(false)`, add (using the ref to avoid circular dependency):

```typescript
case 'crawl_done':
  setSummary({
    sources_processed: event.sources_processed,
    total_new: event.total_new,
    total_errors: event.total_errors,
  });
  qc.invalidateQueries({ queryKey: ['documents'] });
  qc.invalidateQueries({ queryKey: ['signals'] });
  qc.invalidateQueries({ queryKey: ['sources'] });
  qc.invalidateQueries({ queryKey: ['crawlRuns'] });
  qc.invalidateQueries({ queryKey: ['activeCrawlRun'] });
  qc.invalidateQueries({ queryKey: ['discoveredPagesStats'] });
  qc.invalidateQueries({ queryKey: ['signalsOverTime'] });
  qc.invalidateQueries({ queryKey: ['signalDistribution'] });
  qc.invalidateQueries({ queryKey: ['sourceCandidates'] });
  setIsRunning(false);
  if (queuedRunIdRef.current) {
    setTimeout(() => startQueuedStreamRef.current(), 300);
  }
  break;
```

`handleEvent`'s `useCallback` dependency array stays `[qc]` — no `startQueuedStream` added because the ref is used instead.

- [ ] **Step 4: Modify `start()` to call enqueue when running**

Change the `start` callback to:

```typescript
const start = useCallback(
  async (sourceId?: string) => {
    // If a crawl is already running, enqueue the source instead
    if (isRunningRef.current && sourceId) {
      try {
        const res = await fetch(`/api/crawl/enqueue/${sourceId}`, {
          method: 'POST',
          headers: getAuthHeader(),
        });
        if (res.ok) {
          const data = await res.json();
          // Fetch source URL for display — use the existing sources query cache or fall back to source_id
          // The queued_state from reconnect will populate full details on reload;
          // for live display we add a placeholder that reconnect will fill in
          queuedRunIdRef.current = data.crawl_run_id;
          // Re-fetch queue state via a lightweight reconnect to get the URL
          const reconnectRes = await fetch('/api/crawl/reconnect', { headers: getAuthHeader() });
          if (reconnectRes.ok && reconnectRes.body) {
            const reader = reconnectRes.body.getReader();
            const decoder = new TextDecoder();
            let buf = '';
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buf += decoder.decode(value, { stream: true });
              const lines = buf.split('\n');
              buf = lines.pop()!;
              for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                  const event: CrawlEvent = JSON.parse(line.slice(6));
                  if (event.type === 'queued_state') handleEvent(event);
                } catch { /* ignore */ }
              }
            }
          }
        }
      } catch {
        // enqueue failed silently — user can retry
      }
      return;
    }

    if (isRunningRef.current) return;
    isRunningRef.current = true;
    setIsRunning(true);

    abortRef.current = new AbortController();
    setSourceStates([]);
    setSummary(null);
    setConnectionError(null);
    setCrawlTotal(0);
    setCrawlRunId(null);

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
```

- [ ] **Step 5: Auto-start queued stream from reconnect `useEffect`**

After the reconnect stream ends in the `useEffect`, add auto-start logic:

```typescript
useEffect(() => {
  (async () => {
    try {
      const runs = await apiGet<CrawlRunList[]>('/crawl-runs/', { status: 'running' });
      if (runs.length === 0) {
        // No active run — check if there is a queued run via reconnect
        const res = await fetch('/api/crawl/reconnect', { headers: getAuthHeader() });
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
            } catch { /* ignore */ }
          }
        }

        // If reconnect populated a queued run and nothing is running, start it
        if (queuedRunIdRef.current && !isRunningRef.current) {
          await startQueuedStream();
        }
        return;
      }

      // Active run exists — reconnect to it
      const run = runs[0];
      setCrawlRunId(run.id);
      setCrawlTotal(run.total_sources);
      setIsRunning(true);
      isRunningRef.current = true;

      const res = await fetch('/api/crawl/reconnect', { headers: getAuthHeader() });
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
          } catch { /* ignore */ }
        }
      }
    } catch {
      // no active run or reconnect failed — that's fine
    }
  })();
}, [handleEvent, startQueuedStream]);  // startQueuedStream needed here since useEffect calls it directly (not via ref)
```

- [ ] **Step 6: Expose `queuedSources` from the hook**

Add `queuedSources` to the return value:

```typescript
return {
  start,
  cancel,
  reset,
  isRunning,
  crawlRunId,
  sourceStates,
  summary,
  connectionError,
  crawlTotal,
  queuedSources,
};
```

- [ ] **Step 7: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useCrawlStream.ts
git commit -m "feat: useCrawlStream enqueue logic and auto-start queued stream"
```

---

## Task 7: `CrawlProgressPanel` — queued section + run counter

**Files:**
- Modify: `frontend/src/components/CrawlProgressPanel.tsx`
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Add `queuedSources` prop and queued section**

Replace the entire `CrawlProgressPanel.tsx` with:

```typescript
import { X, Check, AlertCircle, Loader2, Minus } from 'lucide-react';
import type { SourceCrawlState, CrawlStreamSummary, CrawlStep } from '../types';

const STEP_LABELS: Record<CrawlStep, string> = {
  fetching: 'Fetching...',
  extracting: 'Extracting...',
  analysing: 'Analysing...',
  discovering: 'Discovering...',
};

function formatMs(ms: number | undefined): string {
  if (ms == null) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function SourceRow({ state }: { state: SourceCrawlState }) {
  let domain: string;
  try {
    domain = new URL(state.url).hostname;
  } catch {
    domain = state.url;
  }

  const stepLabel =
    state.status === 'running' && state.currentStep
      ? state.currentStep === 'discovering' && state.discoveryProgress
        ? `Discovering ${state.discoveryProgress.pages_crawled}/${state.discoveryProgress.max_pages} Seiten`
        : STEP_LABELS[state.currentStep]
      : null;

  const timingsParts: string[] = [];
  if (state.stepTimings) {
    const order: CrawlStep[] = ['fetching', 'extracting', 'analysing', 'discovering'];
    for (const step of order) {
      const ms = state.stepTimings[step];
      if (ms != null) {
        const shortLabel = step === 'analysing' ? 'analyse' : step === 'discovering' ? 'discover' : step === 'extracting' ? 'extract' : 'fetch';
        timingsParts.push(`${shortLabel} ${formatMs(ms)}`);
      }
    }
  }

  return (
    <div className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0">
      <span className="w-4 flex-shrink-0 flex justify-center">
        {state.status === 'done' ? (
          <Check className="w-3.5 h-3.5 text-signal-high" />
        ) : state.status === 'error' ? (
          <AlertCircle className="w-3.5 h-3.5 text-signal-low" />
        ) : state.status === 'running' ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-blue" />
        ) : (
          <Minus className="w-3.5 h-3.5 text-ink-muted" />
        )}
      </span>
      <span className="flex-1 truncate text-ink" title={state.url}>{domain}</span>
      <span className="text-xs text-ink-muted flex-shrink-0">
        {state.status === 'done' && state.result
          ? timingsParts.length > 0
            ? timingsParts.join(' · ')
            : `${state.result.new_documents} new · ${state.result.skipped} skipped`
          : state.status === 'error'
            ? (state.errorMessage ?? 'Error')
            : state.status === 'running' && stepLabel
              ? stepLabel
              : 'Waiting...'}
      </span>
    </div>
  );
}

interface Props {
  isRunning: boolean;
  sourceStates: SourceCrawlState[];
  summary: CrawlStreamSummary | null;
  connectionError: string | null;
  crawlTotal?: number;
  queuedSources?: { source_id: string; url: string }[];
  onCancel: () => void;
  onDismiss: () => void;
}

export function CrawlProgressPanel({
  isRunning,
  sourceStates,
  summary,
  connectionError,
  crawlTotal,
  queuedSources = [],
  onCancel,
  onDismiss,
}: Props) {
  if (!isRunning && !summary && !connectionError && sourceStates.length === 0 && queuedSources.length === 0) return null;

  const doneCount = sourceStates.filter(
    (s) => s.status === 'done' || s.status === 'error',
  ).length;
  const total = summary?.sources_processed ?? crawlTotal ?? sourceStates.length;
  const hasErrors = (summary?.total_errors ?? 0) > 0 || connectionError != null;
  const hasQueue = queuedSources.length > 0;

  const borderColor = hasErrors
    ? 'border-signal-low/40'
    : summary
      ? 'border-signal-high/40'
      : 'border-accent-blue/40';

  const runCounter = hasQueue ? ' (1/2)' : '';
  const headerText = connectionError
    ? `Connection failed: ${connectionError}`
    : isRunning
      ? `Crawling...${runCounter} (${doneCount}/${total})`
      : hasErrors
        ? `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs, ${summary?.total_errors ?? 0} errors`
        : `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs`;

  return (
    <div className={`mb-6 rounded-lg border ${borderColor} bg-app-card overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-app-border/30">
        <span className="text-sm font-medium text-ink">{headerText}</span>
        {isRunning ? (
          <button onClick={onCancel} className="text-xs text-ink-muted hover:text-ink px-2 py-0.5 rounded">
            Cancel
          </button>
        ) : (
          <button onClick={onDismiss} className="text-ink-muted hover:text-ink" aria-label="Dismiss">
            <X size={16} />
          </button>
        )}
      </div>
      <div>
        {sourceStates.map((s) => (
          <SourceRow key={s.source_id} state={s} />
        ))}
      </div>
      {hasQueue && (
        <>
          <div className="px-4 py-1.5 border-t border-app-border/30 bg-app-bg/40">
            <span className="text-xs text-ink-muted font-medium">Queued (startet danach)</span>
          </div>
          <div>
            {queuedSources.map((s) => {
              let domain: string;
              try { domain = new URL(s.url).hostname; } catch { domain = s.url; }
              return (
                <div key={s.source_id} className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0 opacity-60">
                  <Minus className="w-3.5 h-3.5 text-ink-muted flex-shrink-0" />
                  <span className="flex-1 truncate text-ink">{domain}</span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Pass `queuedSources` in `SourcesAdmin.tsx`**

In `frontend/src/pages/SourcesAdmin.tsx`, update the `<CrawlProgressPanel>` usage to pass the new prop:

```tsx
<CrawlProgressPanel
  isRunning={stream.isRunning}
  sourceStates={stream.sourceStates}
  summary={stream.summary}
  connectionError={stream.connectionError}
  crawlTotal={stream.crawlTotal}
  queuedSources={stream.queuedSources}
  onCancel={stream.cancel}
  onDismiss={stream.reset}
/>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Manual smoke test**

Start the dev stack: `docker compose -f docker-compose.dev.yml up -d`
Start the frontend: `cd frontend && npm run dev`

1. Navigate to Sources Admin
2. Click "Crawl" on one source — progress panel appears
3. While it runs, click "Crawl" on a second source — "Queued" section appears below the active sources, header shows "(1/2)"
4. First crawl completes — panel transitions to second run, header shows "(2/2)", queued section disappears
5. Second run completes — panel shows "Crawl complete"
6. Repeat steps 2–3, then **reload the page** mid-crawl — queued section should reappear after reload

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CrawlProgressPanel.tsx frontend/src/pages/SourcesAdmin.tsx
git commit -m "feat: CrawlProgressPanel shows queued sources section"
```

---

## Final verification

- [ ] Run backend tests: `cd backend && python -m pytest tests/ -v` — all pass
- [ ] Run TypeScript check: `cd frontend && npx tsc --noEmit` — no errors
- [ ] Smoke test the full queue flow manually (see Task 7 Step 4)
