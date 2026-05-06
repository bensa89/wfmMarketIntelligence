# Crawl/Analyse Zweiphasiger Status — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ersetze die fehleranfälligen `isRunning/isAnalysing`-Booleans durch einen einzelnen `phase`-State, der korrekt zwischen Crawl-Phase und Analyse-Phase unterscheidet — ohne "Fertig" zu zeigen solange noch Dokumente analysiert werden.

**Architecture:** Backend erweitert zwei Events um Phasen-Metadaten. Frontend ersetzt zwei Boolean-States durch einen `CrawlPhase`-Enum-State im Hook, der die Source of Truth für alle UI-Zustände ist. CrawlProgressPanel zeigt beide Phasen als separate Sektionen.

**Tech Stack:** Python/FastAPI (Backend), React 18 + TypeScript (Frontend), TanStack Query (Cache-Invalidierung)

---

## File Map

| Datei | Änderung |
|---|---|
| `backend/app/routers/crawl.py` | `crawl_done`-Payload + reconnect `initial_state` erweitern |
| `backend/tests/test_crawl_router.py` | Tests für neue Felder |
| `frontend/src/types/index.ts` | `CrawlPhase` + aktualisierte Event-Interfaces |
| `frontend/src/hooks/useCrawlStream.ts` | Phase-State, Counter, alle Event-Handler |
| `frontend/src/components/CrawlProgressPanel.tsx` | Neue Props, zweiphasige UI |
| `frontend/src/pages/SourcesAdmin.tsx` | Neue Props an CrawlProgressPanel übergeben |

---

## Task 1: Backend — `crawl_done` und `initial_state` erweitern

**Files:**
- Modify: `backend/app/routers/crawl.py:325-334` (crawl_done payload)
- Modify: `backend/app/routers/crawl.py:690-697` (initial_state in reconnect)
- Test: `backend/tests/test_crawl_router.py`

- [ ] **Step 1: Failing test — `crawl_done` hat `analysis_pending`-Feld**

In `backend/tests/test_crawl_router.py`, füge nach dem bestehenden `test_stream_all_sources_returns_events`-Test hinzu:

```python
def test_crawl_done_includes_analysis_pending_true(client, seed_source, db_engine):
    """crawl_done carries analysis_pending=True when new documents were found."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_run(source, db, analyse=True, progress_callback=None):
        return {
            "source_id": source.id,
            "new_documents": 2,
            "skipped": 0,
            "errors": 0,
            "discovery": {},
        }

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run),
        patch("app.routers.crawl.analyse_unanalysed_for_source", return_value=None),
    ):
        response = client.get("/api/crawl/stream")

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    done = next(e for e in events if e["type"] == "crawl_done")
    assert done["analysis_pending"] is True
    assert done["docs_to_analyse"] == 2


def test_crawl_done_includes_analysis_pending_false(client, seed_source, db_engine):
    """crawl_done carries analysis_pending=False when no new documents found."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def mock_run(source, db, analyse=True, progress_callback=None):
        return {
            "source_id": source.id,
            "new_documents": 0,
            "skipped": 1,
            "errors": 0,
            "discovery": {},
        }

    with (
        patch("app.routers.crawl.SessionLocal", TestSessionLocal),
        patch("app.routers.crawl.run_crawl_source", side_effect=mock_run),
    ):
        response = client.get("/api/crawl/stream")

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    done = next(e for e in events if e["type"] == "crawl_done")
    assert done["analysis_pending"] is False
    assert done["docs_to_analyse"] == 0
```

- [ ] **Step 2: Test laufen lassen — erwartet FAIL**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_crawl_done_includes_analysis_pending_true tests/test_crawl_router.py::test_crawl_done_includes_analysis_pending_false -v
```

Erwartet: `FAILED` mit `KeyError: 'analysis_pending'`

- [ ] **Step 3: `crawl_done`-Payload in `crawl.py` erweitern**

In `backend/app/routers/crawl.py`, ersetze das `crawl_done`-Dict (Zeilen ~325-334):

```python
# Vorher:
loop.call_soon_threadsafe(
    queue.put_nowait,
    {
        "type": "crawl_done",
        "crawl_run_id": crawl_run_id,
        "sources_processed": total,
        "total_new": total_new,
        "total_errors": total_errors,
    },
)

