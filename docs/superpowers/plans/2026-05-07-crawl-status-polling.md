# Crawl Status Polling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the SSE-based crawl status system with a DB-polling approach that survives page refreshes, shows granular analysis progress, and moves queue auto-start into the backend.

**Architecture:** Backend stores all crawl/analysis progress in `CrawlRunSource` fields. A new `GET /api/crawl/status` endpoint reads and returns this state. Frontend polls it every 2s while running, 10s when done. Queue auto-start logic moves from frontend into the background thread that completes a run.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), React 18/TypeScript/react-query (frontend), Alembic (migrations)

---

## File Map

**Backend — create:**
- `backend/alembic/versions/<rev>_add_analyse_progress_to_crawl_run_source.py`

**Backend — modify:**
- `backend/app/models/crawl_run.py` — add 3 fields to `CrawlRunSource`
- `backend/app/schemas/crawl_run.py` — add fields to `CrawlRunSourceRead`, add `CrawlStatusResponse`
- `backend/app/crawler/pipeline.py` — pass actual doc URL in `analysis_progress` callback
- `backend/app/routers/crawl.py` — remove SSE code, add `_run_crawl_background`, `POST /start`, `GET /status`
- `backend/tests/test_crawl_router.py` — replace SSE tests, add polling tests

**Frontend — create:**
- `frontend/src/hooks/useCrawlStatus.ts` — polling hook, replaces `useCrawlStream.ts`

**Frontend — modify:**
- `frontend/src/types/index.ts` — add `CrawlStatusRun`, `CrawlStatusSource`, `CrawlStatusResponse`
- `frontend/src/components/CrawlProgressPanel.tsx` — new props, analysis URL display
- `frontend/src/pages/SourcesAdmin.tsx` — swap hook, update panel props

**Frontend — delete:**
- `frontend/src/hooks/useCrawlStream.ts`

---

## Task 1: DB Migration — add analyse progress fields

**Files:**
- Create: `backend/alembic/versions/<rev>_add_analyse_progress_to_crawl_run_source.py`
- Modify: `backend/app/models/crawl_run.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_crawl_router.py`, add at the bottom:

```python
def test_crawl_run_source_has_analyse_progress_fields(db_session, seed_source):
    from app.models.crawl_run import CrawlRun, CrawlRunSource, CrawlRunStatus, CrawlRunSourceStatus
    run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
    db_session.add(run)
    db_session.flush()
    crs = CrawlRunSource(
        crawl_run_id=run.id,
        source_id=seed_source.id,
        url=seed_source.url,
        status=CrawlRunSourceStatus.analysing,
        analyse_docs_done=2,
        analyse_docs_total=5,
        analyse_current_url="https://example.com/page",
    )
    db_session.add(crs)
    db_session.commit()
    db_session.expire_all()
    loaded = db_session.query(CrawlRunSource).filter(CrawlRunSource.id == crs.id).first()
    assert loaded.analyse_docs_done == 2
    assert loaded.analyse_docs_total == 5
    assert loaded.analyse_current_url == "https://example.com/page"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_run_source_has_analyse_progress_fields -v
```

Expected: FAIL with `TypeError` or `AttributeError` — fields don't exist yet.

- [ ] **Step 3: Add fields to the SQLAlchemy model**

In `backend/app/models/crawl_run.py`, after `analyse_finished_at`:

```python
    analyse_docs_done = Column(Integer, default=0, nullable=False)
    analyse_docs_total = Column(Integer, default=0, nullable=False)
    analyse_current_url = Column(String(2000), nullable=True)
```

- [ ] **Step 4: Generate and edit the Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add_analyse_progress_to_crawl_run_source"
```

Open the generated file. Verify `upgrade()` contains:

```python
op.add_column('crawl_run_sources', sa.Column('analyse_docs_done', sa.Integer(), nullable=False, server_default='0'))
op.add_column('crawl_run_sources', sa.Column('analyse_docs_total', sa.Integer(), nullable=False, server_default='0'))
op.add_column('crawl_run_sources', sa.Column('analyse_current_url', sa.String(length=2000), nullable=True))
```

And `downgrade()`:
```python
op.drop_column('crawl_run_sources', 'analyse_current_url')
op.drop_column('crawl_run_sources', 'analyse_docs_total')
op.drop_column('crawl_run_sources', 'analyse_docs_done')
```

If autogenerate missed anything, add the missing lines manually.

- [ ] **Step 5: Run migration**

```bash
cd backend && alembic upgrade head
```

Expected: `Running upgrade ... -> <rev>, add_analyse_progress_to_crawl_run_source`

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_run_source_has_analyse_progress_fields -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd backend && git add app/models/crawl_run.py alembic/versions/ && git commit -m "feat: add analyse_docs_done/total/current_url to CrawlRunSource"
```

---

## Task 2: Add new fields to CrawlRunSourceRead schema

**Files:**
- Modify: `backend/app/schemas/crawl_run.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_crawl_router.py`, add:

