# Design: Polling-basiertes Crawl/Analyse-Status-System

## Kontext

Das bisherige SSE-basierte Status-System hat strukturelle Probleme: Der `/reconnect`-Endpoint gibt nur einen einmaligen Snapshot zurück (keine Live-Events), wodurch das Frontend nach einem Page-Refresh vom laufenden Crawl-Thread abgekoppelt wird. Die Queue-Logik liegt vollständig im Frontend-State und geht bei Tab-Schließung verloren.

## Ziel

- Crawl- und Analyse-Status überlebt Page-Refresh und Tab-Wechsel zuverlässig
- Immer sichtbar ob Crawl, Discovery oder Analyse im Hintergrund läuft
- Pro Source: Analyse-Fortschritt (Dokument X/Y + aktuell analysierte URL)
- Queue-Verarbeitung läuft im Backend, nicht im Frontend
- "Fertig"-Zustand bleibt sichtbar bis manuell dismissed

## Architektur

### Polling-Zyklus

- Frontend pollt `GET /api/crawl/status` alle **2s** wenn `active_run.status == running`
- Frontend pollt alle **10s** wenn `status == completed | failed` (Panel bleibt sichtbar)
- Beim Mount: sofortiger Fetch → Panel zeigt automatisch laufende und abgeschlossene Runs

### Trennung von Start und Status

- `POST /api/crawl/run` startet den Crawl-Thread im Hintergrund, antwortet sofort mit `{ crawl_run_id }`
- Status-Anzeige ist vollständig vom Trigger entkoppelt — der Hook registriert einfach was die DB sagt

## Backend-Änderungen

### 1. Migration: Neue Felder auf `CrawlRunSource`

```
analyse_docs_done    Integer, default 0
analyse_docs_total   Integer, default 0
analyse_current_url  String, nullable
```

Der Analyse-Callback in `crawl.py` schreibt diese Felder nach jedem Dokument in die DB. Polling liest sie beim nächsten Tick.

### 2. `POST /api/crawl/run` (ersetzt `/stream`)

Startet `_run_sources_in_thread` als Daemon-Thread, gibt sofort zurück:

```json
{ "crawl_run_id": "...", "status": "running", "total_sources": 5 }
```

Gleiches für `POST /api/crawl/run/{source_id}`.

### 3. `GET /api/crawl/status`

Gibt den aktuellen Systemzustand zurück:

```json
{
  "active_run": {
    "id": "...",
    "status": "running",
    "started_at": "...",
    "total_sources": 5,
    "sources": [
      {
        "source_id": "...",
        "url": "...",
        "status": "analysing",
        "current_step": null,
        "new_documents": 3,
        "skipped": 12,
        "errors": 0,
        "error_message": null,
        "analyse_docs_done": 2,
        "analyse_docs_total": 3,
        "analyse_current_url": "https://competitor.com/blog/post"
      }
    ]
  },
  "queued_run": {
    "id": "...",
    "sources": [{ "source_id": "...", "url": "..." }]
  }
}
```

`active_run` ist `null` wenn kein Run läuft oder in der DB ist. `queued_run` ist `null` wenn nichts wartet. Completed/failed Runs werden für 24h zurückgegeben (für "Fertig"-Zustand).

### 4. Queue-Logik ins Backend

Am Ende von `_run_sources_in_thread` (nach `status = completed`): prüft ob ein `CrawlRun` mit `status=queued` existiert und startet ihn als neuen Thread. Kein Browser muss offen sein.

`POST /api/crawl/enqueue/{source_id}` bleibt unverändert.

### 5. Entfernte Endpoints

- `GET /api/crawl/stream` → ersetzt durch `POST /api/crawl/run`
- `GET /api/crawl/stream/{source_id}` → ersetzt durch `POST /api/crawl/run/{source_id}`
- `GET /api/crawl/stream/queued` → nicht mehr nötig (Backend startet Queue selbst)
- `GET /api/crawl/reconnect` → nicht mehr nötig

## Frontend-Änderungen

### `useCrawlStatus` Hook (ersetzt `useCrawlStream`)

```typescript
// Polling alle 2s bei laufendem Run, 10s bei abgeschlossenem
// start(sourceId?) → POST /api/crawl/run[/{sourceId}]
// cancel() → POST /api/crawl/cancel
// dismiss() → lokaler Reset
// isRunning: boolean
// phase: 'idle' | 'crawling' | 'analysing' | 'done' | 'error'
```

Beim Mount: einmaliger Fetch. Panel erscheint automatisch wenn Backend einen aktiven/fertigen Run meldet.

### `CrawlProgressPanel` Erweiterungen

Pro Source im `analysing`-Status:
```
Analysiere 2/3 — https://competitor.com/blog/post
```

Panel verschwindet nicht automatisch bei `done` — zeigt Zusammenfassung bis User dismissed.

### Entfernte Dateien / Code

- `frontend/src/hooks/useCrawlStream.ts` → komplett ersetzt
- `queuedRunIdRef`, `startQueuedStreamRef`, SSE-Reader-Loop, `reconnect`-Logik

## Datenbankmigrationen

1. Neue Alembic-Migration: `add_analyse_progress_to_crawl_run_source`

## Testing

- Bestehende Tests in `test_crawl_router.py` auf neue Endpoint-Namen anpassen
- Neuer Test: `GET /api/crawl/status` gibt korrekten Zustand zurück
- Neuer Test: Queue wird automatisch gestartet wenn aktiver Run endet
