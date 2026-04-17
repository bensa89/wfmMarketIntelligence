# Crawl Progress (SSE) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stream live crawl progress via SSE, showing per-step status (fetching/extracting/analysing/discovering) in a CrawlProgressPanel in SourcesAdmin, with a final summary after completion.

**Architecture:** Backend adds two GET `/api/crawl/stream[/{source_id}]` endpoints that use `StreamingResponse` + `asyncio.Queue` + a background thread to stream JSON events. The pipeline gains an optional `progress_callback` parameter. Frontend reads the stream via `fetch` + `ReadableStream` (to support Basic Auth headers) and drives a new `CrawlProgressPanel` component.

**Tech Stack:** FastAPI StreamingResponse, asyncio.Queue, threading.Thread, React useState/useRef/useCallback, fetch ReadableStream, lucide-react icons.

---

## File Map

**Create:**
- `frontend/src/hooks/useCrawlStream.ts` — hook that opens/reads SSE stream, manages state
- `frontend/src/components/CrawlProgressPanel.tsx` — panel component

**Modify:**
- `backend/app/crawler/pipeline.py` — add `progress_callback` param, emit step/error events
- `backend/app/routers/crawl.py` — add SSE stream endpoints
- `frontend/src/types/index.ts` — add crawl stream types
- `frontend/src/pages/SourcesAdmin.tsx` — integrate hook + panel, replace crawlAll banner
- `backend/tests/test_crawler.py` — add callback tests
- `backend/tests/test_crawl_router.py` — add SSE endpoint tests

---

## Task 1: Add `progress_callback` to `run_crawl_source`

**Files:**
- Modify: `backend/app/crawler/pipeline.py`
- Test: `backend/tests/test_crawler.py`

- [ ] **Step 1.1: Write failing tests for callback behaviour**

Append to `backend/tests/test_crawler.py`:

```python
def test_run_crawl_source_calls_progress_callback(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType

    company = Company(name="ATOSS", slug="atoss-cb", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/cb", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html="<html><head><title>T</title></head><body><p>New content</p></body></html>",
            final_url="https://atoss.com/cb",
            status_code=200,
        )
    )

    events = []

    with patch("app.crawler.pipeline.fetch_url", mock_fetch):
        run_crawl_source(
            source, db_session, analyse=False, progress_callback=lambda e: events.append(e)
        )

    steps = [e["step"] for e in events if e.get("type") == "step"]
    assert "fetching" in steps
    assert "extracting" in steps
    assert "discovering" in steps
    assert all(e.get("source_id") == source.id for e in events)


def test_run_crawl_source_callback_on_fetch_failure(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType

    company = Company(name="ATOSS", slug="atoss-cb-fail", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/cb-fail",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    events = []

    with patch("app.crawler.pipeline.fetch_url", return_value=None):
        result = run_crawl_source(
            source, db_session, analyse=False, progress_callback=lambda e: events.append(e)
        )

    assert result["errors"] == 1
    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) == 1
    assert error_events[0]["source_id"] == source.id
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_crawler.py::test_run_crawl_source_calls_progress_callback tests/test_crawler.py::test_run_crawl_source_callback_on_fetch_failure -v
```

Expected: FAIL with `TypeError: run_crawl_source() got an unexpected keyword argument 'progress_callback'`

- [ ] **Step 1.3: Implement `progress_callback` in pipeline**

Replace `backend/app/crawler/pipeline.py` entirely with:

```python
from typing import Callable, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.source import Source
from app.models.document import Document
from app.crawler.fetcher import fetch_url
from app.crawler.extractor import extract_content
from app.crawler.discovery import discover_and_crawl


def run_crawl_source(
    source: Source,
    db: Session,
    analyse: bool = True,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> Dict:
    def emit(event: dict):
        if progress_callback:
            progress_callback(event)

    result = {
        "source_id": source.id,
        "new_documents": 0,
        "skipped": 0,
        "errors": 0,
        "discovery": {},
    }

    emit({"type": "step", "source_id": source.id, "step": "fetching"})
    fetch_result = fetch_url(source.url)
    if fetch_result is None:
        result["errors"] += 1
        emit({"type": "error", "source_id": source.id, "message": "Fetch failed"})
        return result

    emit({"type": "step", "source_id": source.id, "step": "extracting"})
    extraction = extract_content(fetch_result.html, url=fetch_result.final_url)

    existing = (
        db.query(Document)
        .filter(Document.content_hash == extraction.content_hash)
        .first()
    )
    if existing:
        result["skipped"] += 1
    else:
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        db.commit()
        result["new_documents"] += 1

        if analyse:
            from app.analyser.pipeline import analyse_document

            db.refresh(doc)
            emit({"type": "step", "source_id": source.id, "step": "analysing"})
            try:
                analyse_document(doc, source.company_id, db)
            except Exception as e:
                result["errors"] += 1
                emit(
                    {
                        "type": "error",
                        "source_id": source.id,
                        "message": f"Analysis failed: {e}",
                    }
                )

    emit({"type": "step", "source_id": source.id, "step": "discovering"})
    result["discovery"] = discover_and_crawl(
        source, fetch_result.html, db, analyse=analyse
    )

    source.last_crawled_at = datetime.now(timezone.utc)
    db.commit()

    return result
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_crawler.py -v
```

Expected: All tests PASS (including the two new ones and all existing ones).

- [ ] **Step 1.5: Commit**

```bash
cd backend && rtk git add app/crawler/pipeline.py tests/test_crawler.py && rtk git commit -m "feat: add progress_callback to run_crawl_source"
```

---

## Task 2: SSE stream endpoints

**Files:**
- Modify: `backend/app/routers/crawl.py`
- Test: `backend/tests/test_crawl_router.py`

- [ ] **Step 2.1: Write failing SSE endpoint tests**

Append to `backend/tests/test_crawl_router.py`:

```python
import json


def test_stream_all_sources_returns_events(client, seed_source):
    def mock_run(source, db, analyse=True, progress_callback=None):
        if progress_callback:
            progress_callback({"type": "step", "source_id": source.id, "step": "fetching"})
            progress_callback({"type": "step", "source_id": source.id, "step": "extracting"})
        return {"source_id": source.id, "new_documents": 1, "skipped": 0, "errors": 0, "discovery": {}}

    with patch("app.routers.crawl.run_crawl_source", side_effect=mock_run):
        response = client.get("/api/crawl/stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert event_types[0] == "crawl_start"
    assert "source_start" in event_types
    assert "step" in event_types
    assert "source_done" in event_types
    assert event_types[-1] == "crawl_done"

    done = next(e for e in events if e["type"] == "crawl_done")
    assert done["sources_processed"] == 1
    assert done["total_new"] == 1


def test_stream_single_source_returns_events(client, seed_source):
    def mock_run(source, db, analyse=True, progress_callback=None):
        if progress_callback:
            progress_callback({"type": "step", "source_id": source.id, "step": "fetching"})
        return {"source_id": source.id, "new_documents": 0, "skipped": 1, "errors": 0, "discovery": {}}

    with patch("app.routers.crawl.run_crawl_source", side_effect=mock_run):
        response = client.get(f"/api/crawl/stream/{seed_source.id}")

    assert response.status_code == 200
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    event_types = [e["type"] for e in events]
    assert "crawl_start" in event_types
    assert "crawl_done" in event_types


def test_stream_nonexistent_source_returns_404(client):
    response = client.get("/api/crawl/stream/nonexistent-id")
    assert response.status_code == 404
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_stream_all_sources_returns_events tests/test_crawl_router.py::test_stream_single_source_returns_events tests/test_crawl_router.py::test_stream_nonexistent_source_returns_404 -v
```