# Nachher:
loop.call_soon_threadsafe(
    queue.put_nowait,
    {
        "type": "crawl_done",
        "crawl_run_id": crawl_run_id,
        "sources_processed": total,
        "total_new": total_new,
        "total_errors": total_errors,
        "analysis_pending": total_new > 0,
        "docs_to_analyse": total_new,
    },
)
```

- [ ] **Step 4: Failing test — reconnect `initial_state` hat `analysis_phase_active`**

In `backend/tests/test_crawl_router.py`, füge nach `test_reconnect_with_active_run` hinzu:

```python
def test_reconnect_initial_state_analysis_phase_active(client, seed_source, db_engine):
    """initial_state.analysis_phase_active=True when a source is being analysed."""
    from app.models.crawl_run import CrawlRunSourceStatus

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    verify_db = TestSessionLocal()
    try:
        crawl_run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        verify_db.add(crawl_run)
        verify_db.flush()
        crs = CrawlRunSource(
            crawl_run_id=crawl_run.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.analysing,
        )
        verify_db.add(crs)
        verify_db.commit()
    finally:
        verify_db.close()

    with patch("app.routers.crawl.SessionLocal", TestSessionLocal):
        response = client.get("/api/crawl/reconnect")

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    state = next(e for e in events if e["type"] == "initial_state")
    assert state["analysis_phase_active"] is True


