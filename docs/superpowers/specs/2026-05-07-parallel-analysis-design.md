# Parallel Analysis Phase — Design Spec

**Date:** 2026-05-07  
**Status:** Approved

## Problem

The analysis phase processes documents sequentially (one LLM call at a time). With 50+ documents per crawl and 3–5s per LLM call, analysis takes 3–8 minutes. The bottleneck is the LLM call — all three providers (Anthropic, OpenCode, Ollama) are blocking HTTP calls that can run concurrently without conflict.

## Approach

ThreadPoolExecutor with per-thread DB sessions. Each worker thread owns its own SQLAlchemy Session, runs the LLM call independently, and commits results without sharing state. The main thread coordinates progress events via an atomic counter.

Chosen over async rewrite (too invasive, SQLAlchemy is sync) and batch-based parallelism (uneven batch completion wastes time).

## Changes

### 1. Config (`backend/app/config.py`)

Add `analysis_concurrency: int = 3` — independent from `discovery_concurrency` (3) and `crawl_concurrency` (4). Default 3 is appropriate for Anthropic/OpenCode rate limits.

### 2. LLM Client Singletons (`backend/app/analyser/client.py`)

Replace per-call client instantiation with module-level singletons for Anthropic and OpenCode clients. Both SDKs are thread-safe. Ollama uses stateless `httpx.post` — no change needed.

```python
_anthropic_client = None

def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=120.0)
    return _anthropic_client
```

### 3. Worker Function (`backend/app/crawler/pipeline.py`)

New `_analyse_doc_worker(doc_id, company_id, context)` function:
- Opens its own `SessionLocal()` session
- Loads document by ID
- Calls `analyse_document(doc, company_id, db, preloaded_context=context)`
- Closes session in `finally` block
- Returns `(doc_id, success: bool)`

### 4. Context Pre-loading (`backend/app/analyser/pipeline.py`)

Extract context-building logic from `analyse_document` into a helper `_build_context_dict(ctx_record)`. Add optional `preloaded_context: dict | None = None` parameter to `analyse_document` — if provided, skips the DB query for `InternalCompanyContext`. If `None`, falls back to the existing DB query (backwards compatible for direct callers e.g. tests). This saves N identical DB queries (one per document) in the parallel path.

### 5. Parallel Loop (`backend/app/crawler/pipeline.py` — `analyse_unanalysed_for_source`)

Replace sequential `for` loop with `ThreadPoolExecutor`:

```python
completed_count = 0
lock = threading.Lock()

context = _build_context_dict(db.query(InternalCompanyContext).first())

with ThreadPoolExecutor(max_workers=settings.analysis_concurrency) as executor:
    futures = {
        executor.submit(_analyse_doc_worker, doc.id, source.company_id, context): doc
        for doc in unanalysed
    }
    for future in as_completed(futures):
        doc_id, success = future.result()
        with lock:
            completed_count += 1
            current = completed_count
        if not success:
            result["errors"] += 1
        else:
            result["analysed"] += 1
        emit({"type": "analysis_progress", "source_id": source.id,
              "current": current, "total": total, "url": ""})
```

`DiscoveredPage` status updates run after the pool completes in the main thread (no concurrent DB access).

### 6. Frontend (`frontend/src/`)

Remove `currentUrl` from:
- `types/index.ts` — `AnalysisProgressEvent` and `SourceCrawlState.analysisProgress`
- `hooks/useCrawlStream.ts` — `analysis_progress` handler

The label `"Analysing X/Y Dokumente"` in `CrawlProgressPanel.tsx` is unaffected. No visible UI change.

## Data Flow

```
analyse_unanalysed_for_source (main thread)
  │
  ├─ Load InternalCompanyContext once → context dict
  ├─ Load all unanalysed docs for source
  │
  └─ ThreadPoolExecutor (analysis_concurrency workers)
       ├─ Thread 1: _analyse_doc_worker(doc_1) → own Session → LLM → commit
       ├─ Thread 2: _analyse_doc_worker(doc_2) → own Session → LLM → commit
       └─ Thread N: ...
  │
  ├─ as_completed → emit analysis_progress (atomic counter)
  └─ Post-pool: DiscoveredPage status updates (main thread, original session)
```

## Error Handling

- Worker catches all exceptions, returns `(doc_id, False)` — never raises
- Main thread tallies errors from return values
- `db.rollback()` in worker's except block prevents partial writes
- Source `analysis_status` set to `analysis_failed` if any errors, same as before

## Testing

- Existing tests in `tests/test_crawl_router.py` cover the analysis flow — verify they still pass
- Add unit test for `_analyse_doc_worker` with a mocked `analyse_document`
- Add test verifying parallel execution (mock LLM to sleep, assert wall time < sequential time)

## Expected Impact

| Scenario | Before | After (concurrency=3) |
|----------|--------|-----------------------|
| 50 docs, 4s/LLM | ~200s | ~70s |
| 20 docs, 5s/LLM | ~100s | ~35s |
| Rate-limited (1 req/s) | 50s | 50s (unchanged — rate limits dominate) |
