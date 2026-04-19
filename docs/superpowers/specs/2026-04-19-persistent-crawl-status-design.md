# Persistent Crawl Status Design

## Problem

When a crawl is running, the SSE-based progress panel in SourcesAdmin shows real-time status. On page refresh or navigation away, the SSE connection drops and all progress is lost. Since crawls can take a long time, users need to see the status after refreshing.

## Approach

**CrawlRun model + SSE reconnect.** New database models persist crawl progress server-side. When a client reconnects to the SSE stream, it first receives the accumulated state, then live events.

## Data Model

### `crawl_runs` table

| Column         | Type                          | Notes                  |
|----------------|-------------------------------|------------------------|
| id             | UUID (PK)                     |                        |
| status         | Enum: running, completed, failed, cancelled |          |
| started_at     | datetime                      |                        |
| finished_at    | datetime (nullable)           |                        |
| total_sources  | int                           |                        |
| total_new      | int, default 0               |                        |
| total_skipped  | int, default 0               |                        |
| total_errors   | int, default 0               |                        |

### `crawl_run_sources` table (1:N from crawl_runs)

| Column         | Type                                                    | Notes         |
|----------------|---------------------------------------------------------|----------------|
| id             | UUID (PK)                                               |                |
| crawl_run_id   | UUID (FK -> crawl_runs.id)                              |                |
| source_id      | UUID (FK -> sources.id)                                 |                |
| url            | string                                                  |                |
| status         | Enum: pending, running, completed, failed, skipped      |                |
| current_step   | Enum: fetching, extracting, analysing, discovering (nullable) |     |
| new_documents  | int, default 0                                          |                |
| skipped        | int, default 0                                          |                |
| errors         | int, default 0                                          |                |
| error_message  | string (nullable)                                       |                |
| started_at     | datetime (nullable)                                     |                |
| finished_at    | datetime (nullable)                                     |                |

## SSE Reconnect & State Replay

### Backend

On `GET /api/crawl/stream` or `GET /api/crawl/stream/{source_id}`:

1. If a CrawlRun with `status=running` exists, send an `initial_state` event containing all accumulated CrawlRunSource entries
2. Then attach the client to the live SSE stream for ongoing events

### Event format

All events now include `crawl_run_id`:

```
event: initial_state
data: { crawl_run_id, sources: [{ source_id, url, status, current_step, new_documents, ... }], ... }

event: source_start
data: { crawl_run_id, source_id, url, index, total }

event: step
data: { crawl_run_id, source_id, step }

event: source_done
data: { crawl_run_id, source_id, new_documents, skipped, errors }

event: crawl_done
data: { crawl_run_id, total_new, total_skipped, total_errors }
```

### New REST endpoints

- `GET /api/crawl/runs` — List all CrawlRuns (filterable by status)
- `GET /api/crawl/runs/{id}` — CrawlRun details including CrawlRunSources

## Pipeline Changes

The crawl pipeline (`pipeline.py`) and SSE endpoint must update `CrawlRunSource` rows in the database at each step:
- `source_start` -> set status=running, started_at
- `step` events -> update current_step
- `source_done` -> set status=completed, finished_at, new_documents, skipped, errors
- `crawl_done` -> set CrawlRun status=completed, finished_at, totals

## Frontend: SourcesAdmin

### `useCrawlStream` hook changes

- On crawl start: store `crawl_run_id` from first event
- On page load/refresh: call `GET /api/crawl/runs?status=running`
  - If a running run exists: reconnect SSE, receive `initial_state`, rebuild CrawlProgressPanel state
- `CrawlProgressPanel` stays visible after crawl completion until user dismisses it

### `CrawlProgressPanel` changes

- Show run status at top: "Crawl laeuft..." or "Crawl abgeschlossen"
- Associated with a specific `crawl_run_id`

## Frontend: Dashboard

### New hook: `useActiveCrawlRun()`

- Polls `GET /api/crawl/runs?status=running` every 5 seconds via React Query with `refetchInterval`
- If an active run is found: show banner "Crawl laeuft — X von Y Sources verarbeitet" with link to `/admin/sources`
- After completion: show "Crawl abgeschlossen — N neue Dokumente" until dismissed or next crawl starts

## CrawlRun Cleanup

- When starting a new crawl for the same scope: cancel any existing `running` CrawlRun (set status=cancelled)
- No automatic cleanup of old runs (YAGNI for now — can be added later)

## Out of Scope

- Per-source crawl history page
- Automatic old-run cleanup cron
- WebSocket (SSE is sufficient)
- Dashboard sync crawl migration (keep as-is, separate concern)