Expected: FAIL with 404 (endpoints don't exist yet).

- [ ] **Step 2.3: Implement SSE endpoints**

Replace `backend/app/routers/crawl.py` entirely with:

```python
import asyncio
import json
import threading
from typing import AsyncGenerator, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.source import Source
from app.crawler.pipeline import run_crawl_source

router = APIRouter()


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


def _run_sources_in_thread(
    source_ids: List[str],
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> None:
    thread_db = SessionLocal()
    try:
        total = len(source_ids)
        loop.call_soon_threadsafe(
            queue.put_nowait, {"type": "crawl_start", "total": total}
        )
        total_new = 0
        total_errors = 0

        for i, source_id in enumerate(source_ids):
            source = thread_db.query(Source).filter(Source.id == source_id).first()
            if not source:
                continue

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_start",
                    "source_id": source.id,
                    "url": source.url,
                    "index": i + 1,
                    "total": total,
                },
            )

            def make_callback(sid: str):
                def callback(event: dict) -> None:
                    loop.call_soon_threadsafe(queue.put_nowait, event)

                return callback

            result = run_crawl_source(
                source,
                thread_db,
                analyse=True,
                progress_callback=make_callback(source.id),
            )
            total_new += result.get("new_documents", 0)
            total_errors += result.get("errors", 0)

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_done",
                    "source_id": source.id,
                    "new_documents": result["new_documents"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
            )

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "crawl_done",
                "sources_processed": total,
                "total_new": total_new,
                "total_errors": total_errors,
            },
        )
    except Exception as e:
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"type": "error", "source_id": None, "message": str(e)},
        )
    finally:
        thread_db.close()
        loop.call_soon_threadsafe(queue.put_nowait, None)


async def _sse_generator(source_ids: List[str]) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    thread = threading.Thread(
        target=_run_sources_in_thread,
        args=(source_ids, loop, queue),
        daemon=True,
    )
    thread.start()

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"


@router.get("/stream")
async def stream_all_sources(db: Session = Depends(get_db)) -> StreamingResponse:
    source_ids = [
        s.id
        for s in db.query(Source).filter(Source.is_active == True).all()  # noqa: E712
    ]
    return StreamingResponse(
        _sse_generator(source_ids),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/stream/{source_id}")
async def stream_single_source(
    source_id: str, db: Session = Depends(get_db)
) -> StreamingResponse:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return StreamingResponse(
        _sse_generator([source.id]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 2.4: Run all crawl router tests**

```bash
cd backend && python -m pytest tests/test_crawl_router.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 2.5: Run full test suite to check for regressions**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 2.6: Commit**

```bash
cd backend && rtk git add app/routers/crawl.py tests/test_crawl_router.py && rtk git commit -m "feat: add SSE stream endpoints for crawl progress"
```

---

## Task 3: Add crawl stream types to frontend

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 3.1: Append crawl stream types**

Append to the end of `frontend/src/types/index.ts`:

```typescript
export type CrawlStep = 'fetching' | 'extracting' | 'analysing' | 'discovering';

export interface CrawlStartEvent {
  type: 'crawl_start';
  total: number;
}
export interface CrawlSourceStartEvent {
  type: 'source_start';
  source_id: string;
  url: string;
  index: number;
  total: number;
}
export interface CrawlStepEvent {
  type: 'step';
  source_id: string;
  step: CrawlStep;
}
export interface CrawlSourceDoneEvent {
  type: 'source_done';
  source_id: string;
  new_documents: number;
  skipped: number;
  errors: number;
}
export interface CrawlDoneEvent {
  type: 'crawl_done';
  sources_processed: number;
  total_new: number;
  total_errors: number;
}
export interface CrawlErrorEvent {
  type: 'error';
  source_id: string | null;
  message: string;
}
export type CrawlEvent =
  | CrawlStartEvent
  | CrawlSourceStartEvent
  | CrawlStepEvent
  | CrawlSourceDoneEvent
  | CrawlDoneEvent
  | CrawlErrorEvent;

export interface SourceCrawlState {
  source_id: string;
  url: string;
  status: 'waiting' | 'running' | 'done' | 'error';
  currentStep?: CrawlStep;
  result?: { new_documents: number; skipped: number; errors: number };
  errorMessage?: string;
}

export interface CrawlStreamSummary {
  sources_processed: number;
  total_new: number;
  total_errors: number;
}
```

- [ ] **Step 3.2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3.3: Commit**

```bash
rtk git add frontend/src/types/index.ts && rtk git commit -m "feat: add crawl stream types"
```

---

## Task 4: Create `useCrawlStream` hook

**Files:**
- Create: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 4.1: Create the hook**

Create `frontend/src/hooks/useCrawlStream.ts`:

```typescript
import { useState, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type {
  CrawlEvent,
  CrawlStreamSummary,
  SourceCrawlState,
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

export function useCrawlStream() {
  const qc = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const [sourceStates, setSourceStates] = useState<SourceCrawlState[]>([]);
  const [summary, setSummary] = useState<CrawlStreamSummary | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback(
    (event: CrawlEvent) => {
      switch (event.type) {
        case 'source_start':
          setSourceStates((prev) => [
            ...prev,
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

  const start = useCallback(
    async (sourceId?: string) => {
      if (isRunning) return;

      abortRef.current = new AbortController();
      setIsRunning(true);
      setSourceStates([]);
      setSummary(null);
      setConnectionError(null);

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
          setIsRunning(false);
          return;
        }

        const reader = res.body!.getReader();
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
        setIsRunning(false);
      }
    },
    [isRunning, handleEvent],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setSourceStates([]);
    setSummary(null);
    setConnectionError(null);
  }, []);

  return { start, cancel, reset, isRunning, sourceStates, summary, connectionError };
}
```

- [ ] **Step 4.2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4.3: Commit**

```bash
rtk git add frontend/src/hooks/useCrawlStream.ts && rtk git commit -m "feat: add useCrawlStream hook"
```

---

## Task 5: Create `CrawlProgressPanel` component

**Files:**
- Create: `frontend/src/components/CrawlProgressPanel.tsx`

- [ ] **Step 5.1: Create the component**

Create `frontend/src/components/CrawlProgressPanel.tsx`:

```tsx
import { X, Check, AlertCircle, Loader2, Minus } from 'lucide-react';
import type { SourceCrawlState, CrawlStreamSummary, CrawlStep } from '../types';

const STEP_LABELS: Record<CrawlStep, string> = {
  fetching: 'Fetching...',
  extracting: 'Extracting...',
  analysing: 'Analysing...',
  discovering: 'Discovering...',
};

function SourceRow({ state }: { state: SourceCrawlState }) {
  let domain: string;
  try {
    domain = new URL(state.url).hostname;
  } catch {
    domain = state.url;
  }

  return (
    <div className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-dark-border/20 last:border-0">
      <span className="w-4 flex-shrink-0 flex items-center justify-center">
        {state.status === 'done' && <Check size={13} className="text-signal-high" />}
        {state.status === 'error' && <AlertCircle size={13} className="text-signal-low" />}
        {state.status === 'running' && (
          <Loader2 size={13} className="text-dark-accent animate-spin" />
        )}
        {state.status === 'waiting' && <Minus size={13} className="text-dark-muted" />}
      </span>
      <span className="flex-1 text-dark-text truncate" title={state.url}>
        {domain}
      </span>
      <span className="text-dark-muted text-xs min-w-0 shrink-0">
        {state.status === 'done' && state.result
          ? `${state.result.new_documents} new · ${state.result.skipped} skipped`
          : state.status === 'error'
            ? (state.errorMessage ?? 'Error')
            : state.status === 'running' && state.currentStep
              ? STEP_LABELS[state.currentStep]
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
  onCancel: () => void;
  onDismiss: () => void;
}

export function CrawlProgressPanel({
  isRunning,
  sourceStates,
  summary,
  connectionError,
  onCancel,
  onDismiss,
}: Props) {
  if (!isRunning && !summary && !connectionError) return null;

  const doneCount = sourceStates.filter(
    (s) => s.status === 'done' || s.status === 'error',
  ).length;
  const total = summary?.sources_processed ?? sourceStates.length;
  const hasErrors = (summary?.total_errors ?? 0) > 0 || connectionError != null;

  const borderColor = hasErrors
    ? 'border-signal-low/40'
    : summary
      ? 'border-signal-high/40'
      : 'border-dark-accent/40';

  const headerText = connectionError
    ? `Connection failed: ${connectionError}`
    : isRunning
      ? `Crawling... (${doneCount}/${total})`
      : hasErrors
        ? `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs, ${summary?.total_errors} errors`
        : `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs`;

  return (
    <div
      className={`mb-6 rounded-lg border ${borderColor} bg-dark-card overflow-hidden`}
    >
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-dark-border/30">
        <span className="text-sm font-medium text-dark-text">{headerText}</span>
        {isRunning ? (
          <button
            onClick={onCancel}
            className="text-xs text-dark-muted hover:text-dark-text px-2 py-0.5 rounded"
          >
            Cancel
          </button>
        ) : (
          <button
            onClick={onDismiss}
            className="text-dark-muted hover:text-dark-text"
            aria-label="Dismiss"
          >
            <X size={16} />
          </button>
        )}
      </div>
      <div>
        {sourceStates.map((s) => (
          <SourceRow key={s.source_id} state={s} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5.2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 5.3: Commit**

```bash
rtk git add frontend/src/components/CrawlProgressPanel.tsx && rtk git commit -m "feat: add CrawlProgressPanel component"
```

---

## Task 6: Integrate into SourcesAdmin

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 6.1: Update imports and replace crawl hooks**

In `frontend/src/pages/SourcesAdmin.tsx`, make these changes:

**Replace the import of `useCrawlAll, useCrawlSource`:**
```typescript
// Remove this line:
import { useCrawlAll, useCrawlSource } from '../hooks/useCrawl';

// Add these two lines instead:
import { useCrawlStream } from '../hooks/useCrawlStream';
import { CrawlProgressPanel } from '../components/CrawlProgressPanel';
```

- [ ] **Step 6.2: Replace hook usage in component body**

Inside the `SourcesAdmin` function body, find and replace:

```typescript
// Remove these two lines:
  const crawlAll = useCrawlAll();
  const crawlSingle = useCrawlSource();
```

```typescript
// Add this line instead:
  const stream = useCrawlStream();
```

- [ ] **Step 6.3: Update handler functions**

Find:
```typescript
  function handleCrawlSource(sourceId: string) {
    crawlSingle.mutate(sourceId);
  }
```

Replace with:
```typescript
  function handleCrawlSource(sourceId: string) {
    stream.start(sourceId);
  }
```

- [ ] **Step 6.4: Update "Run Full Crawl" button**

Find:
```tsx
          <button onClick={() => crawlAll.mutate()} disabled={crawlAll.isPending} className="btn-primary flex items-center gap-2">
            <Play size={16} /> {crawlAll.isPending ? 'Crawling...' : 'Run Full Crawl'}
          </button>
```

Replace with:
```tsx
          <button onClick={() => stream.start()} disabled={stream.isRunning} className="btn-primary flex items-center gap-2">
            <Play size={16} /> {stream.isRunning ? 'Crawling...' : 'Run Full Crawl'}
          </button>
```

- [ ] **Step 6.5: Remove old success banner and add CrawlProgressPanel**

Find and remove:
```tsx
      {crawlAll.isSuccess && (
        <div className="mb-4 p-3 rounded bg-signal-high/10 text-signal-high text-sm">
          Crawl complete: {crawlAll.data.sources_processed} sources processed
        </div>
      )}
```

Replace with:
```tsx
      <CrawlProgressPanel
        isRunning={stream.isRunning}
        sourceStates={stream.sourceStates}
        summary={stream.summary}
        connectionError={stream.connectionError}
        onCancel={stream.cancel}
        onDismiss={stream.reset}
      />
```

- [ ] **Step 6.6: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 6.7: Start dev stack and manually test**

```bash
docker compose -f docker-compose.dev.yml up -d
```

Open the Sources Admin page. Click "Run Full Crawl" — the panel should appear with live per-step updates. Click a per-source Play button — same panel with one row. After completion, verify summary counts are shown and the × dismisses the panel.

- [ ] **Step 6.8: Commit**

```bash
rtk git add frontend/src/pages/SourcesAdmin.tsx && rtk git commit -m "feat: integrate crawl progress panel into SourcesAdmin"
```
