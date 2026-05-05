# Crawl Progress & Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add granular crawl progress reporting (per-page discovery progress, per-step timing) and parallel source crawling to make crawls faster and more transparent.

**Architecture:** Extend the existing SSE streaming pipeline with new event types (`discovery_progress`, `step_timing`). Add timing columns to `CrawlRunSource` for persistence. Parallelize source crawling with `ThreadPoolExecutor` and page fetching within discovery with a `Semaphore`. Update the frontend to display real-time progress and historical timings.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, React 18, TypeScript

---

## Task 1: Add timing columns to CrawlRunSource model

**Files:**
- Modify: `backend/app/models/crawl_run.py`
- Modify: `backend/app/schemas/crawl_run.py`

- [ ] **Step 1: Add timing columns to CrawlRunSource model**

In `backend/app/models/crawl_run.py`, add four new columns to the `CrawlRunSource` class, after the `finished_at` column:

```python
    fetch_ms = Column(Integer, nullable=True)
    extract_ms = Column(Integer, nullable=True)
    analyse_ms = Column(Integer, nullable=True)
    discover_ms = Column(Integer, nullable=True)
```

- [ ] **Step 2: Add timing fields to CrawlRunSourceRead schema**

In `backend/app/schemas/crawl_run.py`, add four optional fields to `CrawlRunSourceRead`, after `finished_at`:

```python
    fetch_ms: Optional[int] = None
    extract_ms: Optional[int] = None
    analyse_ms: Optional[int] = None
    discover_ms: Optional[int] = None
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/crawl_run.py backend/app/schemas/crawl_run.py
git commit -m "feat: add timing columns to CrawlRunSource model and schema"
```

---

## Task 2: Create Alembic migration for timing columns

**Files:**
- Create: `backend/alembic/versions/<auto>_add_crawl_run_source_timing.py`

- [ ] **Step 1: Generate the migration**

```bash
cd backend && alembic revision --autogenerate -m "add_crawl_run_source_timing"
```

- [ ] **Step 2: Verify the generated migration**

Open the generated migration file and confirm it contains an `upgrade()` that adds `fetch_ms`, `extract_ms`, `analyse_ms`, `discover_ms` columns to `crawl_run_sources`, and a `downgrade()` that drops them.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add alembic migration for crawl run source timing columns"
```

---

## Task 3: Add config settings for concurrency

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add concurrency settings**

In `backend/app/config.py`, add two new fields to the `Settings` class, after the `assessment_threshold` field:

```python
    crawl_concurrency: int = 4
    discovery_concurrency: int = 3
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add crawl_concurrency and discovery_concurrency config settings"
```

---

## Task 4: Add timing measurement to crawl pipeline

**Files:**
- Modify: `backend/app/crawler/pipeline.py`

- [ ] **Step 1: Add timing measurement around each step in `run_crawl_source`**

In `backend/app/crawler/pipeline.py`, import `time` at the top and modify `run_crawl_source` to measure each step with `time.monotonic()` and emit `step_timing` events via the existing `emit()` function. The function should also return timing data in its result dict.

Replace the `emit` call and the step execution for each of the four steps (fetching, extracting, analysing, discovering) with timing-wrapped versions. The structure for each step:

```python
    import time

    # ... inside run_crawl_source ...

    emit({"type": "step", "source_id": source.id, "step": "fetching"})
    t0 = time.monotonic()
    fetch_result = fetch_url(source.url)
    fetch_ms = int((time.monotonic() - t0) * 1000)
    emit({"type": "step_timing", "source_id": source.id, "step": "fetching", "duration_ms": fetch_ms})
```

Apply the same pattern to extracting, analysing, and discovering steps. Store timings in a `timings` dict on the result:

```python
    result["timings"] = {
        "fetch_ms": fetch_ms,
        "extract_ms": extract_ms,
        "analyse_ms": analyse_ms,
        "discover_ms": discover_ms,
    }
