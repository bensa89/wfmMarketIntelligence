# Decouple Analysis from Crawl Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple LLM analysis from the crawl/discovery loop so discovery completes in ~1-2 minutes instead of 15-30 minutes, and show analysis progress as a separate phase in the UI.

**Architecture:** Split the current inline `analyse=True` flow into two phases: (1) Crawl+Discovery saves documents with `is_analysed=False`, (2) A post-crawl analysis loop processes all unanalysed documents sequentially. The CrawlRunSource model gets a new `analysing` status and an `analyse_ms` timing that is recorded after the analysis phase. SSE events are extended with `analysis_start` / `analysis_done` events so the frontend can show a separate "Analysing..." step after discovery completes. The Source list in SourcesAdmin shows a per-source analysis status badge.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync), SSE (existing), React 18 + TypeScript, TanStack Query

---

## File Structure

### Backend — Modified
- `backend/app/crawler/pipeline.py` — Remove inline `analyse_document` calls; add `analyse_unanalysed_documents()` function
- `backend/app/crawler/discovery.py` — Remove `_save_and_analyse()` inline analysis; just save documents
- `backend/app/routers/crawl.py` — After crawl+discovery thread finishes, run analysis phase; emit new SSE events
- `backend/app/models/crawl_run.py` — Add `CrawlRunSourceStatus.analysing` enum value; add `analyse_started_at`, `analyse_finished_at` columns to `CrawlRunSource`
- `backend/app/schemas/crawl_run.py` — Add new fields to `CrawlRunSourceRead`
- `backend/app/models/source.py` — Add `analysis_status` column to Source (nullable enum: `pending` | `analysing` | `analysed` | `analysis_failed`)

### Backend — New
- `backend/app/alembic/versions/XXXX_add_analysis_phase_fields.py` — Migration for new columns

### Frontend — Modified
- `frontend/src/types/index.ts` — Add `CrawlStep.analysing` already exists; add `analysis_status` to Source type; add new SSE event types
- `frontend/src/hooks/useCrawlStream.ts` — Handle `analysis_start` / `analysis_progress` / `analysis_done` SSE events
- `frontend/src/components/CrawlProgressPanel.tsx` — Show analysis as separate phase after discovery
- `frontend/src/pages/SourcesAdmin.tsx` — Show analysis status badge per source in the table
- `frontend/src/hooks/useSources.ts` — Include `analysis_status` in source data

---

### Task 1: Add analysis phase fields to DB models

**Files:**
- Modify: `backend/app/models/crawl_run.py`
- Modify: `backend/app/models/source.py`
- Modify: `backend/app/schemas/crawl_run.py`

- [ ] **Step 1: Add `analysing` to `CrawlRunSourceStatus` enum and new columns to `CrawlRunSource`**

In `backend/app/models/crawl_run.py`, update the enum:

```python
class CrawlRunSourceStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    analysing = "analysing"
    failed = "failed"
    skipped = "skipped"
```

Add columns to `CrawlRunSource`:

```python
    analyse_started_at = Column(DateTime, nullable=True)
    analyse_finished_at = Column(DateTime, nullable=True)
```

In `backend/app/models/source.py`, add a new enum and column:

```python
class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    analysing = "analysing"
    analysed = "analysed"
    analysis_failed = "analysis_failed"

# Inside Source class:
    analysis_status = Column(
        SAEnum(AnalysisStatus), nullable=True, default=None
    )
```

- [ ] **Step 2: Update `CrawlRunSourceRead` schema**

In `backend/app/schemas/crawl_run.py`, add fields:

```python
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
    analyse_started_at: Optional[datetime] = None
    analyse_finished_at: Optional[datetime] = None
```

Update the Source schema (find `SourceRead` or equivalent in `backend/app/schemas/`):

```python
    analysis_status: Optional[str] = None
```

