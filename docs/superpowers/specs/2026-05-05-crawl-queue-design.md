# Crawl Queue Design

**Date:** 2026-05-05
**Status:** Approved

## Summary

When a crawl is already running and the user clicks "Crawl" on additional sources, those sources are added to a persistent queued `CrawlRun` instead of being silently ignored. Once the active run completes, the **frontend** opens a new SSE stream for the queued run via a dedicated endpoint. The frontend shows both the active run and the pending queue, and the queue survives page reload.

---

## Data Model

`CrawlRunStatus` gets a new value: `queued`.

```python
class CrawlRunStatus(str, enum.Enum):
    running = "running"
    queued = "queued"      # new
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
```

At any point there is at most **one** queued `CrawlRun`. If a second source is enqueued while a queued run already exists, the source is appended to it as a new `CrawlRunSource` rather than creating another `CrawlRun`.

No new DB columns are needed beyond the enum change (Alembic migration required).

---

## Backend Changes

### New endpoint: `POST /api/crawl/enqueue/{source_id}`

Called when the user clicks "Crawl" on a source and a run is already active.

- Finds or creates a `queued` `CrawlRun`
- Appends the source as a `CrawlRunSource` with status `pending`
- Returns `{"queued": true, "position": N}` (HTTP 202) where `N` is the total number of sources now in the queued run
- If the source is already in the queued run, returns current position (no-op)
- Does **not** open an SSE stream

### New endpoint: `GET /api/crawl/stream/queued`

Starts the queued run as a full SSE stream, identical to `_sse_generator` but for an existing queued `CrawlRun`:

- Finds the queued run; returns 404 if none exists
- Marks the run as `running`, updates `started_at`
- Runs `_sse_generator` with the queued run's source IDs
- This is called by the **frontend** after the previous run completes, not by the backend

### Modified: `GET /api/crawl/reconnect`

Returns up to two events:

1. `initial_state` (existing) — for the running run, if one exists
2. `queued_state` (new) — for the queued run, if one exists

```json
{
  "type": "queued_state",
  "crawl_run_id": "...",
  "sources": [
    { "source_id": "...", "url": "..." }
  ]
}
```

If no running run exists but a queued run does, the endpoint sends only `queued_state` (no `initial_state`, no `no_active_run`).

### `_run_sources_in_thread`: no change needed

The backend does **not** auto-start the queued run. The frontend is responsible for initiating the next SSE stream. This keeps the SSE lifecycle fully client-initiated and avoids orphaned background threads with no consumer.

---

## Frontend Changes

### `useCrawlStream` hook

New state:
```ts
const [queuedSources, setQueuedSources] = useState<{ source_id: string; url: string }[]>([]);
const queuedRunIdRef = useRef<string | null>(null);
```

**`start(sourceId?)`** logic:
- If `isRunningRef.current === false`: open SSE stream as before
- If `isRunningRef.current === true`: call `POST /api/crawl/enqueue/{source_id}`, update `queuedSources` from response

**`crawl_done` handler** (addition):
- After the existing cache invalidations and `setIsRunning(false)`, check `queuedRunIdRef.current`
- If a queued run exists: after 300ms, open a new SSE stream to `GET /api/crawl/stream/queued`
- Process events from this stream exactly as the current stream (same `handleEvent`)
- `queuedSources` is cleared and `queuedRunIdRef` reset when the new `crawl_start` event fires

**`queued_state` event handler** (new):
```ts
case 'queued_state':
  setQueuedSources(event.sources);
  queuedRunIdRef.current = event.crawl_run_id;
  break;
```

**Reconnect `useEffect`** (addition):
- After reconnect completes, if `queuedRunIdRef.current` is set but `isRunning === false`, auto-call `GET /api/crawl/stream/queued`
- This handles the case where the user reloads after a run completes but before the queued run has started

### `CrawlProgressPanel` component

Gets a new optional prop:
```ts
queuedSources?: { source_id: string; url: string }[]
```

When `queuedSources` is non-empty, a second section is rendered below the active sources list:

```
┌─────────────────────────────────────────────┐
│ Crawling... (1/2)                    Cancel │
│  ✓ competitor.com/blog    fetch 1.2s        │
│  ⟳ competitor.com/jobs    Analysing...      │
├─────────────────────────────────────────────┤
│ Queued (startet danach)                     │
│  – startup.io/news                          │
│  – startup.io/blog                          │
└─────────────────────────────────────────────┘
```

The header `(1/2)` counts runs: current run number / total runs (active + queued).

### `SourcesAdmin` page

`handleCrawlSource(sourceId)` passes through to `stream.start(sourceId)` unchanged.

---

## Sequence: User queues a source mid-crawl (no reload)

```
User clicks "Crawl startup.io" while competitor.com is running
  → Frontend: isRunning === true
  → Frontend: POST /api/crawl/enqueue/startup-io-source-id
  → Backend: finds/creates queued CrawlRun, appends CrawlRunSource
  → Backend: returns { queued: true, position: 1 }
  → Frontend: sets queuedSources = [startup.io], queuedRunIdRef = run_id
  → Panel: shows "Queued" section with startup.io, header "Crawling... (1/2)"

competitor.com run finishes
  → Backend: crawl_done emitted, run marked completed
  → Frontend: receives crawl_done, cache invalidated, isRunning = false
  → Frontend: queuedRunIdRef is set → after 300ms opens GET /api/crawl/stream/queued
  → Backend: marks queued run as running, starts _sse_generator
  → Frontend: receives crawl_start → clears queuedSources, starts new run
  → Panel: transitions to new run, Queued section disappears, header "Crawling... (2/2)"
```

---

## Sequence: User reloads while a run is active and a queue exists

```
User reloads while competitor.com is running and startup.io is queued
  → useCrawlStream useEffect fires: GET /api/crawl/reconnect
  → Backend: sends initial_state (running run) + queued_state (queued run)
  → Frontend: sourceStates ← initial_state, isRunning = true
  → Frontend: queuedSources ← queued_state, queuedRunIdRef set
  → Panel: active run + queued section both visible
```

## Sequence: User reloads after active run finished but before queue started

```
User reloads (crawl_done already happened, no frontend present to start the queue)
  → useCrawlStream useEffect fires: GET /api/crawl/reconnect
  → Backend: no running run → sends only queued_state
  → Frontend: isRunning stays false, queuedSources set, queuedRunIdRef set
  → useEffect detects: queuedRunIdRef set + isRunning false
  → Frontend: opens GET /api/crawl/stream/queued
  → Panel: starts showing queued run as active
```

---

## Error Handling

- If `GET /api/crawl/stream/queued` is called and no queued run exists → 404, frontend clears `queuedRunIdRef`
- Enqueue of a source already in the queued run → no-op, returns current position
- Cancelling the active run does not cancel the queued run; it will auto-start when the frontend detects `queuedRunIdRef` set and `isRunning` false
- If the queued run itself fails, it follows the existing error flow (run marked `failed`, `crawl_done` with errors emitted)

---

## Out of Scope

- Multiple stacked queued runs (max 1 queued run at a time)
- Cancel queue button
- Full Crawl (`/stream`) queueing when a run is active