```

Also add `time` to the import at the top of the file. The full import line should be:

```python
import logging
import time
from typing import Callable, Dict, Optional
```

Note: The `analysing` step can appear in two branches (same-url-changed and new-url). In both cases, wrap it with timing.

- [ ] **Step 2: Verify no syntax errors**

```bash
cd backend && python -c "from app.crawler.pipeline import run_crawl_source; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/crawler/pipeline.py
git commit -m "feat: add per-step timing measurement to crawl pipeline"
```

---

## Task 5: Add discovery_progress events to discovery module

**Files:**
- Modify: `backend/app/crawler/discovery.py`

- [ ] **Step 1: Add `progress_callback` parameter to `discover_and_crawl`**

Change the function signature from:

```python
def discover_and_crawl(
    source: Source, seed_html: str, db: Session, analyse: bool = True
) -> Dict:
```

to:

```python
def discover_and_crawl(
    source: Source, seed_html: str, db: Session, analyse: bool = True, progress_callback: Optional[Callable[[dict], None]] = None
) -> Dict:
```

Add the import at the top:

```python
from typing import Callable, Dict, List, Optional, Set
```

- [ ] **Step 2: Emit `discovery_progress` events during the crawl loop**

In the `while queue and pages_crawled < _MAX_PAGES_PER_RUN:` loop, after incrementing `pages_crawled` (or after processing each page), emit a progress event:

```python
        pages_crawled += 1
        if progress_callback:
            progress_callback({
                "type": "discovery_progress",
                "source_id": source.id,
                "pages_found": len(visited) + len(queue),
                "pages_crawled": pages_crawled,
                "max_pages": _MAX_PAGES_PER_RUN,
                "current_url": url,
            })
```

The `pages_crawled += 1` already exists in the loop — find it and add the callback immediately after it. Find the line:

```python
        pages_crawled = 0
```

and the increment line in the loop body and add the callback there.

- [ ] **Step 3: Update the call site in `pipeline.py`**

In `backend/app/crawler/pipeline.py`, update the call to `discover_and_crawl` to pass the `progress_callback`:

```python
    result["discovery"] = discover_and_crawl(
        source, fetch_result.html, db, analyse=analyse, progress_callback=emit
    )
```

- [ ] **Step 4: Verify no syntax errors**

```bash
cd backend && python -c "from app.crawler.discovery import discover_and_crawl; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/discovery.py backend/app/crawler/pipeline.py
git commit -m "feat: emit discovery_progress events during page crawling"
```

---

## Task 6: Parallelize source crawling with ThreadPoolExecutor

**Files:**
- Modify: `backend/app/routers/crawl.py`

- [ ] **Step 1: Add ThreadPoolExecutor imports**

At the top of `backend/app/routers/crawl.py`, add:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import settings
```

- [ ] **Step 2: Add helper function for single-source crawl within thread**

In `crawl.py`, add a helper function that encapsulates the per-source crawl logic currently inside the `for` loop in `_run_sources_in_thread`. This function will be submitted to the `ThreadPoolExecutor`:

```python
def _crawl_single_source(
    source_id: str,
    crawl_run_id: str,
    crs_id: str,
    source_url: str,
    thread_db: Session,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> Dict:
    source = thread_db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return {"new_documents": 0, "skipped": 0, "errors": 0}

    crs = (
        thread_db.query(CrawlRunSource)
        .filter(CrawlRunSource.id == crs_id)
        .first()
    )
    if not crs:
        return {"new_documents": 0, "skipped": 0, "errors": 0}

    crs.status = CrawlRunSourceStatus.running
    crs.started_at = datetime.now(timezone.utc)
    thread_db.commit()

    loop.call_soon_threadsafe(
        queue.put_nowait,
        {
            "type": "source_start",
            "crawl_run_id": crawl_run_id,
            "source_id": source_id,
            "url": source_url,
        },
    )

    def make_callback(sid: str, crs_id_val: str):
        def callback(event: dict):
            event_copy = dict(event)
            event_copy["crawl_run_id"] = crawl_run_id
            event_copy["source_id"] = sid
            if event.get("type") == "step":
                crs_obj = (
                    thread_db.query(CrawlRunSource)
                    .filter(CrawlRunSource.id == crs_id_val)
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
            progress_callback=make_callback(source_id, crs_id),
        )
    except Exception as e:
        thread_db.rollback()
        result = {"new_documents": 0, "skipped": 0, "errors": 1}
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "error",
                "crawl_run_id": crawl_run_id,
                "source_id": source_id,
                "message": str(e),
            },
        )

    timings = result.get("timings", {})

    if crs:
        crs.status = CrawlRunSourceStatus.completed
        crs.current_step = None
        crs.new_documents = result.get("new_documents", 0)
        crs.skipped = result.get("skipped", 0)
        crs.errors = result.get("errors", 0)
        crs.finished_at = datetime.now(timezone.utc)
        crs.fetch_ms = timings.get("fetch_ms")
        crs.extract_ms = timings.get("extract_ms")
        crs.analyse_ms = timings.get("analyse_ms")
        crs.discover_ms = timings.get("discover_ms")
        if result.get("errors", 0) > 0 and not result.get("new_documents") and not result.get("skipped"):
            crs.status = CrawlRunSourceStatus.failed
            if result.get("errors", 0) > 0:
                crs.error_message = "Errors during crawl"
        thread_db.commit()

    loop.call_soon_threadsafe(
        queue.put_nowait,
        {
            "type": "source_done",
            "crawl_run_id": crawl_run_id,
            "source_id": source_id,
            "new_documents": result.get("new_documents", 0),
            "skipped": result.get("skipped", 0),
            "errors": result.get("errors", 0),
            "timings": timings,
        },
    )

    return result
```

- [ ] **Step 3: Replace sequential loop with ThreadPoolExecutor**

In `_run_sources_in_thread`, replace the sequential `for i, source_id in enumerate(source_ids):` loop with parallel execution using `ThreadPoolExecutor`. The new body of `_run_sources_in_thread` after the initial `crawl_start` event should be:

```python
        total_new = 0
        total_skipped = 0
        total_errors = 0

        crs_map = {}
        for source_id in source_ids:
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
            crs_map[source_id] = crs.id

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
                    _crawl_single_source,
                    source_id,
                    crawl_run_id,
                    crs_id,
                    source.url,
                    SessionLocal(),
                    loop,
                    queue,
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
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        {
                            "type": "error",
                            "crawl_run_id": crawl_run_id,
                            "source_id": source_id,
                            "message": str(e),
                        },
                    )
```

**Important:** Each `ThreadPoolExecutor` worker gets its own `SessionLocal()` session, matching the thread-safety requirement. Remove the old sequential loop code entirely.

After the `with ThreadPoolExecutor...` block, keep the existing post-crawl logic (briefing + summaries + `crawl_done` event). The remainder of `_run_sources_in_thread` after the executor block should remain as-is.

- [ ] **Step 4: Verify no syntax errors**

```bash
cd backend && python -c "from app.routers.crawl import router; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/crawl.py
git commit -m "feat: parallelize source crawling with ThreadPoolExecutor"
```

---

## Task 7: Add discovery_concurrency to discovery module

**Files:**
- Modify: `backend/app/crawler/discovery.py`

- [ ] **Step 1: Add `threading` import and Semaphore-based fetch parallelism**

At the top of `backend/app/crawler/discovery.py`, add:

```python
import threading
```

And import settings:

```python
from app.config import settings
```

(`settings` is already imported — verify and keep it.)

- [ ] **Step 2: Replace `time.sleep(1)` with semaphore-based rate limiting**

In the `while queue and pages_crawled < _MAX_PAGES_PER_RUN:` loop, replace the `time.sleep(1)` line and the sequential `fetch_url(url)` call with a pattern using `threading.Semaphore`:

First, at the beginning of `discover_and_crawl()`, create a semaphore:

```python
    sem = threading.Semaphore(settings.discovery_concurrency)
```

Then replace the `time.sleep(1)` + `fetch_result = fetch_url(url)` block with:

```python
        sem.acquire()
        try:
            fetch_result = fetch_url(url)
        finally:
            sem.release()
```

This limits concurrent fetches to `discovery_concurrency` (default: 3) without artificial 1-second delays. Note: Since the discovery loop is still sequential (one URL at a time from the queue), this primarily ensures that if we later parallelize the loop, the semaphore is already in place. For now, the semaphore ensures max 3 concurrent fetches if we later change to parallel fetches, but in the current sequential loop, it acts as a simple rate-limiter — remove the `time.sleep(1)` entirely since the semaphore provides controlled access.