- [ ] **Step 3: Create Alembic migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "add analysis phase fields"
```

Then review the generated migration and run:
```bash
cd backend && alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/ backend/app/schemas/ backend/alembic/
git commit -m "feat: add analysis phase fields to CrawlRunSource and Source models"
```

---

### Task 2: Remove inline analysis from crawl pipeline

**Files:**
- Modify: `backend/app/crawler/pipeline.py`
- Modify: `backend/app/crawler/discovery.py`

- [ ] **Step 1: Remove `analyse` parameter usage in `run_crawl_source`**

In `backend/app/crawler/pipeline.py`, change `run_crawl_source` to always skip inline analysis. Remove the `analyse` parameter default or ignore it for the analysis part. The function should:

1. Still accept `analyse` param for backward compatibility but not use it for analysis
2. When a new document is saved, set `is_analysed = False` (already default)
3. Set `source.analysis_status = AnalysisStatus.pending` when new docs are found
4. Do NOT call `analyse_document()` inline

Specifically in `run_crawl_source`, remove the two blocks that call `analyse_document` (one for existing changed docs, one for new docs). Replace with:

```python
# After saving a new or changed document, just set analysis_status
source.analysis_status = AnalysisStatus.pending
db.commit()
```

Remove the `analyse_ms` timing from the crawl phase — it will be recorded later during the analysis phase. Keep `fetch_ms`, `extract_ms`, `discover_ms` as-is.

- [ ] **Step 2: Remove `_save_and_analyse` from discovery.py and replace with save-only**

In `backend/app/crawler/discovery.py`, replace `_save_and_analyse` with `_save_document_only` that does the same document saving but WITHOUT calling `analyse_document` or `_update_page_relevance`:

```python
def _save_document_only(source, fetch_result, extraction, now, db):
    existing_doc = (
        db.query(Document).filter(Document.url == fetch_result.final_url).first()
    )
    if existing_doc:
        existing_doc.content_markdown = extraction.markdown
        existing_doc.content_hash = extraction.content_hash
        existing_doc.content_raw_html = fetch_result.html.replace("\x00", "")
        existing_doc.crawled_at = now
        existing_doc.is_analysed = False
        if extraction.published_at and not existing_doc.published_at:
            existing_doc.published_at = extraction.published_at
        db.commit()
    else:
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=now,
            published_at=extraction.published_at,
        )
        db.add(doc)
        db.commit()
```

In `discover_and_crawl`, replace all calls to `_save_and_analyse(...)` with `_save_document_only(...)`. Remove `_update_page_relevance` calls from the discovery loop (relevance update will happen after analysis).

- [ ] **Step 3: Run existing tests to verify crawl still works without inline analysis**

Run: `cd backend && python -m pytest tests/ -v -k "crawl or pipeline or discovery"`

The tests may need updates since they expect analysis inline. For now, just verify the crawl part works (fetch, extract, save document, dedup). If tests fail because they assert on `is_analysed=True` or signals existing after crawl, we'll fix those in Task 4.

- [ ] **Step 4: Commit**

```bash
git add backend/app/crawler/pipeline.py backend/app/crawler/discovery.py
git commit -m "feat: remove inline analysis from crawl and discovery pipeline"
```

---

### Task 3: Add post-crawl analysis phase

**Files:**
- Modify: `backend/app/crawler/pipeline.py` — Add `analyse_unanalysed_for_source()` function
- Modify: `backend/app/routers/crawl.py` — Run analysis phase after crawl thread completes

- [ ] **Step 1: Add `analyse_unanalysed_for_source` function to pipeline.py**

In `backend/app/crawler/pipeline.py`, add a new function:

```python
def analyse_unanalysed_for_source(
    source: Source,
    db: Session,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> Dict:
    from app.analyser.pipeline import analyse_document
    from app.assessor.pipeline import assess_signal
    from app.models.document import Document
    from app.models.signal import Signal
    from app.models.source import AnalysisStatus
    from app.crawler.discovery import _update_page_relevance
    from app.models.discovered_page import DiscoveredPage

    def emit(event: dict):
        if progress_callback:
            progress_callback(event)

    result = {"source_id": source.id, "analysed": 0, "errors": 0, "analyse_ms": 0}

    source.analysis_status = AnalysisStatus.analysing
    db.commit()

    unanalysed = (
        db.query(Document)
        .filter(
            Document.source_id == source.id,
            Document.is_analysed == False,
        )
        .order_by(Document.crawled_at.asc())
        .all()
    )

    if not unanalysed:
        source.analysis_status = AnalysisStatus.analysed
        db.commit()
        return result

    total = len(unanalysed)
    t0 = time.monotonic()

    for i, doc in enumerate(unanalysed):
        emit({
            "type": "analysis_progress",
            "source_id": source.id,
            "current": i + 1,
            "total": total,
            "url": doc.url,
        })
        try:
            analyse_document(doc, source.company_id, db)
            result["analysed"] += 1

            page = db.query(DiscoveredPage).filter(DiscoveredPage.url == doc.url).first()
            if page:
                _update_page_relevance(page, doc.url, db)
        except Exception as e:
            result["errors"] += 1
            logger.exception("Analysis failed for doc %s: %s", doc.id, e)
            db.rollback()

    result["analyse_ms"] = int((time.monotonic() - t0) * 1000)

    source.analysis_status = AnalysisStatus.analysed if result["errors"] == 0 else AnalysisStatus.analysis_failed
    db.commit()

    return result
```

- [ ] **Step 2: Integrate analysis phase into crawl router**

In `backend/app/routers/crawl.py`, after the crawl+discovery thread finishes (`_run_sources_in_thread`), add a second phase in the same thread that analyses documents.

Modify `_run_sources_in_thread` to add the analysis phase after the crawl loop. After `crawl_run.status = CrawlRunStatus.completed` and briefing generation, add:

```python
        # --- Analysis Phase ---
        if total_new > 0:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "analysis_phase_start", "crawl_run_id": crawl_run_id},
            )
            for crs in crawl_run.sources:
                if crs.status != CrawlRunSourceStatus.completed or crs.new_documents <= 0:
                    continue
                crs.status = CrawlRunSourceStatus.analysing
                crs.analyse_started_at = datetime.now(timezone.utc)
                thread_db.commit()

                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "analysis_start",
                        "crawl_run_id": crawl_run_id,
                        "source_id": crs.source_id,
                        "url": crs.url,
                    },
                )

                source = thread_db.query(Source).filter(Source.id == crs.source_id).first()
                if source:
                    analysis_result = analyse_unanalysed_for_source(source, thread_db)

                crs.analyse_ms = analysis_result.get("analyse_ms", 0) if source else 0
                crs.analyse_finished_at = datetime.now(timezone.utc)
                crs.status = CrawlRunSourceStatus.completed
                thread_db.commit()

                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "analysis_done",
                        "crawl_run_id": crawl_run_id,
                        "source_id": crs.source_id,
                        "url": crs.url,
                        "analysed": analysis_result.get("analysed", 0) if source else 0,
                        "analyse_ms": crs.analyse_ms,
                    },
                )

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "analysis_phase_done", "crawl_run_id": crawl_run_id},
            )
