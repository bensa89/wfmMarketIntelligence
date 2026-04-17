# Crawl Progress & Status — Design Spec

## Overview

Live crawl progress via Server-Sent Events (SSE), with a per-step status panel in the Sources Admin UI. After completion, a summary report replaces the live view.

## Scope

- Full crawl (`/api/crawl/stream`) and single-source crawl (`/api/crawl/stream/{source_id}`)
- Step-level granularity: fetching → extracting → analysing → discovering
- Live panel in `SourcesAdmin`, same UI for both full and single crawl
- Existing POST endpoints (`/api/crawl/run`, `/api/crawl/run/{source_id}`) remain unchanged

---

## Backend

### New Endpoints

```
GET /api/crawl/stream              — stream all active sources
GET /api/crawl/stream/{source_id}  — stream single source
```

Both return `Content-Type: text/event-stream`. Each event is a single line:
```
data: {"type": "...", ...}\n\n
```

### Event Schema

| type | fields |
|---|---|
| `crawl_start` | `total: int` |
| `source_start` | `source_id`, `url`, `index`, `total` |
| `step` | `source_id`, `step: "fetching" \| "extracting" \| "analysing" \| "discovering"` |
| `source_done` | `source_id`, `new_documents`, `skipped`, `errors` |
| `crawl_done` | `sources_processed`, `total_new`, `total_errors` |
| `error` | `source_id`, `message` |

### Pipeline Changes

`run_crawl_source` gets an optional `progress_callback: Callable[[dict], None] | None = None` parameter. Existing callers pass nothing — behavior unchanged. The SSE endpoint passes a callback that yields events into the generator.

Steps where the callback fires:
1. Before `fetch_url` → `step: fetching`
2. Before `extract_content` → `step: extracting`
3. Before `analyse_document` → `step: analysing`
4. Before `discover_and_crawl` → `step: discovering`
5. After all → `source_done` with result counts

The SSE endpoint uses a `Generator[str, None, None]` wrapped in FastAPI's `StreamingResponse`. A thread-safe queue bridges the synchronous pipeline and the async generator.

### DB Session

The synchronous pipeline runs in a `run_in_executor` thread to avoid blocking the async event loop. A fresh `SessionLocal()` is created inside the thread (not shared across threads).

---

## Frontend

### Hook: `useCrawlStream`

```ts
useCrawlStream(): {
  start: (sourceId?: string) => void
  cancel: () => void
  isRunning: boolean
  events: CrawlEvent[]
  summary: CrawlSummary | null
}
```

- Opens via `fetch` + `ReadableStream` (not `EventSource` — needs Basic Auth header)
- Reads the stream line by line, parses `data: {...}` lines as JSON
- Appends to `events[]` as they arrive
- On `crawl_done`: sets `summary`, sets `isRunning = false`
- `cancel()` aborts the fetch via `AbortController`

### Component: `CrawlProgressPanel`

Appears below the toolbar buttons in `SourcesAdmin` while `isRunning || summary !== null`.

**During crawl:**
```
┌─────────────────────────────────────────────────────┐
│ Crawling... (3/8)                          [Cancel] │
├─────────────────────────────────────────────────────┤
│ ✓  example.com/blog        3 new · 1 skipped        │
│ ✓  competitor.io/news      0 new · 5 skipped        │
│ ⟳  example2.com/press      Analysing...             │
│ ·  othersource.com         Waiting...               │
└─────────────────────────────────────────────────────┘
```

**After completion:**
```
┌─────────────────────────────────────────────────────┐
│ ✓ Crawl complete — 8 sources, 12 new docs, 2 errors │ [×]
│ ✓  example.com/blog        3 new · 1 skipped        │
│ ✗  broken.com              Fetch failed             │
│ ...                                                 │
└─────────────────────────────────────────────────────┘
```

Panel is green-bordered on success, red-bordered if any errors. Dismissed with ×.

### SourcesAdmin Changes

- "Run Full Crawl" button calls `stream.start()` instead of `crawlAll.mutate()`
- Per-source Play button calls `stream.start(source.id)`
- `CrawlProgressPanel` rendered between toolbar and company list
- Existing `crawlAll.isSuccess` banner removed (replaced by panel)

---

## Error Handling

- Fetch error (network down, 401): stream errors immediately, panel shows "Connection failed"
- Per-source errors: emitted as `error` event, counted in `source_done.errors`
- LLM errors during analysis: caught in pipeline, emitted as `error` event, crawl continues
- Stream aborted by user: `AbortController.abort()`, panel resets to idle

---

## Testing

- Backend: unit test `run_crawl_source` with a mock callback — verify all steps fire
- Backend: integration test SSE endpoint — verify event sequence for a known source
- Frontend: no new tests required (existing hook tests pattern covers useCrawlStream if tests exist)