Actually, since the current code is *sequential* (one page at a time), adding a Semaphore alone doesn't change anything — we need to also parallelize the fetch within the loop. Let me revise the approach:

Keep the loop structure, but for the fetch step specifically, use a simple approach: just remove the `time.sleep(1)` and let the natural HTTP latency serve as rate limiting. The `Semaphore` will be used when we later do concurrent fetching. For now, we'll just remove the `time.sleep(1)` and add the import.

Replace:

```python
        time.sleep(1)
        fetch_result = fetch_url(url)
```

with:

```python
        fetch_result = fetch_url(url)
```

Remove the `time` import if no longer used. Check if `time` is used elsewhere in the file before removing.

- [ ] **Step 3: Verify no syntax errors**

```bash
cd backend && python -c "from app.crawler.discovery import discover_and_crawl; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/crawler/discovery.py
git commit -m "feat: remove artificial 1s delay from discovery fetch loop"
```

---

## Task 8: Update frontend types for new SSE events

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add new event types**

In `frontend/src/types/index.ts`, add the new SSE event interfaces after the existing `CrawlStepEvent`:

```typescript
export interface CrawlDiscoveryProgressEvent {
  type: 'discovery_progress';
  crawl_run_id: string;
  source_id: string;
  pages_found: number;
  pages_crawled: number;
  max_pages: number;
  current_url: string;
}

export interface CrawlStepTimingEvent {
  type: 'step_timing';
  crawl_run_id: string;
  source_id: string;
  step: CrawlStep;
  duration_ms: number;
}
```

Update the `CrawlEvent` union type to include the new events:

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
  | CrawlNoActiveRunEvent;
```

- [ ] **Step 2: Update `SourceCrawlState` and `CrawlRunSourceState` types**

Add timing and discovery progress fields to `SourceCrawlState`:

```typescript
export interface SourceCrawlState {
  source_id: string;
  url: string;
  status: 'waiting' | 'running' | 'done' | 'error';
  currentStep?: CrawlStep;
  result?: { new_documents: number; skipped: number; errors: number };
  errorMessage?: string;
  discoveryProgress?: { pages_found: number; pages_crawled: number; max_pages: number };
  stepTimings?: Partial<Record<CrawlStep, number>>;
}
```

Add timing fields to `CrawlRunSourceState`:

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
  fetch_ms?: number;
  extract_ms?: number;
  analyse_ms?: number;
  discover_ms?: number;
}
```

Update `CrawlSourceDoneEvent` to include timings:

```typescript
export interface CrawlSourceDoneEvent {
  type: 'source_done';
  crawl_run_id: string;
  source_id: string;
  new_documents: number;
  skipped: number;
  errors: number;
  timings?: {
    fetch_ms?: number;
    extract_ms?: number;
    analyse_ms?: number;
    discover_ms?: number;
  };
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add discovery_progress and step_timing event types to frontend"
```

---

## Task 9: Update useCrawlStream hook for new events

**Files:**
- Modify: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 1: Handle `discovery_progress` and `step_timing` events**

In the `handleEvent` switch statement, add two new cases after the `step` case:

```typescript
        case 'discovery_progress':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    discoveryProgress: {
                      pages_found: event.pages_found,
                      pages_crawled: event.pages_crawled,
                      max_pages: event.max_pages,
                    },
                  }
                : s,
            ),
          );
          break;
        case 'step_timing':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    stepTimings: {
                      ...s.stepTimings,
                      [event.step]: event.duration_ms,
                    },
                  }
                : s,
            ),
          );
          break;
```

- [ ] **Step 2: Update `source_done` handler to persist timings**

In the `source_done` case, add the timings from the event to the source state:

```typescript
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
                    stepTimings: event.timings
                      ? {
                          fetching: event.timings.fetch_ms,
                          extracting: event.timings.extract_ms,
                          analysing: event.timings.analyse_ms,
                          discovering: event.timings.discover_ms,
                        }
                      : s.stepTimings,
                  }
                : s,
            ),
          );
          break;
```