def test_reconnect_initial_state_analysis_phase_inactive(client, seed_source, db_engine):
    """initial_state.analysis_phase_active=False when no source is being analysed."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    verify_db = TestSessionLocal()
    try:
        crawl_run = CrawlRun(status=CrawlRunStatus.running, total_sources=1)
        verify_db.add(crawl_run)
        verify_db.flush()
        crs = CrawlRunSource(
            crawl_run_id=crawl_run.id,
            source_id=seed_source.id,
            url=seed_source.url,
            status=CrawlRunSourceStatus.running,
        )
        verify_db.add(crs)
        verify_db.commit()
    finally:
        verify_db.close()

    with patch("app.routers.crawl.SessionLocal", TestSessionLocal):
        response = client.get("/api/crawl/reconnect")

    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    state = next(e for e in events if e["type"] == "initial_state")
    assert state["analysis_phase_active"] is False
```

- [ ] **Step 5: Test laufen lassen — erwartet FAIL**

```bash
cd backend && python -m pytest tests/test_crawl_router.py::test_reconnect_initial_state_analysis_phase_active tests/test_crawl_router.py::test_reconnect_initial_state_analysis_phase_inactive -v
```

Erwartet: `FAILED` mit `KeyError: 'analysis_phase_active'`

- [ ] **Step 6: Reconnect-Endpoint `initial_state` erweitern**

In `backend/app/routers/crawl.py`, im `reconnect_crawl`-Handler, ersetze den `events.append`-Block für `initial_state` (Zeilen ~690-697):

```python
# Vorher:
events.append(
    {
        "type": "initial_state",
        "crawl_run_id": running_run.id,
        "total": running_run.total_sources,
        "sources": sources_data,
    }
)

# Nachher:
analysis_phase_active = any(
    crs.status == CrawlRunSourceStatus.analysing
    for crs in running_run.sources
)
events.append(
    {
        "type": "initial_state",
        "crawl_run_id": running_run.id,
        "total": running_run.total_sources,
        "sources": sources_data,
        "analysis_phase_active": analysis_phase_active,
    }
)
```

Stelle sicher dass `CrawlRunSourceStatus` im Import-Block von `crawl.py` oben bereits importiert ist (es ist bereits vorhanden in Zeile ~19).

- [ ] **Step 7: Alle Backend-Tests laufen lassen**

```bash
cd backend && python -m pytest tests/test_crawl_router.py -v
```

Erwartet: Alle Tests grün, inkl. der 4 neuen.

- [ ] **Step 8: Commit**

```bash
rtk git add backend/app/routers/crawl.py backend/tests/test_crawl_router.py
rtk git commit -m "feat: extend crawl_done and initial_state with analysis phase metadata"
```

---

## Task 2: Frontend — Typen aktualisieren

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: `CrawlPhase`-Typ hinzufügen**

In `frontend/src/types/index.ts`, füge vor der `CrawlDoneEvent`-Interface-Definition hinzu:

```typescript
export type CrawlPhase = 'idle' | 'crawling' | 'analysing' | 'done';
```

- [ ] **Step 2: `CrawlDoneEvent` erweitern**

Ersetze die bestehende `CrawlDoneEvent`-Interface (Zeilen ~235-241):

```typescript
// Vorher:
export interface CrawlDoneEvent {
  type: 'crawl_done';
  crawl_run_id: string;
  sources_processed: number;
  total_new: number;
  total_errors: number;
}

// Nachher:
export interface CrawlDoneEvent {
  type: 'crawl_done';
  crawl_run_id: string;
  sources_processed: number;
  total_new: number;
  total_errors: number;
  analysis_pending: boolean;
  docs_to_analyse: number;
}
```

- [ ] **Step 3: `CrawlInitialStateEvent` erweitern**

Ersetze die bestehende `CrawlInitialStateEvent`-Interface (Zeilen ~248-253):

```typescript
// Vorher:
export interface CrawlInitialStateEvent {
  type: 'initial_state';
  crawl_run_id: string;
  total: number;
  sources: CrawlRunSourceState[];
}

// Nachher:
export interface CrawlInitialStateEvent {
  type: 'initial_state';
  crawl_run_id: string;
  total: number;
  sources: CrawlRunSourceState[];
  analysis_phase_active: boolean;
}
```

- [ ] **Step 4: TypeScript-Build prüfen**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Erwartet: Fehler in `useCrawlStream.ts` und `CrawlProgressPanel.tsx` (weil Felder noch nicht genutzt werden) — das ist OK, wird in Task 3+4 behoben.

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/types/index.ts
rtk git commit -m "feat: add CrawlPhase type and extend CrawlDoneEvent/CrawlInitialStateEvent"
```

---

## Task 3: Frontend — `useCrawlStream` Hook refactoren

**Files:**
- Modify: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 1: Import und State-Deklaration ersetzen**

Am Anfang von `useCrawlStream.ts`, ersetze die Imports:

```typescript
// Vorher:
import type {
  CrawlEvent,
  CrawlStreamSummary,
  CrawlRunList,
  CrawlRunSourceState,
  SourceCrawlState,
} from '../types';

// Nachher:
import type {
  CrawlEvent,
  CrawlPhase,
  CrawlStreamSummary,
  CrawlRunList,
  CrawlRunSourceState,
  SourceCrawlState,
} from '../types';
```

- [ ] **Step 2: State-Deklarationen im Hook ersetzen**

Ersetze in der `useCrawlStream`-Funktion die ersten State-Zeilen (Zeilen ~44-47):

```typescript
// Vorher:
const [isRunning, setIsRunning] = useState(false);
const isRunningRef = useRef(false);
const [isAnalysing, setIsAnalysing] = useState(false);
const isAnalysingRef = useRef(false);

// Nachher:
const [phase, setPhase] = useState<CrawlPhase>('idle');
const phaseRef = useRef<CrawlPhase>('idle');
const [analysisDocsTotal, setAnalysisDocsTotal] = useState(0);
const [analysisDocsDone, setAnalysisDocsDone] = useState(0);
// Computed für interne Nutzung (startQueuedStream, start, cancel)
const isRunningRef = useRef(false);
```

Hinweis: `isRunningRef` bleibt als Mechanismus um gleichzeitige Stream-Starts zu verhindern — das ist unabhängig vom Display-State.

- [ ] **Step 3: Hilfsfunktion zum phasen-sicheren Setzen hinzufügen**

Direkt nach den State-Deklarationen, vor `handleEvent`:

```typescript
const setPhaseSync = useCallback((p: CrawlPhase) => {
  phaseRef.current = p;
  setPhase(p);
}, []);
```

- [ ] **Step 4: Event-Handler `crawl_start` aktualisieren**

Im `handleEvent`-Switch, ersetze den `crawl_start`-Case:

```typescript
// Vorher:
case 'crawl_start':
  setCrawlRunId(event.crawl_run_id);
  setCrawlTotal(event.total);
  setQueuedSources([]);
  queuedRunIdRef.current = null;
  break;

// Nachher:
case 'crawl_start':
  setCrawlRunId(event.crawl_run_id);
  setCrawlTotal(event.total);
  setQueuedSources([]);
  queuedRunIdRef.current = null;
  setAnalysisDocsTotal(0);
  setAnalysisDocsDone(0);
  setPhaseSync('crawling');
  break;
```

- [ ] **Step 5: Event-Handler `initial_state` aktualisieren**

Ersetze den `initial_state`-Case:

```typescript
// Vorher:
case 'initial_state':
  setCrawlRunId(event.crawl_run_id);
  setCrawlTotal(event.total);
  setSourceStates(
    event.sources.map((s) => ({
      // ... mapping ...
    })),
  );
  setIsRunning(true);
  break;

// Nachher:
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
        fetching: s.fetch_ms!,
        extracting: s.extract_ms!,
        analysing: s.analyse_ms!,
        discovering: s.discover_ms!,
      } : undefined,
      discoveryProgress:
        s.current_step === 'discovering' && s.discover_pages_crawled != null
          ? {
              pages_found: s.discover_pages_found ?? s.discover_pages_crawled,
              pages_crawled: s.discover_pages_crawled,
              max_pages: 50,
            }
          : undefined,
    })),
  );
  setPhaseSync(event.analysis_phase_active ? 'analysing' : 'crawling');
  break;
```

- [ ] **Step 6: Event-Handler `no_active_run` aktualisieren**

```typescript
// Vorher:
case 'no_active_run':
  setIsRunning(false);
  break;

// Nachher:
case 'no_active_run':
  setPhaseSync('idle');
  break;
```

- [ ] **Step 7: Event-Handler `crawl_done` aktualisieren**

Ersetze den `crawl_done`-Case vollständig:

```typescript
// Vorher:
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
  if (!isAnalysingRef.current) {
    setIsRunning(false);
  }
  if (queuedRunIdRef.current) {
    setTimeout(() => startQueuedStreamRef.current(), 300);
  }
  break;

// Nachher:
case 'crawl_done':
  setSummary({
    sources_processed: event.sources_processed,
    total_new: event.total_new,
    total_errors: event.total_errors,
  });
  setAnalysisDocsTotal(event.docs_to_analyse);
  qc.invalidateQueries({ queryKey: ['documents'] });
  qc.invalidateQueries({ queryKey: ['signals'] });
  qc.invalidateQueries({ queryKey: ['sources'] });
  qc.invalidateQueries({ queryKey: ['crawlRuns'] });
  qc.invalidateQueries({ queryKey: ['activeCrawlRun'] });
  qc.invalidateQueries({ queryKey: ['discoveredPagesStats'] });
  qc.invalidateQueries({ queryKey: ['signalsOverTime'] });
  qc.invalidateQueries({ queryKey: ['signalDistribution'] });
  qc.invalidateQueries({ queryKey: ['sourceCandidates'] });
  if (event.analysis_pending) {
    setPhaseSync('analysing');
  } else {
    setPhaseSync('done');
    isRunningRef.current = false;
    if (queuedRunIdRef.current) {
      setTimeout(() => startQueuedStreamRef.current(), 300);
    }
  }
  break;
```

- [ ] **Step 8: Event-Handler `analysis_phase_start` aktualisieren**

```typescript
// Vorher:
case 'analysis_phase_start':
  setIsAnalysing(true);
  isAnalysingRef.current = true;
  break;

// Nachher:
case 'analysis_phase_start':
  setPhaseSync('analysing');
  break;
```

- [ ] **Step 9: Event-Handler `analysis_start` aktualisieren**

```typescript
// Vorher:
case 'analysis_start':
  setSourceStates((prev) =>
    prev.map((s) =>
      s.source_id === event.source_id
        ? { ...s, currentStep: 'analysing', status: 'running' }
        : s
    ),
  );
  break;

// Nachher:
case 'analysis_start':
  setSourceStates((prev) =>
    prev.map((s) =>
      s.source_id === event.source_id
        ? { ...s, currentStep: 'analysing', status: 'running' }
        : s
    ),
  );
  qc.invalidateQueries({ queryKey: ['sources'] });
  break;
```

- [ ] **Step 10: Event-Handler `analysis_done` aktualisieren**

```typescript
// Vorher:
case 'analysis_done':
  setSourceStates((prev) =>
    prev.map((s) =>
      s.source_id === event.source_id
        ? {
            ...s,
            status: 'done',
            currentStep: undefined,
            analysisProgress: undefined,
            stepTimings: {
              ...s.stepTimings,
              analysing: event.analyse_ms,
            },
          }
        : s
    ),
  );
  break;

// Nachher:
case 'analysis_done':
  setSourceStates((prev) =>
    prev.map((s) =>
      s.source_id === event.source_id
        ? {
            ...s,
            status: 'done',
            currentStep: undefined,
            analysisProgress: undefined,
            stepTimings: {
              ...s.stepTimings,
              analysing: event.analyse_ms,
            },
          }
        : s
    ),
  );
  setAnalysisDocsDone((n) => n + event.analysed);
  qc.invalidateQueries({ queryKey: ['sources'] });
  break;
```

- [ ] **Step 11: Event-Handler `analysis_phase_done` aktualisieren**

```typescript
// Vorher:
case 'analysis_phase_done':
  setIsAnalysing(false);
  isAnalysingRef.current = false;
  setIsRunning(false);
  break;

// Nachher:
case 'analysis_phase_done':
  setPhaseSync('done');
  isRunningRef.current = false;
  if (queuedRunIdRef.current) {
    setTimeout(() => startQueuedStreamRef.current(), 300);
  }
  break;
```

- [ ] **Step 12: `startQueuedStream` und `start`-Callbacks aktualisieren**

In `startQueuedStream` (Zeile ~287):

```typescript
// Vorher:
const startQueuedStream = useCallback(async () => {
  if (isRunningRef.current) return;
  isRunningRef.current = true;
  setIsRunning(true);
  setSourceStates([]);
  setSummary(null);
  setConnectionError(null);
  setCrawlTotal(0);
  // ...
  } finally {
    isRunningRef.current = false;
    setIsRunning(false);
  }
}, [handleEvent]);

// Nachher:
const startQueuedStream = useCallback(async () => {
  if (isRunningRef.current) return;
  isRunningRef.current = true;
  setPhaseSync('crawling');
  setSourceStates([]);
  setSummary(null);
  setConnectionError(null);
  setCrawlTotal(0);
  setAnalysisDocsTotal(0);
  setAnalysisDocsDone(0);
  // ... rest bleibt gleich ...
  } finally {
    isRunningRef.current = false;
    // phase wird durch Events gesetzt, nicht hier
  }
}, [handleEvent, setPhaseSync]);
```

Im `start`-Callback (suche nach `setIsRunning(true)` in der `start`-Funktion), ersetze:

```typescript
// Vorher:
setIsRunning(true);

// Nachher:
setPhaseSync('crawling');
```

Und am Ende des Stream-Loops im `start`-Callback, wenn der Stream ohne `analysis_phase_done` endet (finally-Block):

```typescript
// Vorher (finally in start):
} finally {
  isRunningRef.current = false;
  if (!isAnalysingRef.current) setIsRunning(false);
}

// Nachher:
} finally {
  isRunningRef.current = false;
  // phase wird durch Events gesetzt; kein Override hier nötig
}
```

- [ ] **Step 13: `cancel`- und `reset`-Funktionen aktualisieren**

Ersetze die `cancel`-Funktion (Zeile ~538):

```typescript
// Vorher:
const cancel = useCallback(() => {
  abortRef.current?.abort();
  apiPost('/crawl/cancel').catch(() => {});
  isRunningRef.current = false;
  setIsRunning(false);
}, []);

// Nachher:
const cancel = useCallback(() => {
  abortRef.current?.abort();
  apiPost('/crawl/cancel').catch(() => {});
  isRunningRef.current = false;
  setPhaseSync('idle');
}, [setPhaseSync]);
```

Ersetze die `reset`-Funktion (Zeile ~545):

```typescript
// Vorher:
const reset = useCallback(() => {
  abortRef.current?.abort();
  setSourceStates([]);
  setSummary(null);
  setConnectionError(null);
  setCrawlTotal(0);
  setCrawlRunId(null);
  setIsAnalysing(false);
  isAnalysingRef.current = false;
}, []);

// Nachher:
const reset = useCallback(() => {
  abortRef.current?.abort();
  setSourceStates([]);
  setSummary(null);
  setConnectionError(null);
  setCrawlTotal(0);
  setCrawlRunId(null);
  setAnalysisDocsTotal(0);
  setAnalysisDocsDone(0);
  setPhaseSync('idle');
}, [setPhaseSync]);
```

Ersetze außerdem in der `start`-Funktion (Zeile ~474) `setIsRunning(true)`:

```typescript
// Vorher:
setIsRunning(true);

// Nachher:
setPhaseSync('crawling');
setAnalysisDocsTotal(0);
setAnalysisDocsDone(0);
```

Und den `finally`-Block der `start`-Funktion (Zeile ~530):

```typescript
// Vorher:
} finally {
  isRunningRef.current = false;
  setIsRunning(false);
}

// Nachher:
} finally {
  isRunningRef.current = false;
  // phase wird durch Events gesetzt; AbortError (cancel) wird durch cancel() auf 'idle' gesetzt
}
```

- [ ] **Step 14: Return-Wert des Hooks aktualisieren**

Ersetze den `return`-Statement des Hooks (Zeile ~556):

```typescript
// Vorher:
return {
  start,
  cancel,
  reset,
  isRunning,
  isAnalysing,
  crawlRunId,
  sourceStates,
  summary,
  connectionError,
  crawlTotal,
  queuedSources,
};

// Nachher:
const isRunning = phase === 'crawling' || phase === 'analysing';
const isAnalysing = phase === 'analysing';
return {
  phase,
  analysisDocsTotal,
  analysisDocsDone,
  isRunning,
  isAnalysing,
  start,
  cancel,
  reset,
  crawlRunId,
  sourceStates,
  summary,
  connectionError,
  crawlTotal,
  queuedSources,
};
```

- [ ] **Step 15: TypeScript-Build prüfen**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -40
```

Erwartet: Mögliche Fehler in `CrawlProgressPanel.tsx` (da Props noch nicht aktualisiert), aber keine Fehler in `useCrawlStream.ts` selbst.

- [ ] **Step 16: Commit**

```bash
rtk git add frontend/src/hooks/useCrawlStream.ts
rtk git commit -m "feat: replace isRunning/isAnalysing booleans with CrawlPhase state in useCrawlStream"
```

---

## Task 4: Frontend — `CrawlProgressPanel` aktualisieren

**Files:**
- Modify: `frontend/src/components/CrawlProgressPanel.tsx`

- [ ] **Step 1: Import und Props-Interface aktualisieren**

Ersetze den Import-Block oben in `CrawlProgressPanel.tsx`:

```typescript
// Vorher:
import type { SourceCrawlState, CrawlStreamSummary, CrawlStep } from '../types';

// Nachher:
import type { SourceCrawlState, CrawlStreamSummary, CrawlStep, CrawlPhase } from '../types';
```

Ersetze das `Props`-Interface:

```typescript
// Vorher:
interface Props {
  isRunning: boolean;
  isAnalysing: boolean;
  sourceStates: SourceCrawlState[];
  summary: CrawlStreamSummary | null;
  connectionError: string | null;
  crawlTotal?: number;
  queuedSources?: { source_id: string; url: string }[];
  onCancel: () => void;
  onDismiss: () => void;
}

// Nachher:
interface Props {
  phase: CrawlPhase;
  analysisDocsTotal: number;
  analysisDocsDone: number;
  sourceStates: SourceCrawlState[];
  summary: CrawlStreamSummary | null;
  connectionError: string | null;
  crawlTotal?: number;
  queuedSources?: { source_id: string; url: string }[];
  onCancel: () => void;
  onDismiss: () => void;
}
```

- [ ] **Step 2: Funktion-Signatur und Sichtbarkeits-Check aktualisieren**

Ersetze die Funktion-Signatur und die erste `if`-Zeile:

```typescript
// Vorher:
export function CrawlProgressPanel({
  isRunning,
  isAnalysing,
  sourceStates,
  summary,
  connectionError,
  crawlTotal,
  queuedSources = [],
  onCancel,
  onDismiss,
}: Props) {
  if (!isRunning && !summary && !connectionError && sourceStates.length === 0 && queuedSources.length === 0) return null;

// Nachher:
export function CrawlProgressPanel({
  phase,
  analysisDocsTotal,
  analysisDocsDone,
  sourceStates,
  summary,
  connectionError,
  crawlTotal,
  queuedSources = [],
  onCancel,
  onDismiss,
}: Props) {
  if (phase === 'idle' && !summary && !connectionError && sourceStates.length === 0 && queuedSources.length === 0) return null;
```

- [ ] **Step 3: Berechnete Variablen und Border-Farbe aktualisieren**

Ersetze nach dem Sichtbarkeits-Check:

```typescript
// Vorher:
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

// Nachher:
const doneCount = sourceStates.filter(
  (s) => s.status === 'done' || s.status === 'error',
).length;
const total = summary?.sources_processed ?? crawlTotal ?? sourceStates.length;
const hasErrors = (summary?.total_errors ?? 0) > 0 || connectionError != null;
const hasQueue = queuedSources.length > 0;

const borderColor = hasErrors
  ? 'border-signal-low/40'
  : phase === 'done'
    ? 'border-signal-high/40'
    : 'border-accent-blue/40';

const isActive = phase === 'crawling' || phase === 'analysing';
const runCounter = hasQueue ? ' (1/2)' : '';

const headerText = connectionError
  ? `Connection failed: ${connectionError}`
  : phase === 'crawling'
    ? `Crawl läuft…${runCounter} (${doneCount}/${total})`
    : phase === 'analysing'
      ? `Analyse läuft… (${analysisDocsDone}/${analysisDocsTotal} Docs)`
      : hasErrors
        ? `Fertig — ${total} Sources, ${summary?.total_new ?? 0} neue Docs, ${summary?.total_errors ?? 0} Fehler`
        : `Fertig — ${summary?.total_new ?? 0} neue Docs${analysisDocsDone > 0 ? `, ${analysisDocsDone} analysiert` : ''}`;
```

- [ ] **Step 4: Header-Buttons aktualisieren**

Ersetze im JSX die Button-Logik:

```tsx
// Vorher:
{isRunning ? (
  <button onClick={onCancel} className="text-xs text-ink-muted hover:text-ink px-2 py-0.5 rounded">
    Cancel
  </button>
) : (
  <button onClick={onDismiss} className="text-ink-muted hover:text-ink" aria-label="Dismiss">
    <X size={16} />
  </button>
)}

// Nachher:
{isActive ? (
  <button onClick={onCancel} className="text-xs text-ink-muted hover:text-ink px-2 py-0.5 rounded">
    Cancel
  </button>
) : (
  <button onClick={onDismiss} className="text-ink-muted hover:text-ink" aria-label="Dismiss">
    <X size={16} />
  </button>
)}
```

- [ ] **Step 5: Blauen Analyse-Banner entfernen, Analyse-Fortschritts-Sektion hinzufügen**

Ersetze den `isAnalysing`-Banner-Block und die darauffolgende Source-Liste:

```tsx
// Vorher:
{isAnalysing && (
  <div className="px-4 py-2 bg-accent-blue/10 border-b border-app-border/30">
    <span className="text-xs text-accent-blue font-medium">
      Analyse-Phase läuft...
    </span>
  </div>
)}
<div>
  {sourceStates.map((s) => (
    <SourceRow key={s.source_id} state={s} />
  ))}
</div>

// Nachher:
<div>
  {sourceStates.map((s) => (
    <SourceRow key={s.source_id} state={s} />
  ))}
</div>
{(phase === 'analysing' || (phase === 'done' && analysisDocsDone > 0)) && (
  <div className="px-4 py-2 border-t border-app-border/30 bg-app-bg/40 flex items-center gap-2">
    {phase === 'analysing' && (
      <Loader2 className="w-3 h-3 animate-spin text-accent-blue flex-shrink-0" />
    )}
    {phase === 'done' && analysisDocsDone > 0 && (
      <Check className="w-3 h-3 text-signal-high flex-shrink-0" />
    )}
    <span className="text-xs text-ink-muted">
      {phase === 'analysing'
        ? `Analyse läuft… ${analysisDocsDone}/${analysisDocsTotal} Dokumente`
        : `${analysisDocsDone} Dokumente analysiert`}
    </span>
  </div>
)}
```

- [ ] **Step 6: TypeScript-Build prüfen**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -40
```

Erwartet: Fehler in `SourcesAdmin.tsx` (Props nicht aktualisiert) — wird in Task 5 behoben.

- [ ] **Step 7: Commit**

```bash
rtk git add frontend/src/components/CrawlProgressPanel.tsx
rtk git commit -m "feat: two-phase UI in CrawlProgressPanel with phase prop and analysis progress section"
```

---

## Task 5: Frontend — `SourcesAdmin` Props aktualisieren

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Props an `CrawlProgressPanel` aktualisieren**

Suche in `frontend/src/pages/SourcesAdmin.tsx` nach dem `CrawlProgressPanel`-Aufruf (Zeile ~355-365) und ersetze die Props:

```tsx
// Vorher:
<CrawlProgressPanel
  isRunning={stream.isRunning}
  isAnalysing={stream.isAnalysing}
  sourceStates={stream.sourceStates}
  summary={stream.summary}
  connectionError={stream.connectionError}
  crawlTotal={stream.crawlTotal}
  queuedSources={stream.queuedSources}
  onCancel={stream.cancel}
  onDismiss={stream.dismiss}
/>

// Nachher:
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
  onDismiss={stream.dismiss}
/>
```

- [ ] **Step 2: "Crawling..."-Button-Text aktualisieren**

Suche nach dem `stream.isRunning`-Check im Button (Zeile ~349):

```tsx
// Vorher:
<button onClick={() => stream.start()} disabled={stream.isRunning} className="btn-primary flex items-center gap-2">
  <Play size={16} /> {stream.isRunning ? 'Crawling...' : 'Run Full Crawl'}
</button>

// Nachher:
<button onClick={() => stream.start()} disabled={stream.isRunning} className="btn-primary flex items-center gap-2">
  <Play size={16} /> {stream.isRunning ? (stream.isAnalysing ? 'Analysiere...' : 'Crawling...') : 'Run Full Crawl'}
</button>
```

Hinweis: `stream.isRunning` und `stream.isAnalysing` sind weiterhin als computed properties verfügbar — kein Import nötig.

- [ ] **Step 3: TypeScript-Build prüfen — keine Fehler erwartet**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Erwartet: Keine Fehler.

- [ ] **Step 4: Vollständige Backend-Test-Suite**

```bash
cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Erwartet: Alle Tests grün.

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/pages/SourcesAdmin.tsx
rtk git commit -m "feat: pass phase and analysis counters to CrawlProgressPanel in SourcesAdmin"
```

---

## Task 6: Manueller End-to-End-Test

- [ ] **Step 1: Dev-Stack starten**

```bash
docker compose -f docker-compose.dev.yml up -d
```

- [ ] **Step 2: Crawl starten und Phasen beobachten**

1. Öffne die App im Browser, navigiere zu Sources
2. Starte einen Crawl auf einer Source mit Subpages (z.B. quinyx.com/solutions/...)
3. Prüfe: Header zeigt "Crawl läuft… (0/1)"
4. Nach Crawl-Ende: Header zeigt "Analyse läuft… (0/N Docs)" — NICHT "Fertig"
5. Während Analyse: Fortschrittsanzeige im Analyse-Bereich zählt hoch
6. Nach Analyse: Header zeigt "Fertig — N neue Docs, M analysiert"

- [ ] **Step 3: Seiten-Refresh während Analyse testen**

1. Starte einen neuen Crawl
2. Warte bis "Analyse läuft…" erscheint
3. Seite neu laden (F5)
4. Prüfe: Panel zeigt wieder "Analyse läuft…" (nicht leer, nicht "Fertig")

- [ ] **Step 4: Badge-Live-Update in SourcesAdmin testen**

1. Starte einen Crawl
2. Beobachte die Sources-Tabelle (OHNE Seiten-Refresh)
3. Prüfe: Badge wechselt von "Analyse ausstehend" → "Analysiere…" → "Analysiert" automatisch

- [ ] **Step 5: Abschlusskcommit wenn alles korrekt**

```bash
rtk git add -A
rtk git commit -m "feat: two-phase crawl/analysis status complete"
```