```

Add the import at top:
```python
from app.crawler.pipeline import analyse_unanalysed_for_source
```

- [ ] **Step 3: Also update the non-SSE crawl endpoint (`POST /run`) to run analysis after crawl**

In the `crawl_all_sources` and `crawl_single_source` endpoints in `crawl.py`, after running `run_crawl_source`, also run `analyse_unanalysed_for_source` for each source that had new docs. These are the synchronous fallback endpoints.

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -v`

Fix any test failures related to the new analysis flow.

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/pipeline.py backend/app/routers/crawl.py
git commit -m "feat: add post-crawl analysis phase, decoupled from discovery"
```

---

### Task 4: Update backend tests for new analysis flow

**Files:**
- Modify: `backend/tests/` — existing test files as needed

- [ ] **Step 1: Update crawler pipeline tests**

Find and update tests that assert `is_analysed=True` after crawl. After the change, crawl-only should leave `is_analysed=False`. Add separate test for `analyse_unanalysed_for_source`:

```python
def test_crawl_saves_document_without_analysis(db_session):
    """Crawl should save document but NOT analyse it inline."""
    source = create_test_source(db_session)
    result = run_crawl_source(source, db_session, analyse=True)
    assert result["new_documents"] >= 1
    doc = db_session.query(Document).filter(Document.source_id == source.id).first()
    assert doc is not None
    assert doc.is_analysed is False

def test_analyse_unanalysed_for_source_analyses_documents(db_session):
    """Post-crawl analysis should analyse all unanalysed documents."""
    source = create_test_source_with_unanalysed_doc(db_session)
    result = analyse_unanalysed_for_source(source, db_session)
    assert result["analysed"] >= 1
    doc = db_session.query(Document).filter(Document.source_id == source.id).first()
    assert doc.is_analysed is True
```

- [ ] **Step 2: Run all tests and fix failures**

Run: `cd backend && python -m pytest tests/ -v`

Fix any remaining test failures. Key things to check:
- Tests that mock `analyse_document` and expect it called during `run_crawl_source` — move mock to `analyse_unanalysed_for_source`
- Tests that check `CrawlRunSourceStatus` values — ensure `analysing` is handled
- Test that SSE events are still emitted correctly for crawl phase

- [ ] **Step 3: Commit**

```bash
git add backend/tests/
git commit -m "test: update tests for decoupled analysis pipeline"
```

---

### Task 5: Add analysis SSE events to frontend types and stream handler

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 1: Add new SSE event types and update Source type**

In `frontend/src/types/index.ts`, add new event interfaces:

```typescript
export interface CrawlAnalysisPhaseStartEvent {
  type: 'analysis_phase_start';
  crawl_run_id: string;
}