```python
def test_crawl_run_source_read_schema_has_analyse_progress(db_session, seed_source):
    from app.models.crawl_run import CrawlRun, CrawlRunSource, CrawlRunStatus, CrawlRunSourceStatus
    from app.schemas.crawl_run import CrawlRunSourceRead
    run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
    db_session.add(run)
    db_session.flush()
    crs = CrawlRunSource(
        crawl_run_id=run.id,
        source_id=seed_source.id,
        url=seed_source.url,
        status=CrawlRunSourceStatus.analysing,
        analyse_docs_done=3,
        analyse_docs_total=7,
        analyse_current_url="https://example.com/doc",
    )
    db_session.add(crs)
    db_session.commit()
    schema = CrawlRunSourceRead.model_validate(crs)
    assert schema.analyse_docs_done == 3
    assert schema.analyse_docs_total == 7
    assert schema.analyse_current_url == "https://example.com/doc"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_run_source_read_schema_has_analyse_progress -v
```

Expected: FAIL with `ValidationError` or `AttributeError`.

- [ ] **Step 3: Update CrawlRunSourceRead and add CrawlStatusResponse**

Replace `backend/app/schemas/crawl_run.py` with:

```python
from datetime import datetime
from typing import Optional, List, Dict, Any
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
    fetch_ms: Optional[int] = None
    extract_ms: Optional[int] = None
    analyse_ms: Optional[int] = None
    discover_ms: Optional[int] = None
    discover_pages_crawled: Optional[int] = None
    discover_pages_found: Optional[int] = None
    analyse_started_at: Optional[datetime] = None
    analyse_finished_at: Optional[datetime] = None
    analyse_docs_done: int = 0
    analyse_docs_total: int = 0
    analyse_current_url: Optional[str] = None


class CrawlRunRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    status: str
    started_at: Optional[datetime] = None
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
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_sources: int = 0
    total_new: int = 0
    total_skipped: int = 0
    total_errors: int = 0


class CrawlQueuedRunStatus(BaseModel):
    id: str
    sources: List[Dict[str, str]]


class CrawlStatusResponse(BaseModel):
    active_run: Optional[CrawlRunRead] = None
    queued_run: Optional[CrawlQueuedRunStatus] = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_run_source_read_schema_has_analyse_progress -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all existing tests pass (schema change is additive).

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/schemas/crawl_run.py tests/test_crawl_router.py && git commit -m "feat: add analyse progress fields to CrawlRunSourceRead schema"
```

---

## Task 3: Fix analysis_progress to pass actual document URL

**Files:**
- Modify: `backend/app/crawler/pipeline.py:272-294`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_crawl_router.py`, add:

```python
def test_analysis_progress_callback_receives_doc_url(db_session, seed_source):
    from unittest.mock import patch, MagicMock
    from app.crawler.pipeline import analyse_unanalysed_for_source
    from app.models.document import Document

    doc = Document(
        source_id=seed_source.id,
        url="https://seed.example.com/article",
        title="Test",
        content_markdown="word " * 60,
        content_hash="abc123",
        is_analysed=False,
    )
    db_session.add(doc)
    db_session.commit()

    received_urls = []

    def cb(event):
        if event.get("type") == "analysis_progress":
            received_urls.append(event.get("url"))

    with patch("app.crawler.pipeline._analyse_doc_worker", return_value=(doc.id, True)):
        analyse_unanalysed_for_source(seed_source, db_session, progress_callback=cb)

    assert len(received_urls) == 1
    assert received_urls[0] == "https://seed.example.com/article"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_analysis_progress_callback_receives_doc_url -v
```

Expected: FAIL — `received_urls[0]` is `""` not the article URL.

- [ ] **Step 3: Fix the emit call in pipeline.py**

In `backend/app/crawler/pipeline.py`, find the `as_completed` loop inside `analyse_unanalysed_for_source` (around line 277). Change:

```python
        for future in as_completed(futures):
            doc_id, success = future.result()
            with lock:
                completed_count += 1
                current = completed_count
            if success:
                result["analysed"] += 1
            else:
                result["errors"] += 1
            emit(
                {
                    "type": "analysis_progress",
                    "source_id": source.id,
                    "current": current,
                    "total": total,
                    "url": "",
                }
            )
```

To:

```python
        for future in as_completed(futures):
            doc_id, success = future.result()
            completed_doc = futures[future]
            with lock:
                completed_count += 1
                current = completed_count
            if success:
                result["analysed"] += 1
            else:
                result["errors"] += 1
            emit(
                {
                    "type": "analysis_progress",
                    "source_id": source.id,
                    "current": current,
                    "total": total,
                    "url": completed_doc.url,
                }
            )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_analysis_progress_callback_receives_doc_url -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/crawler/pipeline.py tests/test_crawl_router.py && git commit -m "fix: pass actual document URL in analysis_progress callback"
