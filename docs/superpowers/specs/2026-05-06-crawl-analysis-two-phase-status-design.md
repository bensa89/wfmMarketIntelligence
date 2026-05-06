# Design: Zweiphasiger Crawl/Analyse-Status

**Datum:** 2026-05-06  
**Status:** Approved

## Kontext

Crawl und Analyse wurden bereits entkoppelt. Das Problem: Das Frontend zeigt "Fertig" sobald `crawl_done` eintrifft — aber zu diesem Zeitpunkt läuft die Analyse noch gar nicht (oder hat gerade erst begonnen). Außerdem überleben Status-Änderungen während der Analyse keinen Seiten-Refresh.

## Ziel

- UI zeigt immer die aktuelle Phase (Crawl / Analyse / Fertig)
- Kein "Fertig" solange noch Dokumente analysiert werden
- Live-Badges in SourcesAdmin ohne Seiten-Refresh
- Vollständige Seiten-Refresh-Resistenz

---

## State-Modell

Bisherige Implementierung: zwei unabhängige Booleans `isRunning + isAnalysing` mit Race-Condition-Risiko.

Neue Implementierung: ein einziger `phase`-State in `useCrawlStream`:

```typescript
type CrawlPhase = 'idle' | 'crawling' | 'analysing' | 'done';
```

### Transitionen

| Event | Bedingung | Neue Phase |
|---|---|---|
| `crawl_start` | — | `crawling` |
| `crawl_done` | `analysis_pending: true` | `analysing` |
| `crawl_done` | `analysis_pending: false` | `done` |
| `analysis_phase_start` | — | `analysing` (Safety-Net) |
| `analysis_phase_done` | — | `done` |
| `initial_state` (Reconnect) | mind. 1 Source `analysing` | `analysing` |
| `initial_state` (Reconnect) | keine Source `analysing` | `crawling` |
| `no_active_run` | — | `idle` |

`isRunning` und `isAnalysing` werden entfernt. Bestehende Konsumenten werden auf `phase` migriert.

---

## Backend-Änderungen

### 1. `crawl_done`-Payload erweitern

```python
emit({
    "type": "crawl_done",
    "total_new": total_new,
    "total_skipped": total_skipped,
    "total_errors": total_errors,
    "analysis_pending": total_new > 0,   # NEU
    "docs_to_analyse": total_new,        # NEU
})
```

### 2. `reconnect`-Endpoint: `initial_state` erweitern

```python
analysis_phase_active = any(
    crs.status == CrawlRunSourceStatus.analysing
    for crs in running_run.sources
)
events.append({
    "type": "initial_state",
    ...
    "analysis_phase_active": analysis_phase_active,  # NEU
})
```

Keine weiteren Backend-Änderungen nötig — `analysis_phase_start`, `analysis_start`, `analysis_progress`, `analysis_done`, `analysis_phase_done` existieren bereits.

---

## Frontend-Änderungen

### useCrawlStream.ts

**Entfernen:** `isRunning`, `isAnalysing`, `isRunningRef`, `isAnalysingRef`  
**Hinzufügen:** `phase: CrawlPhase`, `phaseRef: MutableRefObject<CrawlPhase>`

**Neue Counter:**
```typescript
analysisDocsTotal: number   // gesetzt bei crawl_done (docs_to_analyse) oder analysis_phase_start
analysisDocsDone: number    // aufsummiert aus analysis_done.analysed pro Source
```

**Event-Handler-Änderungen:**

- `crawl_start` → `setPhase('crawling')`
- `crawl_done`:
  - `setSummary(...)` wie bisher
  - `event.analysis_pending ? setPhase('analysing') : setPhase('done')`
  - `invalidateQueries(['sources'])` wie bisher
- `analysis_phase_start` → `setPhase('analysing')` (Safety-Net, falls crawl_done noch nicht verarbeitet)
- `crawl_done` → `setAnalysisDocsTotal(event.docs_to_analyse)` (Total aus Backend)
- `analysis_start` → Source-Status auf `analysing`, `invalidateQueries(['sources'])`
- `analysis_done` → `setAnalysisDocsDone(n => n + event.analysed)`, Source-Status auf `done`, `invalidateQueries(['sources'])`
- `analysis_phase_done` → `setPhase('done')`
- `initial_state` → `setPhase(event.analysis_phase_active ? 'analysing' : 'crawling')`
- `no_active_run` → `setPhase('idle')`

**Rückwärtskompatibilität für Konsumenten:**
```typescript
// Computed properties für sanfte Migration
const isRunning = phase === 'crawling' || phase === 'analysing';
const isAnalysing = phase === 'analysing';
```
Diese können nach vollständiger Migration entfernt werden.

### CrawlProgressPanel.tsx

**Header-Text:**
```typescript
const headerText =
  phase === 'crawling' ? `Crawl läuft… (${doneCount}/${total})` :
  phase === 'analysing' ? `Analyse läuft… (${analysisDocsDone}/${analysisDocsTotal} Docs)` :
  phase === 'done' ? `Fertig — ${summary.total_new} neue Docs, ${analysisDocsDone} analysiert` :
  'Bereit';
```

**Panel-Aufbau:**
1. **Crawl-Ergebnisse** (Phase 1): Bleibt sichtbar auch während Analyse läuft. Zeigt je Source: neue Docs, Skip, Fehler, Timing.
2. **Analyse-Fortschritt** (Phase 2, ab `phase === 'analysing'`): Zeigt welche Source gerade analysiert wird + Gesamt-Fortschrittsanzeige (X/Y Docs).

**Entfernen:** Den isolierten blauen `isAnalysing`-Banner (`bg-accent-blue/10`), da die Info jetzt im Header steht.

### SourcesAdmin.tsx

Keine direkten Änderungen nötig. Durch `invalidateQueries(['sources'])` bei `analysis_start` und `analysis_done` (in useCrawlStream) aktualisieren sich die Badges (Analyse ausstehend / Analysiere… / Analysiert) automatisch ohne Seiten-Refresh.

---

## Seiten-Refresh-Verhalten

| Zeitpunkt des Refreshes | Verhalten nach Refresh |
|---|---|
| Während Crawl läuft | `initial_state` → `phase='crawling'`, Snapshot sichtbar |
| Zwischen Crawl-Ende und Analyse-Start | `initial_state` mit `analysis_phase_active=false`, aber Source `analysis_status='pending'` → `phase='crawling'` (kurzes Fenster, akzeptabel) |
| Während Analyse läuft | `initial_state` mit `analysis_phase_active=true` → `phase='analysing'` |
| Nach Abschluss | `no_active_run` → `phase='idle'`, Badges aus DB korrekt |

---

## Nicht im Scope

- Live-Updates des Reconnect-Streams nach dem Snapshot (kein Re-Attach an SSE-Stream nach Refresh — der Snapshot reicht)
- Polling während Analyse für granulare Progress-Updates nach Refresh
