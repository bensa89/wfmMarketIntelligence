# Crawl Progress & Performance Design

## Problem

- Crawling feels slow with no visibility into what's happening
- Source status shows only "Discovering" — no page counts, timing, or progress
- No way to identify which pipeline step is the bottleneck
- Sources are crawled sequentially, wasting time

## Approach: Incremental — Progressive SSE + Timing DB + Parallelization

### 1. Granular SSE Events

New event types emitted during crawl streaming:

| Event | Payload | When |
|---|---|---|
| `discovery_progress` | `{source_id, pages_found, pages_crawled, max_pages, current_url}` | After each page crawled in `discover_and_crawl()` |
| `step_timing` | `{source_id, step, duration_ms}` | After each step completes (fetch/extract/analyse/discover) |

Existing events (`step`, `source_done`, `crawl_done`, `error`) remain unchanged.

Implementation in `discovery.py`: pass `progress_callback` through. After each page, emit `discovery_progress` event. In `pipeline.py`, measure each step with `time.monotonic()` and emit `step_timing` after completion.

### 2. Timing Fields in `CrawlRunSource`

New columns on `CrawlRunSource`:

| Field | Type | Description |
|---|---|---|
| `fetch_ms` | Integer, nullable | Duration of fetch step in ms |
| `extract_ms` | Integer, nullable | Duration of extract step in ms |
| `analyse_ms` | Integer, nullable | Duration of analyse step in ms |
| `discover_ms` | Integer, nullable | Duration of discover step in ms |

- `CrawlRunSourceRead` schema extended with these 4 optional fields
- No new API endpoint — existing `GET /api/crawl-runs/{id}` includes source timings
- Alembic migration required

### 3. Parallel Source Crawling

**Source-level parallelism:** Use `concurrent.futures.ThreadPoolExecutor` in `_run_sources_in_thread()` with configurable `max_workers` (default 4). Each worker calls `run_crawl_source()`. SSE events continue through the existing `asyncio.Queue` via `loop.call_soon_threadsafe`.

**Discovery-level parallelism:** Within `discover_and_crawl()`, use `threading.Semaphore` (default 3) to parallelize HTTP fetches while keeping dedup+analysis sequential. Rate-limiting via semaphore, not `time.sleep(1)`.

New config fields in `config.py`:
- `crawl_concurrency`: int = 4 (parallel sources)
- `discovery_concurrency`: int = 3 (parallel page fetches within discovery)

### 4. Frontend Improvements

**CrawlProgressPanel:**
- During `discovering` step: show `X/Y Seiten` from `discovery_progress` events
- For every step: show elapsed time `12s · Fetching...`
- After completion: show step timings per source `Fetch 1.2s · Extract 0.3s · Analyse 8.1s · Discover 45s`

**New CrawlRunDetail route (`/crawl-runs/:id`):**
- Per-source: status, step timings as proportional bar chart, new/skipped documents, errors
- Visual identification of slowest steps

**Source detail page extension:**
- "Letzte Crawl-Timings" section showing timing data from last `CrawlRunSource`
- Average over last N runs as trend

**useCrawlStream hook extension:**
- New state field `discoveryProgress: {pages_found, pages_crawled, max_pages}`
- New state field `stepTimings: {[source_id]: {fetch_ms, extract_ms, analyse_ms, discover_ms}}`

## Files to Modify

### Backend
- `backend/app/models/crawl_run.py` — add 4 timing columns
- `backend/app/schemas/crawl_run.py` — add timing fields to `CrawlRunSourceRead`
- `backend/app/crawler/pipeline.py` — timing measurement, emit `step_timing` events
- `backend/app/crawler/discovery.py` — emit `discovery_progress` events, semaphore-based fetch parallelism
- `backend/app/routers/crawl.py` — `ThreadPoolExecutor` for source-level parallelism, new SSE event types
- `backend/app/config.py` — `crawl_concurrency`, `discovery_concurrency` settings
- `backend/alembic/` — migration for new columns

### Frontend
- `frontend/src/types/index.ts` — new SSE event types, timing types
- `frontend/src/hooks/useCrawlStream.ts` — handle `discovery_progress` and `step_timing` events
- `frontend/src/components/CrawlProgressPanel.tsx` — progress bars, timing display
- `frontend/src/pages/CrawlRunDetail.tsx` — new page (route + component)
- `frontend/src/pages/SourcesAdmin.tsx` — source detail timing section