```

---

## Task 4: Refactor crawl.py — remove SSE, add polling-ready background functions

**Files:**
- Modify: `backend/app/routers/crawl.py`

This task replaces the SSE machinery with clean background functions. The DB-write logic is preserved; only the `loop`/`queue` plumbing is removed.

- [ ] **Step 1: Replace `_crawl_single_source` with `_crawl_source_worker`**

In `backend/app/routers/crawl.py`, replace the entire `_crawl_single_source` function (lines 61–185) with:

```python
def _crawl_source_worker(
    source_id: str,
    source_url: str,
    crs_id: str,
    crawl_run_id: str,
) -> Dict:
    worker_db = SessionLocal()
    try:
        source = worker_db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return {"new_documents": 0, "skipped": 0, "errors": 0}

        crs = worker_db.query(CrawlRunSource).filter(CrawlRunSource.id == crs_id).first()
        if not crs:
            return {"new_documents": 0, "skipped": 0, "errors": 0}

        crs.status = CrawlRunSourceStatus.running
        crs.started_at = datetime.now(timezone.utc)
        worker_db.commit()

        def make_callback(sid: str, crs_id_val: str):
            def callback(event: dict) -> None:
                if event.get("type") == "step":
                    step_name = event.get("step")
                    if step_name and step_name in [e.value for e in CrawlRunStep]:
                        crs_obj = (
                            worker_db.query(CrawlRunSource)
                            .filter(CrawlRunSource.id == crs_id_val)
                            .first()
                        )
                        if crs_obj:
                            crs_obj.current_step = CrawlRunStep(step_name)
                            worker_db.commit()
                elif event.get("type") == "discovery_progress":
                    crs_obj = (
                        worker_db.query(CrawlRunSource)
                        .filter(CrawlRunSource.id == crs_id_val)
                        .first()
                    )
                    if crs_obj:
                        crs_obj.discover_pages_crawled = event.get("pages_crawled")
                        crs_obj.discover_pages_found = event.get("pages_found")
                        worker_db.commit()
            return callback

        try:
            result = run_crawl_source(
                source,
                worker_db,
                analyse=True,
                progress_callback=make_callback(source_id, crs_id),
            )
        except Exception as e:
            worker_db.rollback()
            result = {"new_documents": 0, "skipped": 0, "errors": 1}

        timings = result.get("timings", {})

        crs = worker_db.query(CrawlRunSource).filter(CrawlRunSource.id == crs_id).first()
        if crs:
            crs.status = CrawlRunSourceStatus.completed
            crs.current_step = None
            crs.new_documents = result.get("new_documents", 0)
            crs.skipped = result.get("skipped", 0)
            crs.errors = result.get("errors", 0)
            crs.finished_at = datetime.now(timezone.utc)
            crs.fetch_ms = timings.get("fetch_ms")
            crs.extract_ms = timings.get("extract_ms")
            crs.discover_ms = timings.get("discover_ms")
            if (
                result.get("errors", 0) > 0
                and not result.get("new_documents")
                and not result.get("skipped")
            ):
                crs.status = CrawlRunSourceStatus.failed
                crs.error_message = "Errors during crawl"
            worker_db.commit()

        return result
    finally:
        worker_db.close()