- [ ] **Step 3: Update `initial_state` handler to include timings from reconnect**

In the `initial_state` case, map the new `CrawlRunSourceState` timing fields:

```typescript
        case 'initial_state':
          setCrawlRunId(event.crawl_run_id);
          setCrawlTotal(event.total);
          setSourceStates(
            event.sources.map((s) => ({
              source_id: s.source_id,
              url: s.url,
              status: mapSourceStatus(s.status),
              currentStep: s.current_step as SourceCrawlState['currentStep'] | undefined,
              result:
                s.new_documents > 0 || s.skipped > 0 || s.errors > 0
                  ? { new_documents: s.new_documents, skipped: s.skipped, errors: s.errors }
                  : undefined,
              errorMessage: s.error_message,
              stepTimings: s.fetch_ms != null ? {
                fetching: s.fetch_ms,
                extracting: s.extract_ms,
                analysing: s.analyse_ms,
                discovering: s.discover_ms,
              } : undefined,
            })),
          );
          setIsRunning(true);
          break;
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useCrawlStream.ts
git commit -m "feat: handle discovery_progress and step_timing events in useCrawlStream"
```

---

## Task 10: Update CrawlProgressPanel for progress and timing display

**Files:**
- Modify: `frontend/src/components/CrawlProgressPanel.tsx`

- [ ] **Step 1: Update SourceRow to show discovery progress and elapsed time**

Replace the `SourceRow` component with an enhanced version that shows:
- Discovery progress as `X/Y Seiten` when step is `discovering`
- Step timings as a summary like `1.2s` when source is done

```tsx
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
          <Check className="w-3.5 h-3.5 text-green-400" />
        ) : state.status === 'error' ? (
          <AlertCircle className="w-3.5 h-3.5 text-red-400" />
        ) : state.status === 'running' ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
        ) : (
          <Minus className="w-3.5 h-3.5 text-ink-muted" />
        )}
      </span>
      <span className="flex-1 truncate" title={state.url}>{domain}</span>
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
```

- [ ] **Step 2: Verify the component imports are correct**

Ensure `SourceCrawlState` and `CrawlStep` are imported from `../types`. The existing imports should already include them.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/CrawlProgressPanel.tsx
git commit -m "feat: show discovery progress and step timings in CrawlProgressPanel"
```

---

## Task 11: Add CrawlRun detail page with timing visualization

**Files:**
- Create: `frontend/src/pages/CrawlRunDetailPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create the CrawlRunDetailPage component**

Create `frontend/src/pages/CrawlRunDetailPage.tsx` with a page that:
- Fetches a single CrawlRun via `GET /api/crawl-runs/{id}`
- Displays an overview (status, started_at, finished_at, totals)
- Lists each CrawlRunSource with:
  - URL, status badge, new/skipped/errors counts
  - Timing breakdown as a horizontal bar chart (proportional segments for fetch/extract/analyse/discover)
  - Raw timing numbers

