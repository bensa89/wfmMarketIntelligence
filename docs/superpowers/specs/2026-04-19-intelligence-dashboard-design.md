# Intelligence Dashboard Redesign — Design Spec

## Goal

Redesign the existing Dashboard from a simple KPI + table view into an Intelligence Dashboard that lets users understand in 10-20 seconds:
- What is new since the last crawl
- Which signals are most relevant now
- Where the most activity is happening (by competitor, by signal type)
- What trends and peaks are emerging over time

## Design Principles

- Nüchtern, funktional, datendicht — Enterprise/Analysten-UI, not marketing landingpage
- High information density with good scannability
- Most important information above the fold
- Overview first, details below
- Existing signal table preserved as working view, embedded in clearer dashboard structure
- Color only where semantically meaningful
- **Light theme as primary design** — main content area uses light backgrounds (white/gray), clean borders, dark text on light surfaces. The existing dark sidebar remains, but all dashboard content areas are light theme.
- Consistent with existing UI language (sidebar dark, content light, Tailwind classes)

## Layout Architecture

**Two-Column layout** with full-width KPI band above:

```
┌──────────────────────────────────────────────────┐
│  Topbar: Dashboard title + Crawl status + Button  │
├──────────────────────────────────────────────────┤
│  KPI Band (8 cards, full width)                   │
├────────────────────┬─────────────────────────────┤
│  Intelligence      │  Signal Feed                  │
│  Panel (~40%)      │  (~60%)                       │
│                    │                               │
│  1. Crawl Summary  │  FilterBar                    │
│  2. Top New Signals│  Signal Table                  │
│  3. Signals Chart  │  (with NEW/UPDATED badges)      │
│  4. Typ + Heatmap │                               │
│                    │                               │
└────────────────────┴─────────────────────────────┘
```

### Topbar
- Title: "Dashboard"
- Subtitle: Last crawl timestamp + summary ("Letzter Crawl: heute 14:32 — 8 Quellen, 3 neue Dokumente, 5 neue Signale")
- Active crawl banner (from `useActiveCrawlRun` hook, already implemented)
- "Crawl starten" button (existing)

### KPI Band (8 cards, full width)
Responsive grid: 8 columns on desktop, 4 columns on tablet, 2 on mobile.

| # | Label | Color | Value | Delta |
|---|-------|-------|-------|-------|
| 1 | Signale gesamt | blue | total signals | +N seit letztem Crawl |
| 2 | Hohe Relevanz | green | signals ≥ 0.7 | +N neu |
| 3 | Wettbewerber | amber | competitor companies count | — |
| 4 | Neue Signale | purple | signals since last crawl | "seit letztem Crawl" |
| 5 | Neue Dokumente | cyan | documents since last crawl | "seit letztem Crawl" |
| 6 | Source Candidates | pink | candidates count | N ungeprüft |
| 7 | Discovered Pages | orange | discovered pages count | N neu |
| 8 | Fehler letzter Crawl | red | errors from last crawl | "✓ Alle erfolgreich" or count |

Each card: top accent bar, small uppercase label, large number, small delta line.

### Left Panel: Intelligence Overview (~40%)

**1. Crawl Summary ("Seit letztem Crawl")**
- Compact 2×2 grid: Neue Signale, Geändert, Neue Dokumente, Candidates
- Green left border accent
- Data source: `GET /api/crawl-runs/?status=completed` (most recent) + `GET /api/signals` filtered by `created_at` after last crawl

**2. Top Neue Signale**
- 5 most recent signals with relevance ≥ 0.5, ordered by relevance_score desc + created_at desc
- Each row: NEW/UPDATED badge, SignalTypeIcon, title, relevance percentage
- Background highlight for NEW signals
- Data source: `GET /api/signals` + filter by `created_at` after last crawl run

**3. Signale über Zeit (Line Chart)**
- Recharts `LineChart` with one line per company
- X-axis: last 14 days, Y-axis: signal count
- Peak annotation at highest values
- Consistent company colors across chart + heatmap
- Time range selector: 7d / 14d / 30d (default: 14d)
- Data source: New endpoint `GET /api/signals/stats/over-time?days=14` or client-side aggregation from signals list