export interface CrawlAnalysisStartEvent {
  type: 'analysis_start';
  crawl_run_id: string;
  source_id: string;
  url: string;
}

export interface CrawlAnalysisProgressEvent {
  type: 'analysis_progress';
  source_id: string;
  current: number;
  total: number;
  url: string;
}

export interface CrawlAnalysisDoneEvent {
  type: 'analysis_done';
  crawl_run_id: string;
  source_id: string;
  url: string;
  analysed: number;
  analyse_ms: number;
}

export interface CrawlAnalysisPhaseDoneEvent {
  type: 'analysis_phase_done';
  crawl_run_id: string;
}
```

Add these to the `CrawlEvent` union type.

Add `analysis_status` to the `Source` interface:

```typescript
export interface Source {
  // ... existing fields ...
  analysis_status: 'pending' | 'analysing' | 'analysed' | 'analysis_failed' | null;
}
```

- [ ] **Step 2: Handle new events in `useCrawlStream.ts`**

In `frontend/src/hooks/useCrawlStream.ts`, add cases to the `handleEvent` switch:

```typescript
case 'analysis_phase_start':
  // Mark that we're now in analysis phase
  setIsAnalysing(true);
  break;
case 'analysis_start':
  setSourceStates((prev) =>
    prev.map((s) =>
      s.source_id === event.source_id
        ? { ...s, currentStep: 'analysing', status: 'running' }
        : s
    ),
  );
  break;
case 'analysis_progress':
  setSourceStates((prev) =>
    prev.map((s) =>
      s.source_id === event.source_id
        ? {
            ...s,
            analysisProgress: {
              current: event.current,
              total: event.total,
              currentUrl: event.url,
            },
          }
        : s
    ),
  );
  break;
case 'analysis_done':
  setSourceStates((prev) =>
    prev.map((s) =>
      s.source_id === event.source_id
        ? {
            ...s,
            status: 'done',
            currentStep: undefined,
            stepTimings: {
              ...s.stepTimings,
              analysing: event.analyse_ms,
            },
            result: s.result
              ? { ...s.result, analysed: event.analysed }
              : { new_documents: 0, skipped: 0, errors: 0, analysed: event.analysed },
          }
        : s
    ),
  );
  break;
case 'analysis_phase_done':
  setIsAnalysing(false);
  break;
```

Add `isAnalysing` to the hook's state and return value. Add `analysisProgress` to `SourceCrawlState` in types.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/useCrawlStream.ts
git commit -m "feat: add analysis phase SSE events to frontend types and stream handler"
```

---

### Task 6: Show analysis phase in CrawlProgressPanel

**Files:**
- Modify: `frontend/src/components/CrawlProgressPanel.tsx`

- [ ] **Step 1: Update STEP_LABELS and add analysis phase section**

In `CrawlProgressPanel.tsx`, the `STEP_LABELS` already has `analysing: 'Analysing...'`. Update the `SourceRow` component to show analysis progress when `currentStep === 'analysing'`:

```typescript
const stepLabel =
  state.status === 'running' && state.currentStep
    ? state.currentStep === 'analysing' && state.analysisProgress
      ? `Analysing ${state.analysisProgress.current}/${state.analysisProgress.total} Dokumente`
      : state.currentStep === 'discovering' && state.discoveryProgress
        ? `Discovering ${state.discoveryProgress.pages_crawled}/${state.discoveryProgress.max_pages} Seiten`
        : STEP_LABELS[state.currentStep]
    : null;
```

Update timings display to include `analysing` step:

```typescript
const order: CrawlStep[] = ['fetching', 'extracting', 'analysing', 'discovering'];
// This already exists, but make sure the shortLabel for analysing is 'analyse':
const shortLabel = step === 'analysing' ? 'analyse' : step === 'discovering' ? 'discover' : step === 'extracting' ? 'extract' : 'fetch';
```

Add a phase indicator at the top of the panel showing "Crawl Phase" vs "Analysis Phase":

```typescript
{isAnalysing && (
  <div className="px-4 py-2 bg-accent-blue/10 border-b border-app-border/30">
    <span className="text-xs text-accent-blue font-medium">
      Analyse-Phase läuft...
    </span>
  </div>
)}
```

Pass `isAnalysing` from the parent component.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CrawlProgressPanel.tsx
git commit -m "feat: show analysis phase in CrawlProgressPanel"
```

---

### Task 7: Show analysis status badge on SourcesAdmin source rows

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`
- Modify: `frontend/src/hooks/useSources.ts` (if needed to include `analysis_status`)