```tsx
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRun } from '../types';

function formatMs(ms: number | undefined): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

function TimingBar({ timings }: { timings: Record<string, number | undefined> }) {
  const steps = [
    { key: 'fetch_ms', label: 'Fetch', color: 'bg-blue-400' },
    { key: 'extract_ms', label: 'Extract', color: 'bg-green-400' },
    { key: 'analyse_ms', label: 'Analyse', color: 'bg-purple-400' },
    { key: 'discover_ms', label: 'Discover', color: 'bg-yellow-400' },
  ];

  const total = steps.reduce((s, st) => s + (timings[st.key] ?? 0), 0);
  if (total === 0) return null;

  return (
    <div className="flex h-4 rounded overflow-hidden bg-app-card">
      {steps.map((st) => {
        const ms = timings[st.key] ?? 0;
        const pct = total > 0 ? (ms / total) * 100 : 0;
        return pct > 0.5 ? (
          <div
            key={st.key}
            className={`${st.color} flex items-center justify-center text-[10px] text-white font-medium`}
            style={{ width: `${pct}%` }}
            title={`${st.label}: ${formatMs(ms)}`}
          >
            {pct > 12 ? formatMs(ms) : ''}
          </div>
        ) : null;
      })}
    </div>
  );
}

export default function CrawlRunDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: crawlRun, isLoading, error } = useQuery({
    queryKey: ['crawlRun', id],
    queryFn: () => apiGet<CrawlRun>(`/crawl-runs/${id}`),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-6 text-ink-muted">Loading...</div>;
  if (error) return <div className="p-6 text-red-400">Error: {error.message}</div>;
  if (!crawlRun) return <div className="p-6 text-ink-muted">Crawl run not found</div>;

  const statusColors: Record<string, string> = {
    running: 'bg-blue-500/20 text-blue-400',
    completed: 'bg-green-500/20 text-green-400',
    failed: 'bg-red-500/20 text-red-400',
    cancelled: 'bg-gray-500/20 text-gray-400',
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold text-ink mb-4">Crawl Run Detail</h1>

      <div className="bg-app-card rounded-lg p-4 mb-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-ink-muted">Status</span>
          <div>
            <span className={`px-1.5 py-0.5 rounded text-xs ${statusColors[crawlRun.status] ?? ''}`}>
              {crawlRun.status}
            </span>
          </div>
        </div>
        <div>
          <span className="text-ink-muted">Started</span>
          <div>{new Date(crawlRun.started_at).toLocaleString()}</div>
        </div>
        <div>
          <span className="text-ink-muted">New / Skipped</span>
          <div>{crawlRun.total_new} / {crawlRun.total_skipped}</div>
        </div>
        <div>
          <span className="text-ink-muted">Errors</span>
          <div>{crawlRun.total_errors}</div>
        </div>
      </div>

      <h2 className="text-lg font-medium text-ink mb-3">Sources</h2>
      <div className="space-y-2">
        {crawlRun.sources.map((src) => {
          const timings: Record<string, number | undefined> = {
            fetch_ms: src.fetch_ms ?? undefined,
            extract_ms: src.extract_ms ?? undefined,
            analyse_ms: src.analyse_ms ?? undefined,
            discover_ms: src.discover_ms ?? undefined,
          };
          const totalMs = (src.fetch_ms ?? 0) + (src.extract_ms ?? 0) + (src.analyse_ms ?? 0) + (src.discover_ms ?? 0);
          return (
            <div key={src.id} className="bg-app-card rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-ink truncate" title={src.url}>
                  {(() => { try { return new URL(src.url).hostname; } catch { return src.url; } })()}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${statusColors[src.status] ?? ''}`}>
                  {src.status}
                </span>
              </div>
              {totalMs > 0 && <TimingBar timings={timings} />}
              <div className="flex gap-4 text-xs text-ink-muted mt-2">
                {src.fetch_ms != null && <span>Fetch {formatMs(src.fetch_ms)}</span>}
                {src.extract_ms != null && <span>Extract {formatMs(src.extract_ms)}</span>}
                {src.analyse_ms != null && <span>Analyse {formatMs(src.analyse_ms)}</span>}
                {src.discover_ms != null && <span>Discover {formatMs(src.discover_ms)}</span>}
                {totalMs > 0 && <span>Total {formatMs(totalMs)}</span>}
              </div>
              <div className="flex gap-3 text-xs text-ink-muted mt-1">
                <span>{src.new_documents} new</span>
                <span>{src.skipped} skipped</span>
                {src.errors > 0 && <span className="text-red-400">{src.errors} errors</span>}
                {src.error_message && <span className="text-red-400 truncate" title={src.error_message}>{src.error_message}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route in App.tsx**

In `frontend/src/App.tsx`, add the import:

```tsx
import CrawlRunDetailPage from './pages/CrawlRunDetailPage';
```

And add the route inside the authenticated routes (after the `admin/sources` route):

```tsx
            <Route path="crawl-runs/:id" element={<CrawlRunDetailPage />} />
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/CrawlRunDetailPage.tsx frontend/src/App.tsx
git commit -m "feat: add CrawlRunDetailPage with timing bar chart"
```

---

## Task 12: Update reconnect endpoint to include timings

**Files:**
- Modify: `backend/app/routers/crawl.py`

- [ ] **Step 1: Include timing fields in reconnect initial_state**

In the `reconnect_crawl` endpoint, update the per-source data dict to include the new timing fields:

```python
        sources_data.append(
            {
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
            }
        )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/crawl.py
git commit -m "feat: include timing fields in reconnect initial_state"
```

---

## Task 13: Add source detail timing section

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Add a collapsible "Last Crawl Timings" section per source**

In `SourcesAdmin.tsx`, after the existing `DiscoveredPagesSummary` component or inline in the source row expansion, add a small section that shows the latest timing data from the last CrawlRunSource for that source.

This requires adding a query hook for fetching the last crawl run for a source. Add to `frontend/src/hooks/useCrawlStream.ts` or create a new hook. The simplest approach: add a utility fetch and display inline.

In `SourcesAdmin.tsx`, inside the expanded source detail area, add:

```tsx
{lastCrawlTimings && (
  <div className="text-xs text-ink-muted mt-1 space-x-2">
    {lastCrawlTimings.fetch_ms != null && <span>Fetch {formatMs(lastCrawlTimings.fetch_ms)}</span>}
    {lastCrawlTimings.extract_ms != null && <span>Extract {formatMs(lastCrawlTimings.extract_ms)}</span>}
    {lastCrawlTimings.analyse_ms != null && <span>Analyse {formatMs(lastCrawlTimings.analyse_ms)}</span>}
    {lastCrawlTimings.discover_ms != null && <span>Discover {formatMs(lastCrawlTimings.discover_ms)}</span>}
  </div>
)}
```

This requires fetching the last CrawlRunSource for each expanded source. Add a simple `useQuery` call when a source is expanded:

```tsx
const { data: lastCrawlSource } = useQuery({
  queryKey: ['lastCrawlSource', source.id],
  queryFn: () => apiGet<CrawlRunSourceState[]>(`/crawl-runs/?limit=1`).then(runs => {
    // This is a simplified approach; in production you'd want an endpoint
    // that returns the latest CrawlRunSource for a given source_id
    return null;
  }),
  enabled: false, // Only fetch when expanded
});
```

Actually, a simpler approach: since the `CrawlRunSourceRead` schema now includes timing fields, and the existing `GET /api/crawl-runs/{id}` endpoint returns sources with timings, we can add a lightweight endpoint. But to keep the plan simple, let's add a query that fetches the most recent crawl run and finds the source within it.

For now, skip the source detail timing section and rely on the CrawlRunDetailPage for historical timing data. This can be added later as a follow-up.

- [ ] **Step 2: Commit (if any changes were made, otherwise skip)**

This task is intentionally deferred. The CrawlRunDetailPage already provides historical timing views. A per-source timing section in SourcesAdmin can be added in a follow-up.

---

## Task 14: Run backend tests

- [ ] **Step 1: Run existing tests**

```bash
cd backend && python -m pytest tests/ -v --timeout=30 2>&1 | tail -30
```

- [ ] **Step 2: Fix any failing tests**

If any tests fail, investigate and fix the root cause. Common issues:
- The `CrawlRunSource` model changes might affect test fixtures that create `CrawlRunSource` objects — they'll still work since the new columns are nullable
- The `discover_and_crawl` signature change adds an optional parameter, so existing calls will still work
- The `crawl.py` router changes to parallel execution may affect test ordering expectations

- [ ] **Step 3: Re-run tests until all pass**

```bash
cd backend && python -m pytest tests/ -v --timeout=30 2>&1 | tail -30
```

---

## Task 15: Final integration and deployment check

- [ ] **Step 1: Run Alembic migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Verify no TypeScript errors**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Start dev stack and do a manual smoke test**

```bash
docker compose -f docker-compose.dev.yml up -d
```

Then open the UI, trigger a crawl, and verify:
- Progress panel shows "Discovering X/50 Seiten" during discovery
- Step timings show after completion (e.g., "fetch 1.2s · extract 0.3s · analyse 8.1s · discover 45s")
- `/crawl-runs/:id` page shows timing bars
- Parallel execution works (multiple sources crawling simultaneously)