**4. Typ-Verteilung + Heatmap (side-by-side)**
- Left half: Horizontal bar chart showing signal type distribution
- Right half: Compact heatmap matrix: rows = companies, columns = signal types, cell color intensity = count
- Data source: client-side aggregation from signals, or `GET /api/signals/stats/distribution`

### Right Panel: Signal Feed (~60%)

**FilterBar** (existing, enhanced):
- Company filter (dropdown)
- Signal type filter (pills)
- Relevance filter (pills)
- New filter: "Nur Neue" toggle (shows only signals since last crawl)
- New filter: Origin (crawl/search) — optional, if data available

**Signal Table** (existing, enhanced):
- New column: badge column at far left
  - `NEW` badge (green) for signals created since last crawl
  - `UPD` badge (amber) for signals whose document changed since last crawl
- Signal type uses existing `SignalTypeIcon` chip
- Company dot color consistent with chart colors
- Date formatted as DD.MM
- Relevance bar as existing `RelevanceBadge` variant="bar"
- Optional: 1-line `why_it_matters` preview on hover or as truncated subtitle

Badge logic:
- Signal is "NEW" if `signal.created_at` > last completed CrawlRun's `started_at`
- Signal is "UPD" if its document's `crawled_at` > last CrawlRun's `started_at` AND signal is not NEW
- Requires: last crawl run timestamp from `GET /api/crawl-runs/?status=completed&limit=1`

## New Backend Endpoints

### `GET /api/crawl-runs/`
Already planned in persistent-crawl-status design. Returns list of CrawlRun with:
- `id`, `status`, `started_at`, `finished_at`, `total_sources`, `total_new`, `total_skipped`, `total_errors`

Query params: `status`, `limit`, `offset`

### `GET /api/signals/stats/over-time`
Returns time series data for signals per company per day.

```
GET /api/signals/stats/over-time?days=14

Response:
[
  { "date": "2026-04-05", "company_id": "...", "company_name": "SAP", "count": 3 },
  { "date": "2026-04-05", "company_id": "...", "company_name": "Salesforce", "count": 5 },
  ...
]
```

### `GET /api/signals/stats/distribution`
Returns signal type distribution and company × type matrix.

```
GET /api/signals/stats/distribution

Response:
{
  "by_type": [
    { "signal_type": "ai_announcement", "count": 38 },
    ...
  ],
  "by_company_and_type": [
    { "company_id": "...", "company_name": "SAP", "signal_type": "ai_announcement", "count": 5 },
    ...
  ]
}
```

### `GET /api/source-candidates/` (enhanced)
Already exists. Add `status=candidate` filter support to get unreviewed candidates count for KPI.