- [ ] **Step 1: Add analysis status badge function**

In `SourcesAdmin.tsx`, add a badge function near `crawlStatusBadge`:

```typescript
function analysisStatusBadge(status: Source['analysis_status']) {
  if (!status) return null;
  const styles: Record<string, string> = {
    pending: 'bg-yellow-500/20 text-yellow-400',
    analysing: 'bg-accent-blue/20 text-accent-blue animate-pulse',
    analysed: 'bg-signal-high/20 text-signal-high',
    analysis_failed: 'bg-red-500/20 text-red-400',
  };
  const labels: Record<string, string> = {
    pending: 'Analyse ausstehend',
    analysing: 'Analysiere...',
    analysed: 'Analysiert',
    analysis_failed: 'Analyse fehlgeschlagen',
  };
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${styles[status] ?? ''}`}>
      {labels[status] ?? status}
    </span>
  );
}
```

- [ ] **Step 2: Add analysis status column to source table**

In the source table header, add after "Status" column:

```tsx
<th className="text-left py-2 text-ink-muted font-medium">Analyse</th>
```

In the table body row, add after the crawl status cell:

```tsx
<td className="py-2">{analysisStatusBadge(source.analysis_status)}</td>
```

- [ ] **Step 3: Invalidate sources query after crawl completes**

When the crawl stream finishes (in the `crawl_done` or `analysis_phase_done` handler), invalidate the `['sources']` query key so the analysis_status badges refresh. This should already happen via `useCrawl` hook's `onSuccess`, but verify it also triggers from the SSE stream completion path.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SourcesAdmin.tsx
git commit -m "feat: show analysis status badge per source in SourcesAdmin"
```

---

### Task 8: Add API endpoint to trigger analysis for unanalysed sources

**Files:**
- Modify: `backend/app/routers/crawl.py` — Add `POST /api/crawl/analyse/{source_id}` endpoint
- Modify: `frontend/src/hooks/useCrawl.ts` — Add mutation hook

- [ ] **Step 1: Add backend endpoint**

In `backend/app/routers/crawl.py`, add:

```python
@router.post("/analyse/{source_id}")
def analyse_source(source_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    result = analyse_unanalysed_for_source(source, db)
    return {
        "source_id": source_id,
        "analysed": result["analysed"],
        "errors": result["errors"],
        "analyse_ms": result["analyse_ms"],
    }
```

- [ ] **Step 2: Add frontend mutation hook**

In `frontend/src/hooks/useCrawl.ts`, add:

```typescript
export function useAnalyseSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => apiPost<{ source_id: string; analysed: number; errors: number; analyse_ms: number }>(`/crawl/analyse/${sourceId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sources'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}
```

- [ ] **Step 3: Add "Analyse" button to SourcesAdmin for sources with pending analysis**

In `SourcesAdmin.tsx`, add a small button in the Actions column when `analysis_status === 'pending'` or `analysis_status === 'analysis_failed'`:

```tsx
{(source.analysis_status === 'pending' || source.analysis_status === 'analysis_failed') && (
  <button
    onClick={() => analyseSource.mutate(source.id)}
    className="text-accent-blue hover:text-accent-blue/80 p-1"
    title="Analyse starten"
  >
    <Play size={12} />
  </button>
)}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/crawl.py frontend/src/hooks/useCrawl.ts frontend/src/pages/SourcesAdmin.tsx
git commit -m "feat: add manual analysis trigger endpoint and UI button"
```

---

### Task 9: End-to-end verification

**Files:** None new

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && python -m pytest tests/ -v
```

All tests should pass.

- [ ] **Step 2: Start dev stack and run a crawl**

```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Trigger a crawl from the UI or via API:
```bash
curl -X POST http://localhost:8000/api/crawl/stream/<source_id> -u admin:changeme
```

Verify:
1. Discovery phase completes quickly (within 1-3 minutes)
2. SSE events show `analysis_phase_start` after `crawl_done`
3. Analysis phase runs with `analysis_start`/`analysis_progress`/`analysis_done` events
4. Source shows `analysis_status: "analysed"` after completion
5. Signals are created during analysis phase, not during crawl

- [ ] **Step 3: Verify SourcesAdmin shows analysis badges**

Open the Sources page in the UI, verify:
- Sources with new unanalysed docs show "Analyse ausstehend" badge
- During analysis, badge shows "Analysiere..." with pulse animation
- After analysis, badge shows "Analysiert"
- The manual "Analyse" button works for re-triggering

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found during e2e verification"
```
