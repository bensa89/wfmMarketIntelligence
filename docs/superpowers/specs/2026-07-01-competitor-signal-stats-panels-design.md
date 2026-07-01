# Competitor Signal Stats Panels — Design Spec

## Überblick

Die Competitor-Detail-Ansicht (`CompetitorWorkspacePage.tsx`) zeigt aktuell Signals nur als paginierte Rohliste. Es fehlt ein schneller Überblick über:

- Wie viele Signals gibt es insgesamt im gewählten Zeitraum?
- Wie entwickelt sich das Signal-Aufkommen über die Zeit?
- Wie verteilen sich die Signals über die Kategorien (`signal_type`)?

Ziel: zwei neue Panels auf der Competitor-Workspace-Seite, die diese Fragen auf einen Blick beantworten, bevor man in die Rohdaten-Tabelle geht.

### Produktfragen

- Wie aktiv ist dieser Wettbewerber gerade in Bezug auf öffentlich sichtbare Signale?
- Nimmt die Signal-Aktivität zu oder ab?
- In welchen Kategorien (Product Update, Hiring, Partnership, ...) ist der Wettbewerber gerade am aktivsten?

---

## Architektur

**Ansatz: Neuer read-only Aggregations-Endpoint pro Company, on-demand berechnet (kein Caching/Persistierung)**

Analog zum bestehenden Muster in `intelligence.py` (`get_overview`, `get_competitor_workspace`), das bereits `func.count(...).group_by(...)` für Aggregationen nutzt. Kein neues DB-Modell nötig — die Aggregation läuft live über die `Signal`-Tabelle, gefiltert auf `company_id` und Zeitraum.

### Backend

**Neuer Endpoint:** `GET /intelligence/competitors/{slug}/signals/stats?days=30`

- `days` Query-Param: `30` oder `90` (spiegelt den bestehenden Zeitraum-Toggle der Seite; Default `30`)
- Company-Auflösung über `slug` wie bei `get_competitor_workspace`

**Datumsfeld:** `COALESCE(Signal.published_at, Signal.created_at)` für Zeitraumfilter und Timeline-Bucketing.

**Response-Shape:**

```json
{
  "total": 42,
  "period_days": 30,
  "granularity": "day",
  "timeline": [
    { "bucket": "2026-06-01", "count": 3 },
    { "bucket": "2026-06-02", "count": 0 },
    ...
  ],
  "by_category": [
    { "signal_type": "product_update", "count": 15 },
    { "signal_type": "hiring_signal", "count": 9 },
    ...
  ]
}
```

**Granularität (automatisch):**
- `days=30` → `granularity: "day"`, ein Bucket pro Kalendertag
- `days=90` → `granularity: "week"`, ein Bucket pro ISO-Kalenderwoche (Wochenstart als Bucket-Datum)

**Lückenlosigkeit:** Die Timeline wird serverseitig mit 0-Werten für Tage/Wochen ohne Signals aufgefüllt (kein Sparse-Array), damit das Frontend keine Lückenlogik braucht. Range: von `heute - days` bis `heute`.

**by_category:** Alle 8 `SignalType`-Werte werden zurückgegeben (auch mit `count: 0`), absteigend nach `count` sortiert, damit die Balkenreihenfolge stabil und vollständig ist.

**Implementierung:** Neue Funktion `get_competitor_signal_stats` in `backend/app/routers/intelligence.py`, zwei `func.count().group_by()`-Queries (eine für Timeline mit `date_trunc`, eine für Kategorie), gefiltert auf `Signal.company_id == company.id` und den Zeitraum.

### Frontend

**Neuer Hook:** `useCompetitorSignalStats(slug: string, days: 30 | 90)` in `frontend/src/hooks/useCompetitorSignalStats.ts`, analog zu bestehenden Hooks (z.B. `useCompetitorWorkspace`) — ruft den neuen Endpoint, liefert `{ data, isLoading, error }`.

**Neue Komponenten** in `frontend/src/components/workspace/`:

1. **`SignalTimelinePanel.tsx`**
   - Card-Styling: `bg-white border border-slate-200 rounded-xl p-4` (bestehendes Konventions-Pattern)
   - Header: Titel "Signal-Aktivität" + große Zahl `total` prominent daneben/darüber (z.B. "42 Signals in den letzten 30 Tagen")
   - Recharts `BarChart` (`ResponsiveContainer` + `Bar` + `XAxis` + `YAxis` + `Tooltip`), X-Achse = `bucket` (formatiert je nach `granularity`: `Tag.Monat` bei day, `KW n` bei week), Y-Achse = `count`
   - Empty-State (kein Signal im Zeitraum): Text `text-slate-400 text-[12px]`, kein leerer Chart

2. **`SignalCategoryPanel.tsx`**
   - Gleiches Card-Styling
   - Horizontales Recharts `BarChart` (`layout="vertical"`), eine Zeile je `signal_type`, sortiert nach `count` absteigend
   - Kategorie-Labels: bestehende Label-Mapping-Funktion wiederverwenden (dieselbe, die `SignalFeedTable`/`SignalFeedFilters` für lesbare `signal_type`-Namen nutzt — z.B. "Product Update" statt `product_update`); falls keine zentrale Mapping-Funktion existiert, wird sie bei der Implementierung lokalisiert und ggf. in eine gemeinsame Util ausgelagert
   - Kategorien mit `count: 0` werden ausgeblendet (nicht als leere Balken angezeigt)

**Platzierung:** Neue Row in `CompetitorWorkspacePage.tsx` direkt oberhalb der bestehenden Row 5 ("Signals"-Panel mit `SignalFeedFilters`/`SignalFeedTable`). Zwei-Spalten-Grid (`SignalTimelinePanel` links, `SignalCategoryPanel` rechts), gleiche Grid-Konventionen wie andere Zwei-Panel-Rows auf der Seite (z.B. Row 2).

**Zeitraum-Kopplung:** Beide Panels nutzen denselben `days`-State wie der bestehende 30d/90d-Toggle der Seite (kein eigener Switch). Wechselt der User den Toggle, refetchen beide Panels automatisch über den Hook.

**Neue Dependency:** `recharts` wird zu `frontend/package.json` hinzugefügt.

---

## Fehlerbehandlung

- Lädt der Stats-Endpoint (noch), zeigen beide Panels einen einfachen Loading-Skeleton/Platzhalter (bestehendes Loading-Pattern der Seite wiederverwenden, falls vorhanden)
- Schlägt der Request fehl, zeigen beide Panels eine kompakte Fehlermeldung im Card-Rahmen, ohne die restliche Seite zu blockieren (Panels sind unabhängig vom Rest der Workspace-Daten)
- Company ohne jegliche Signals im Zeitraum: `total: 0`, Timeline vollständig mit 0-Werten, `by_category` leer → beide Panels zeigen ihren jeweiligen Empty-State

---

## Testing

- Backend: neuer Test in `backend/tests/` für `get_competitor_signal_stats` — prüft Timeline-Lückenlosigkeit (Tage ohne Signal = 0), korrekte Granularität-Umschaltung bei `days=30` vs `days=90`, korrekte `by_category`-Sortierung inkl. Kategorien mit `count: 0`, und Datumsfeld-Fallback (`published_at` fehlt → `created_at` wird verwendet)
- Frontend: manuelle Verifikation über `/verify`-Skill nach Implementierung (Panels rendern korrekt bei Toggle-Wechsel, Empty-State, Fehlerfall)

---

## Out of Scope

- Keine Persistierung/Caching der Aggregation (immer live berechnet)
- Kein eigener Zeitraum-Switch nur für diese Panels
- Keine Drilldown-Interaktion (Klick auf Balken → gefilterte Signal-Liste) — kann später als Erweiterung ergänzt werden
- Keine Vergleichsansicht zwischen mehreren Wettbewerbern (nur Einzelansicht pro Competitor)