### `GET /api/discovered-pages/stats`
Returns global discovered pages count (the existing endpoint requires `source_id`, which doesn't work for a dashboard KPI).

```
GET /api/discovered-pages/stats

Response:
{ "total": 23, "new": 5, "changed": 2, "known": 16 }
```

### `GET /api/signals` (enhanced)
Add optional query params:
- `since`: ISO timestamp to filter signals created after this date (for NEW badge logic)
- `is_new`: boolean filter for signals created since last crawl

Alternatively, the frontend can fetch all signals and compute this client-side using the last CrawlRun timestamp.

## New Frontend Components

### `DeltaKpiCard`
Extends current `KpiCard`. Props: label, value, delta (string), color, trendDirection ("up"|"down"|"neutral").

### `CrawlSummaryCard`
Compact card showing changes since last crawl. 2×2 grid of stats.

### `TopSignalsPanel`
Shows top 5 new/updated signals. Props: signals[], lastCrawlStartedAt.

### `SignalsOverTimeChart`
Recharts `LineChart`. Props: timeSeriesData (date + company + count), companies (for color mapping), days (7|14|30).

### `CompanyColorMap`
Utility: deterministic color assignment per company ID. Colors: `['#7c3aed', '#2563eb', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4']`. Used consistently in chart, heatmap, and signal table.

### `SignalTypeDistribution`
Horizontal bar chart showing signal type distribution. Client-side aggregation or from stats endpoint.

### `CompanySignalHeatmap`
Compact HTML/CSS matrix (not a chart library). Rows = companies, columns = signal types, cell color intensity based on count.

### `SignalFeedTable`
The existing signal table, enhanced with NEW/UPD badge column.

## New Frontend Hooks

### `useCrawlRuns()`
Fetches `GET /api/crawl-runs/?status=completed&limit=1`. Returns most recent completed crawl run for delta calculations.

### `useSignalStats()`
Fetches `GET /api/signals/stats/distribution` and `GET /api/signals/stats/over-time?days=14`. Returns distribution data and time series.

### `useSourceCandidates()`
Fetches `GET /api/source-candidates/?status=candidate`. Returns count for KPI.

### `useDiscoveredPagesStats()`
Fetches `GET /api/discovered-pages/stats`. Returns total/new/changed/known counts for KPI.

### `useSignalBadges(lastCrawlStartedAt)`
Utility hook that takes the last crawl start timestamp and returns a function `getBadge(signal)` that returns "NEW" | "UPD" | null.

## Data Flow

```
Page Load
  ├─ useSignals({}) → all signals
  ├─ useCrawlRuns({ status: 'completed', limit: 1 }) → last completed crawl
  ├─ useCrawlRuns({ status: 'running' }) → active crawl (for banner)
  ├─ useSignalStats() → distribution + time series
  ├─ useSourceCandidates({ status: 'candidate' }) → candidate count
  ├─ useDiscoveredPages() → page counts
  └─ useCompanies() → company list + colors

Computed:
  ├─ new signals = signals where created_at > lastCrawl.started_at
  ├─ updated signals = signals where document.crawled_at > lastCrawl.started_at && !new
  ├─ KPI deltas = derived from new/updated counts
  └─ badge assignment = per signal based on lastCrawl.started_at
```

## Color Scheme — Light Theme

The dashboard content area uses a **light theme**. The existing dark sidebar (#0f172a) remains unchanged.

**Content area palette:**
- Background: `#f8fafc` (slate-50, matches existing `app-bg`)
- Card background: `#ffffff` (white)
- Card border: `#e2e8f0` (slate-200)
- Primary text: `#0f172a` (slate-900)
- Secondary text: `#475569` (slate-600)
- Muted text: `#94a3b8` (slate-400)
- Accent blue: `#2563eb` (existing)
- Accent borders on KPI cards: colored top borders on white cards
- Badges: colored backgrounds with matching text (same colors as existing SignalTypeIcon)
- NEW badge: `#dcfce7` bg / `#15803d` text (green-200/700)
- UPD badge: `#fef3c7` bg / `#92400e` text (amber-200/800)
- Heatmap cells: gradient from `#f1f5f9` (0) through `#dbeafe` (low) to `#1e3a8a` (high)
- Chart lines: consistent company colors on white background
- Relevance bars: same color logic (green ≥0.7, amber ≥0.4, red <0.4)

- **Desktop (≥1280px):** 8 KPI columns, 40/60 two-column layout
- **Tablet (768-1279px):** 4 KPI columns (2 rows), single column (intelligence panel above feed)
- **Mobile (<768px):** 2 KPI columns (4 rows), single column, charts full width, table horizontally scrollable

## Dependencies

- **Recharts** — new npm dependency for `LineChart`
- **No other new dependencies** — all other components use existing Tailwind + Lucide icons

## Out of Scope

- Per-source crawl history page
- WebSocket (SSE is sufficient)
- Automatic old-run cleanup cron
- Signal detail page / drill-down (signals link to competitors page as before)
- Search/filter integration with charts (charts reflect global state, not filtered state)
- Drag-and-drop widget arrangement
- Dark mode (light theme only for now)