```

- [ ] **Step 2: Replace `_run_sources_in_thread` with `_run_crawl_background`**

Replace the entire `_run_sources_in_thread` function (lines 188–490) with:

```python
def _run_crawl_background(
    crawl_run_id: str,
    source_ids: List[str],
) -> None:
    thread_db = SessionLocal()
    try:
        total = len(source_ids)
        total_new = 0
        total_skipped = 0
        total_errors = 0

        crs_map: Dict[str, str] = {}
        for sid in source_ids:
            crs_obj = (
                thread_db.query(CrawlRunSource)
                .filter(
                    CrawlRunSource.crawl_run_id == crawl_run_id,
                    CrawlRunSource.source_id == sid,
                )
                .first()
            )
            if crs_obj:
                crs_map[sid] = crs_obj.id

        with ThreadPoolExecutor(max_workers=settings.crawl_concurrency) as executor:
            future_to_source = {}
            for source_id in source_ids:
                crs_id = crs_map.get(source_id)
                if not crs_id:
                    continue
                source = thread_db.query(Source).filter(Source.id == source_id).first()
                if not source:
                    continue
                future = executor.submit(
                    _crawl_source_worker,
                    source_id,
                    source.url,
                    crs_id,
                    crawl_run_id,
                )
                future_to_source[future] = source_id

            for future in as_completed(future_to_source):
                source_id = future_to_source[future]
                try:
                    result = future.result()
                    total_new += result.get("new_documents", 0)
                    total_skipped += result.get("skipped", 0)
                    total_errors += result.get("errors", 0)
                except Exception as e:
                    total_errors += 1
                    logger.warning("Crawl worker failed for source %s: %s", source_id, e)

        crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        if crawl_run:
            crawl_run.total_new = total_new
            crawl_run.total_skipped = total_skipped
            crawl_run.total_errors = total_errors
            thread_db.commit()

            from app.models.source import AnalysisStatus as _AS
            from app.models.document import Document as _Doc

            thread_db.expire_all()

            analysis_needed = total_new > 0
            if not analysis_needed:
                for crs in crawl_run.sources:
                    src = thread_db.query(Source).filter(Source.id == crs.source_id).first()
                    if src and src.analysis_status == _AS.pending:
                        analysis_needed = True
                        break

            if analysis_needed:
                crawl_run = (
                    thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
                )
                for crs in crawl_run.sources:
                    if crs.status != CrawlRunSourceStatus.completed:
                        continue
                    src = thread_db.query(Source).filter(Source.id == crs.source_id).first()
                    if not src or src.analysis_status != _AS.pending:
                        if crs.new_documents <= 0:
                            continue

                    crs.status = CrawlRunSourceStatus.analysing
                    crs.analyse_started_at = datetime.now(timezone.utc)
                    thread_db.commit()

                    source = thread_db.query(Source).filter(Source.id == crs.source_id).first()
                    analysis_result = {"analysed": 0, "errors": 0, "analyse_ms": 0}
                    if source:
                        def make_analysis_callback(crs_id_val: str):
                            def cb(event: dict) -> None:
                                if event.get("type") == "analysis_progress":
                                    crs_obj = (
                                        thread_db.query(CrawlRunSource)
                                        .filter(CrawlRunSource.id == crs_id_val)
                                        .first()
                                    )
                                    if crs_obj:
                                        crs_obj.analyse_docs_done = event.get("current", 0)
                                        crs_obj.analyse_docs_total = event.get("total", 0)
                                        crs_obj.analyse_current_url = event.get("url") or None
                                        thread_db.commit()
                            return cb

                        try:
                            analysis_result = analyse_unanalysed_for_source(
                                source,
                                thread_db,
                                progress_callback=make_analysis_callback(crs.id),
                            )
                        except Exception as analysis_exc:
                            logger.warning(
                                "Analysis failed for source %s: %s",
                                crs.source_id,
                                analysis_exc,
                            )
                            analysis_result = {"analysed": 0, "errors": 1, "analyse_ms": 0}
                            try:
                                source.analysis_status = _AS.analysis_failed
                                thread_db.commit()
                            except Exception:
                                thread_db.rollback()

                    crs.analyse_ms = analysis_result.get("analyse_ms", 0)
                    crs.analyse_finished_at = datetime.now(timezone.utc)
                    crs.analyse_current_url = None
                    crs.status = CrawlRunSourceStatus.completed
                    thread_db.commit()

            crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
            if crawl_run:
                crawl_run.status = CrawlRunStatus.completed
                crawl_run.finished_at = datetime.now(timezone.utc)
                thread_db.commit()

            try:
                from app.analyser.briefing import generate_briefing_content
                from app.models.crawl_briefing import CrawlBriefing

                briefing_content = generate_briefing_content(thread_db, crawl_run_id=crawl_run_id)
                briefing = CrawlBriefing(
                    crawl_run_id=crawl_run_id,
                    content=briefing_content,
                    generated_at=datetime.now(timezone.utc),
                )
                thread_db.add(briefing)
                thread_db.commit()
            except Exception as e:
                logger.warning("Auto-briefing generation failed: %s", e)

            try:
                from app.models.signal import Signal
                from app.models.company import Company
                from app.assessor.summarizer import generate_competitor_summary

                crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
                if crawl_run and crawl_run.started_at is not None:
                    company_ids_with_new_signals = (
                        thread_db.query(Signal.company_id)
                        .filter(Signal.created_at >= crawl_run.started_at)
                        .distinct()
                        .all()
                    )
                    for (cid,) in company_ids_with_new_signals:
                        company = thread_db.query(Company).filter(Company.id == cid).first()
                        if company:
                            for period in ("7d", "30d"):
                                try:
                                    generate_competitor_summary(company, period, thread_db)
                                except Exception as period_exc:
                                    logger.warning(
                                        "Summary gen failed for %s/%s: %s",
                                        company.name,
                                        period,
                                        period_exc,
                                    )
            except Exception as e:
                logger.warning("Post-crawl summary trigger failed: %s", e)

            # Auto-start queued run if one exists
            queued_run = (
                thread_db.query(CrawlRun)
                .filter(CrawlRun.status == CrawlRunStatus.queued)
                .first()
            )
            if queued_run:
                queued_source_ids = [crs.source_id for crs in queued_run.sources]
                queued_run.status = CrawlRunStatus.running
                queued_run.started_at = datetime.now(timezone.utc)
                thread_db.commit()
                threading.Thread(
                    target=_run_crawl_background,
                    args=(queued_run.id, queued_source_ids),
                    daemon=True,
                ).start()

    except Exception as e:
        crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        if crawl_run:
            crawl_run.status = CrawlRunStatus.failed
            crawl_run.finished_at = datetime.now(timezone.utc)
            thread_db.commit()
        logger.exception("Background crawl failed for run %s: %s", crawl_run_id, e)
    finally:
        thread_db.close()
```

- [ ] **Step 3: Remove SSE functions and endpoints, add new endpoints**

Remove from `crawl.py`:
- The entire `_sse_generator` function
- `@router.get("/stream")` endpoint (`stream_all_sources`)
- `@router.get("/stream/queued")` endpoint (`stream_queued_run`)
- `@router.get("/stream/{source_id}")` endpoint (`stream_single_source`)
- `@router.get("/reconnect")` endpoint (`reconnect_crawl`)

Also remove unused imports: `asyncio`, `AsyncGenerator` from the import block.

Then add these two new endpoints after the `cancel_crawl` endpoint:

```python
@router.post("/start", status_code=202)
def start_crawl_background(db: Session = Depends(get_db)) -> Dict[str, Any]:
    active_sources = (
        db.query(Source)
        .filter(Source.is_active == True)  # noqa: E712
        .order_by(Source.last_crawled_at.asc().nullsfirst())
        .all()
    )
    if not active_sources:
        return {"crawl_run_id": None, "status": "no_active_sources", "total_sources": 0}
    source_ids = [s.id for s in active_sources]
    crawl_run = _create_crawl_run(source_ids, db)
    threading.Thread(
        target=_run_crawl_background,
        args=(crawl_run.id, source_ids),
        daemon=True,
    ).start()
    return {"crawl_run_id": crawl_run.id, "status": "running", "total_sources": len(source_ids)}


