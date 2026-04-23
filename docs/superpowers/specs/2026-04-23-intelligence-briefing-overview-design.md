# Intelligence Briefing für Overview — Design

**Datum:** 2026-04-23  
**Status:** Approved

## Ziel

Ein LLM-generiertes, persistiertes Briefing auf der Overview-Seite, das auf Assessments und Signals basiert und sich auf Veränderungen seit dem letzten Crawl konzentriert. Zwei Fokusebenen: strategischer Überblick + operative Handlungsempfehlungen.

## Backend

### Neues Modell: `IntelligenceBriefing`

`backend/app/models/intelligence_briefing.py`

Felder:
- `id` — UUID String PK
- `content` — Text (Markdown)
- `signal_count` — Integer (Anzahl Signals im Briefing-Zeitraum)
- `assessment_count` — Integer (Anzahl Assessments im Briefing-Zeitraum)
- `generated_at` — DateTime UTC

Alembic-Migration erforderlich.

### Generator: `backend/app/assessor/intel_briefing.py`

Funktion `generate_intelligence_briefing(db: Session) -> str`

**Datenbasis:**
- "Letzter Crawl" = Signals mit `created_at >= now - 24h` (Heuristik für den jüngsten Crawl-Batch)
- Zugehörige `SignalAssessment`-Datensätze per JOIN
- `InternalCompanyContext` für Unternehmenskontext

**Prompt-Struktur (auf Deutsch):**
1. Metadaten: Zeitraum, Anzahl Signale, Anzahl Assessments, beteiligte Unternehmen
2. Top-Bewegungen: Assessments mit `movement_strength = market_shaping` oder `strong`, sortiert nach `movement_score desc`
3. Capability-Verschiebungen: welche `capability_primary` tauchen neu/häufig auf
4. `implication_for_us` der Top-5-Assessments

**Ausgabe:** Strukturiertes Markdown mit zwei Abschnitten:
- `## Strategischer Überblick` — 2–3 Sätze zu den wichtigsten Bewegungen
- `## Handlungsempfehlungen` — Markdown-Tabelle (Priorität | Signal | Unternehmen | Empfehlung)

`max_tokens=2048`

### Endpoints: `backend/app/routers/intelligence_briefing.py`

Router unter `/api/intelligence/briefing/`:

| Method | Path | Beschreibung |
|--------|------|--------------|
| GET | `/latest` | Neuestes Briefing oder 404 |
| POST | `/generate` | Generiert neu, persistiert, gibt zurück |

Router in `backend/app/main.py` einbinden unter `/api/intelligence/briefing`.

### Schema: `backend/app/schemas/intelligence_briefing.py`

`IntelligenceBriefingRead`: `id`, `content`, `signal_count`, `assessment_count`, `generated_at`

## Frontend

### Neuer Hook: `useIntelligenceBriefing.ts`

`frontend/src/hooks/useIntelligenceBriefing.ts`

- `useLatestIntelligenceBriefing()` — GET `/intelligence/briefing/latest`, 404 → `null`
- `useGenerateIntelligenceBriefing()` — POST `/intelligence/briefing/generate`, invalidiert Query on success

### Neue Komponente: `IntelligenceBriefingPanel`

`frontend/src/components/overview/IntelligenceBriefingPanel.tsx`

Visuell identisch zu `BriefingPanel`:
- Header: Label "Intelligence Briefing", Zeitstempel (relativ + absolut), Refresh-Button mit Spinner
- Body: `<MarkdownViewer>` für den Markdown-Content
- States: Loading, kein Briefing vorhanden (mit Hinweis), Error bei Generierung (inline unter Button)

### Integration in `OverviewPage.tsx`

`IntelligenceBriefingPanel` als erstes Element innerhalb des scrollbaren Bereichs, vor `OverviewKPIBar`.

## Datenbankmigrationen

Eine neue Alembic-Migration: Tabelle `intelligence_briefings`.