@router.post("/start/{source_id}", status_code=202)
def start_single_source_background(
    source_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    crawl_run = _create_crawl_run([source_id], db)
    threading.Thread(
        target=_run_crawl_background,
        args=(crawl_run.id, [source_id]),
        daemon=True,
    ).start()
    return {"crawl_run_id": crawl_run.id, "status": "running", "total_sources": 1}
```

- [ ] **Step 4: Run the full test suite**

```bash
cd backend && python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: Tests that reference `/api/crawl/stream` or `/api/crawl/reconnect` will now FAIL. That's expected — they'll be replaced in Task 5.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/routers/crawl.py && git commit -m "feat: replace SSE crawl with polling-ready background functions"
```

---

## Task 5: Add GET /api/crawl/status endpoint

**Files:**
- Modify: `backend/app/routers/crawl.py`
- Test: `backend/tests/test_crawl_router.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_crawl_router.py`, add:

```python
def test_crawl_status_no_active_run(client):
    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"] is None
    assert data["queued_run"] is None


def test_crawl_status_running_run(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    setup_db = TestSessionLocal()
    try:
        run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(run)
        setup_db.flush()
        crs = CrawlRunSource(
            crawl_run_id=run.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.analysing,
            analyse_docs_done=1,
            analyse_docs_total=3,
            analyse_current_url="https://example.com/p",
        )
        setup_db.add(crs)
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"] is not None
    assert data["active_run"]["status"] == "running"
    assert len(data["active_run"]["sources"]) == 1
    src = data["active_run"]["sources"][0]
    assert src["status"] == "analysing"
    assert src["analyse_docs_done"] == 1
    assert src["analyse_docs_total"] == 3
    assert src["analyse_current_url"] == "https://example.com/p"


def test_crawl_status_shows_queued_run(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    setup_db = TestSessionLocal()
    try:
        running = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        setup_db.add(running)
        queued = CrawlRun(status=CrawlRunStatus.queued, total_sources=1)
        setup_db.add(queued)
        setup_db.flush()
        setup_db.add(CrawlRunSource(
            crawl_run_id=running.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.running,
        ))
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

    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"]["status"] == "running"
    assert data["queued_run"] is not None
    assert data["queued_run"]["id"] == queued_id
    assert len(data["queued_run"]["sources"]) == 1


def test_crawl_status_returns_recent_completed_run(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    from datetime import timedelta
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    setup_db = TestSessionLocal()
    try:
        run = CrawlRun(
            status=CrawlRunStatus.completed,
            total_sources=1,
            total_new=2,
            finished_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        setup_db.add(run)
        setup_db.commit()
    finally:
        setup_db.close()

    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["active_run"] is not None
    assert data["active_run"]["status"] == "completed"
    assert data["active_run"]["total_new"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_status_no_active_run tests/test_crawl_router.py::test_crawl_status_running_run -v
```

Expected: FAIL with 404 (endpoint doesn't exist yet).

- [ ] **Step 3: Add the status endpoint to crawl.py**

Add after the `start_single_source_background` endpoint:

```python
@router.get("/status")
def get_crawl_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    from app.schemas.crawl_run import CrawlRunRead, CrawlQueuedRunStatus
    from datetime import timedelta

    active_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).first()

    if not active_run:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        active_run = (
            db.query(CrawlRun)
            .filter(
                CrawlRun.status.in_(
                    [CrawlRunStatus.completed, CrawlRunStatus.failed, CrawlRunStatus.cancelled]
                ),
                CrawlRun.finished_at >= cutoff,
            )
            .order_by(CrawlRun.finished_at.desc())
            .first()
        )

    queued_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()

    return {
        "active_run": CrawlRunRead.model_validate(active_run).model_dump() if active_run else None,
        "queued_run": CrawlQueuedRunStatus(
            id=queued_run.id,
            sources=[{"source_id": crs.source_id, "url": crs.url} for crs in queued_run.sources],
        ).model_dump() if queued_run else None,
    }
```

- [ ] **Step 4: Run the new status tests**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_status_no_active_run tests/test_crawl_router.py::test_crawl_status_running_run tests/test_crawl_router.py::test_crawl_status_shows_queued_run tests/test_crawl_router.py::test_crawl_status_returns_recent_completed_run -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/routers/crawl.py tests/test_crawl_router.py && git commit -m "feat: add GET /api/crawl/status polling endpoint"
```

---

## Task 6: Replace SSE tests with polling tests

**Files:**
- Modify: `backend/tests/test_crawl_router.py`

- [ ] **Step 1: Remove all SSE-specific tests**

Delete these test functions from `test_crawl_router.py`:
- `test_stream_all_sources_returns_events`
- `test_stream_single_source_returns_events`
- `test_stream_nonexistent_source_returns_404`
- `test_stream_creates_crawl_run_in_db`
- `test_stream_cancels_previous_running_crawl`
- `test_reconnect_no_active_run`
- `test_reconnect_with_active_run`
- `test_reconnect_initial_state_analysis_phase_active`
- `test_reconnect_initial_state_analysis_phase_inactive`
- `test_reconnect_returns_queued_state`
- `test_reconnect_queued_state_only_when_no_running_run`
- `test_stream_queued_returns_404_when_no_queue`
- `test_stream_queued_runs_queued_sources`
- `test_crawl_done_includes_analysis_pending_true`
- `test_crawl_done_includes_analysis_pending_false`
- `test_stream_all_sources_includes_analysis_events`
- `test_stream_skips_analysis_when_no_new_documents`

Also remove `import json` if it's no longer used elsewhere in the file.

- [ ] **Step 2: Add tests for POST /start endpoints**

Add to `test_crawl_router.py`:

```python
def test_start_background_returns_202(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl._run_crawl_background"),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        response = client.post("/api/crawl/start")

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "running"
    assert data["crawl_run_id"] is not None
    assert data["total_sources"] == 1


def test_start_single_source_returns_202(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        response = client.post(f"/api/crawl/start/{seed_source.id}")

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "running"
    assert data["total_sources"] == 1


def test_start_creates_crawl_run_in_db(client, seed_source, db_engine):
    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        response = client.post("/api/crawl/start")

    assert response.status_code == 202
    verify_db = TestSessionLocal()
    try:
        runs = verify_db.query(CrawlRun).all()
        assert len(runs) == 1
        assert runs[0].status == CrawlRunStatus.running
        assert runs[0].total_sources == 1
    finally:
        verify_db.close()


def test_start_nonexistent_source_returns_404(client):
    response = client.post("/api/crawl/start/nonexistent-id")
    assert response.status_code == 404
```

- [ ] **Step 3: Run the full test suite**

```bash
cd backend && python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
cd backend && git add tests/test_crawl_router.py && git commit -m "test: replace SSE tests with polling endpoint tests"
```

---

## Task 7: Add frontend types for polling API

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add new types**

In `frontend/src/types/index.ts`, after the `CrawlRun` interface (around line 358), add:

```typescript
export interface CrawlStatusSource {
  id: string;
  crawl_run_id: string;
  source_id: string;
  url: string;
  status: 'pending' | 'running' | 'analysing' | 'completed' | 'failed' | 'skipped';
  current_step: string | null;
  new_documents: number;
  skipped: number;
  errors: number;
  error_message: string | null;
  fetch_ms: number | null;
  extract_ms: number | null;
  analyse_ms: number | null;
  discover_ms: number | null;
  discover_pages_crawled: number | null;
  discover_pages_found: number | null;
  analyse_docs_done: number;
  analyse_docs_total: number;
  analyse_current_url: string | null;
}

export interface CrawlStatusRun {
  id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  finished_at: string | null;
  total_sources: number;
  total_new: number;
  total_skipped: number;
  total_errors: number;
  sources: CrawlStatusSource[];
}

export interface CrawlStatusQueuedRun {
  id: string;
  sources: { source_id: string; url: string }[];
}

export interface CrawlStatusResponse {
  active_run: CrawlStatusRun | null;
  queued_run: CrawlStatusQueuedRun | null;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to the new types.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/types/index.ts && git commit -m "feat: add CrawlStatusRun/Source/Response types"
```

---

## Task 8: Create useCrawlStatus hook

**Files:**
- Create: `frontend/src/hooks/useCrawlStatus.ts`
- Delete: `frontend/src/hooks/useCrawlStream.ts` (after SourcesAdmin is updated in Task 10)

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/useCrawlStatus.ts`:

```typescript
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type { CrawlStatusResponse, CrawlStatusRun, CrawlStatusQueuedRun, CrawlPhase } from '../types';

export function useCrawlStatus() {
  const qc = useQueryClient();
  const dismissedRef = useRef(false);
  const [dismissed, setDismissed] = useState(false);
  const prevStatusRef = useRef<string | undefined>(undefined);

  const { data } = useQuery<CrawlStatusResponse>({
    queryKey: ['crawlStatus'],
    queryFn: () => apiGet<CrawlStatusResponse>('/crawl/status'),
    refetchInterval: (query) => {
      if (dismissedRef.current) return false;
      const status = query.state.data?.active_run?.status;
      if (status === 'running') return 2000;
      if (query.state.data?.active_run) return 10000;
      return false;
    },
    refetchOnMount: true,
    staleTime: 0,
  });

  useEffect(() => {
    const status = data?.active_run?.status;
    if (prevStatusRef.current === 'running' && status !== 'running') {
      qc.invalidateQueries({ queryKey: ['sources'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['crawlRuns'] });
      qc.invalidateQueries({ queryKey: ['activeCrawlRun'] });
      qc.invalidateQueries({ queryKey: ['discoveredPagesStats'] });
      qc.invalidateQueries({ queryKey: ['signalsOverTime'] });
      qc.invalidateQueries({ queryKey: ['signalDistribution'] });
      qc.invalidateQueries({ queryKey: ['sourceCandidates'] });
    }
    if (status === 'running') {
      dismissedRef.current = false;
      setDismissed(false);
    }
    prevStatusRef.current = status;
  }, [data, qc]);

  const start = useCallback(
    async (sourceId?: string) => {
      dismissedRef.current = false;
      setDismissed(false);
      const path = sourceId ? `/crawl/start/${sourceId}` : '/crawl/start';
      try {
        await apiPost(path);
      } catch {
        // error handled by caller or ignored
      }
      qc.invalidateQueries({ queryKey: ['crawlStatus'] });
    },
    [qc],
  );

  const cancel = useCallback(async () => {
    try {
      await apiPost('/crawl/cancel');
    } catch {
      // ignore
    }
    qc.invalidateQueries({ queryKey: ['crawlStatus'] });
  }, [qc]);

  const dismiss = useCallback(() => {
    dismissedRef.current = true;
    setDismissed(true);
  }, []);

  const run: CrawlStatusRun | null = data?.active_run ?? null;
  const queuedRun: CrawlStatusQueuedRun | null = data?.queued_run ?? null;

  const phase = useMemo((): CrawlPhase => {
    if (dismissed || !run) return 'idle';
    if (run.status === 'running') {
      return run.sources.some((s) => s.status === 'analysing') ? 'analysing' : 'crawling';
    }
    if (run.status === 'completed') return 'done';
    return 'idle';
  }, [run, dismissed]);

  const isRunning = run?.status === 'running';

  return { run, queuedRun, phase, isRunning, start, cancel, dismiss };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/hooks/useCrawlStatus.ts && git commit -m "feat: add useCrawlStatus polling hook"
```

---

## Task 9: Update CrawlProgressPanel

**Files:**
- Modify: `frontend/src/components/CrawlProgressPanel.tsx`

- [ ] **Step 1: Replace the component**

Replace the entire contents of `frontend/src/components/CrawlProgressPanel.tsx`:

```typescript
import { X, Check, AlertCircle, Loader2, Minus } from 'lucide-react';
import type { CrawlStatusRun, CrawlStatusSource, CrawlStatusQueuedRun, CrawlPhase } from '../types';

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function SourceRow({ source }: { source: CrawlStatusSource }) {
  const isRunning = source.status === 'running' || source.status === 'analysing';
  const isDone = source.status === 'completed';
  const isError = source.status === 'failed';

  let detail = 'Waiting...';
  if (source.status === 'analysing') {
    detail = source.analyse_docs_total > 0
      ? `Analysiere ${source.analyse_docs_done}/${source.analyse_docs_total}${source.analyse_current_url ? ` — ${source.analyse_current_url}` : ''}`
      : 'Analysiere...';
  } else if (source.status === 'running' && source.current_step) {
    const labels: Record<string, string> = {
      fetching: 'Fetching...',
      extracting: 'Extracting...',
      discovering: source.discover_pages_crawled != null
        ? `Discovering ${source.discover_pages_crawled} Seiten`
        : 'Discovering...',
    };
    detail = labels[source.current_step] ?? source.current_step;
  } else if (isDone) {
    const parts: string[] = [];
    if (source.fetch_ms) parts.push(`fetch ${formatMs(source.fetch_ms)}`);
    if (source.extract_ms) parts.push(`extract ${formatMs(source.extract_ms)}`);
    if (source.discover_ms) parts.push(`discover ${formatMs(source.discover_ms)}`);
    if (source.analyse_ms) parts.push(`analyse ${formatMs(source.analyse_ms)}`);
    detail = parts.length > 0
      ? parts.join(' · ')
      : `${source.new_documents} new · ${source.skipped} skipped`;
  } else if (isError) {
    detail = source.error_message ?? 'Error';
  }

  return (
    <div className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0">
      <span className="w-4 flex-shrink-0 flex justify-center">
        {isDone ? (
          <Check className="w-3.5 h-3.5 text-signal-high" />
        ) : isError ? (
          <AlertCircle className="w-3.5 h-3.5 text-signal-low" />
        ) : isRunning ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-blue" />
        ) : (
          <Minus className="w-3.5 h-3.5 text-ink-muted" />
        )}
      </span>
      <span className="flex-1 truncate text-ink" title={source.url}>{source.url}</span>
      <span className="text-xs text-ink-muted flex-shrink-0 max-w-xs truncate" title={detail}>
        {detail}
      </span>
    </div>
  );
}

interface Props {
  phase: CrawlPhase;
  run: CrawlStatusRun | null;
  queuedRun?: CrawlStatusQueuedRun | null;
  onCancel: () => void;
  onDismiss: () => void;
}

export function CrawlProgressPanel({ phase, run, queuedRun, onCancel, onDismiss }: Props) {
  if (phase === 'idle' || !run) return null;

  const sources = run.sources;
  const doneCount = sources.filter((s) => s.status === 'completed' || s.status === 'failed').length;
  const total = run.total_sources;
  const hasErrors = run.total_errors > 0;
  const isActive = phase === 'crawling' || phase === 'analysing';
  const hasQueue = (queuedRun?.sources.length ?? 0) > 0;

  const analysingSource = sources.find((s) => s.status === 'analysing');
  const analysisTotal = analysingSource?.analyse_docs_total ?? 0;
  const analysisDone = analysingSource?.analyse_docs_done ?? 0;

  const borderColor = hasErrors
    ? 'border-signal-low/40'
    : phase === 'done'
      ? 'border-signal-high/40'
      : 'border-accent-blue/40';

  const queueSuffix = hasQueue ? ' (1/2)' : '';
  const headerText =
    phase === 'crawling'
      ? `Crawl läuft…${queueSuffix} (${doneCount}/${total})`
      : phase === 'analysing'
        ? analysisTotal > 0
          ? `Analyse läuft… (${analysisDone}/${analysisTotal} Docs)`
          : 'Analyse läuft…'
        : hasErrors
          ? `Fertig — ${total} Sources, ${run.total_new} neue Docs, ${run.total_errors} Fehler`
          : `Fertig — ${run.total_new} neue Docs`;

  return (
    <div className={`mb-6 rounded-lg border ${borderColor} bg-app-card overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-app-border/30">
        <span className="text-sm font-medium text-ink">{headerText}</span>
        {isActive ? (
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
        {sources.map((s) => (
          <SourceRow key={s.source_id} source={s} />
        ))}
      </div>
      {hasQueue && queuedRun && (
        <>
          <div className="px-4 py-1.5 border-t border-app-border/30 bg-app-bg/40">
            <span className="text-xs text-ink-muted font-medium">Queued (startet danach)</span>
          </div>
          <div>
            {queuedRun.sources.map((s) => (
              <div key={s.source_id} className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0 opacity-60">
                <Minus className="w-3.5 h-3.5 text-ink-muted flex-shrink-0" />
                <span className="flex-1 truncate text-ink" title={s.url}>{s.url}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: errors only in `SourcesAdmin.tsx` (uses old props) — that's expected, fixed in Task 10.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/components/CrawlProgressPanel.tsx && git commit -m "feat: update CrawlProgressPanel to use polling data model"
```

---

## Task 10: Update SourcesAdmin to use new hook

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`
- Delete: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 1: Update imports in SourcesAdmin.tsx**

At the top of `SourcesAdmin.tsx`, replace:

```typescript
import { useCrawlStream } from '../hooks/useCrawlStream';
```

with:

```typescript
import { useCrawlStatus } from '../hooks/useCrawlStatus';
```

- [ ] **Step 2: Replace stream hook usage**

Replace:

```typescript
const stream = useCrawlStream();
```

with:

```typescript
const crawl = useCrawlStatus();
```

- [ ] **Step 3: Update the "Run Full Crawl" button**

Replace:

```typescript
<button onClick={() => stream.start()} disabled={stream.isRunning} className="btn-primary flex items-center gap-2">
  <Play size={16} /> {stream.phase === 'analysing' ? 'Analysiere...' : stream.phase === 'crawling' ? 'Crawling...' : 'Run Full Crawl'}
</button>
```

with:

```typescript
<button onClick={() => crawl.start()} disabled={crawl.isRunning} className="btn-primary flex items-center gap-2">
  <Play size={16} /> {crawl.phase === 'analysing' ? 'Analysiere...' : crawl.phase === 'crawling' ? 'Crawling...' : 'Run Full Crawl'}
</button>
```

- [ ] **Step 4: Update CrawlProgressPanel props**

Replace:

```typescript
<CrawlProgressPanel
  phase={stream.phase}
  analysisDocsTotal={stream.analysisDocsTotal}
  analysisDocsDone={stream.analysisDocsDone}
  sourceStates={stream.sourceStates}
  summary={stream.summary}
  connectionError={stream.connectionError}
  crawlTotal={stream.crawlTotal}
  queuedSources={stream.queuedSources}
  onCancel={stream.cancel}
  onDismiss={stream.reset}
/>
```

with:

```typescript
<CrawlProgressPanel
  phase={crawl.phase}
  run={crawl.run}
  queuedRun={crawl.queuedRun}
  onCancel={crawl.cancel}
  onDismiss={crawl.dismiss}
/>
```

- [ ] **Step 5: Update per-source crawl trigger**

Replace:

```typescript
function handleCrawlSource(sourceId: string) {
  stream.start(sourceId);
}
```

with:

```typescript
function handleCrawlSource(sourceId: string) {
  crawl.start(sourceId);
}
```

- [ ] **Step 6: Verify TypeScript compiles cleanly**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 7: Delete useCrawlStream.ts**

```bash
rm frontend/src/hooks/useCrawlStream.ts
```

Run TypeScript again to confirm nothing else imports it:

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 8: Run the full backend test suite one last time**

```bash
cd backend && python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
cd frontend && git add src/pages/SourcesAdmin.tsx && git rm src/hooks/useCrawlStream.ts && git commit -m "feat: wire SourcesAdmin to polling-based useCrawlStatus hook"
```

---

## Done

After all tasks complete:

- `GET /api/crawl/status` returns current run state from DB with full analysis progress
- `POST /api/crawl/start[/{source_id}]` fires background crawl, returns immediately
- Page refresh shows in-progress or recent crawl automatically
- Analysis progress (docs done/total + current URL) visible per source in the panel
- Queue auto-starts in backend thread — no frontend required
- `useCrawlStream.ts` and all SSE endpoints removed
