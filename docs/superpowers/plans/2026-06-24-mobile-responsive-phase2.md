# Mobile Responsive Layout — Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend mobile responsiveness (started in `2026-06-12-mobile-responsive.md`, which covered the nav shell, Weekly Digest, Signals Feed, and Sources Admin) to the Dashboard and every remaining frontend page, so the app is usable on an iPhone 16 (393×852 CSS px, i.e. below Tailwind's `sm` 640px breakpoint).

**Architecture:** Mobile-first Tailwind: base classes target the iPhone 16 viewport, `sm:`/`md:`/`lg:` overrides restore the existing desktop layout. The hard rule from product: **side-by-side panels stack vertically on mobile instead of being squeezed into columns.** The one explicit exception is the Dashboard's Capability Heatmap, which is hidden entirely below `md` (table-grid visualization, not worth cramming onto a phone) — Top Movers takes the full width in its place. No other panel is dropped; everything else stacks.

**Tech Stack:** React 18, TypeScript, Tailwind CSS v3, lucide-react

## Global Constraints

- Target viewport: iPhone 16 portrait, 393px CSS width (verify in browser at 375px and 393px — 375px is the stricter floor, still supported by Tailwind's default `sm:` 640px breakpoint).
- Breakpoint convention already established in this codebase: base = mobile, `md:` (768px) = desktop. Reuse `md:` for panel stacking to stay consistent with `Layout.tsx`'s sidebar/header swap. Use `sm:` (640px) only for in-page grids that should still work on larger phones/small tablets before the full desktop layout kicks in (e.g. KPI tiles).
- No new dependencies. No component logic changes — these are Tailwind class changes only.
- Every task ends with a manual browser check at 375px/393px width (no automated visual regression suite exists in this repo) and a commit.

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/components/overview/DashboardKPIRow.tsx` | KPI grid responsive columns |
| `frontend/src/components/overview/RisksOpportunitiesPanel.tsx` | 3-col → stacked on mobile |
| `frontend/src/pages/DashboardPage.tsx` | Padding, stacked panel grids, hide heatmap on mobile |
| `frontend/src/pages/EventCalendarPage.tsx` | Padding |
| `frontend/src/pages/CompetitorWorkspacePage.tsx` | Header stacking, padding, 2-col rows → stacked |
| `frontend/src/components/workspace/RisksOpportunitiesCards.tsx` | 3-col → stacked on mobile |
| `frontend/src/pages/CompetitorListPage.tsx` | Padding, matrix header controls wrap |
| `frontend/src/pages/MarketTrendsPage.tsx` | Padding |
| `frontend/src/pages/CompanyContextPage.tsx` | Padding, header wrap |
| `frontend/src/pages/CrawlRunDetailPage.tsx` | Padding |
| `frontend/src/pages/SearchPage.tsx` | Header stacking, padding |
| `frontend/src/pages/LoginPage.tsx` | Outer padding safety margin |
| `frontend/src/pages/LogsAdminPage.tsx` | Padding, header wrap |
| `frontend/src/pages/LlmUsageAdminPage.tsx` | KPI grid responsive columns, padding |
| `frontend/src/pages/ScheduleAdminPage.tsx` | Padding, form grids → stacked |
| `frontend/src/pages/SettingsAdminPage.tsx` | Setting rows stack on mobile |

**Not modified (already responsive or auto-adapts):**
- `CapabilityStrengthVsMovement.tsx` — SVG scatter plot resizes its plot width via `ResizeObserver`, already degrades gracefully to its `300px` floor.
- `DimensionScoreGrid.tsx` — already `grid-cols-2 sm:grid-cols-3`.
- `CrawlRunDetailPage.tsx` stat grid — already `grid-cols-2 md:grid-cols-4` (only padding needs a touch).
- `MarketTrendsPage.tsx` / `CompanyContextPage.tsx` signal/content grids — already `grid-cols-1 lg:grid-cols-2` / `md:grid-cols-2` (only padding needs a touch).
- `FilterBar.tsx`, `SignalFeedFilters.tsx`, `SignalFeedTable.tsx`, `Layout.tsx`, `SourcesAdminPage.tsx`, `WeeklyDigestPage.tsx`, `SignalsFeedPage.tsx` — covered by the June 12 plan, no further changes here.

---

### Task 1: DashboardKPIRow.tsx — Responsive KPI grid

**Files:**
- Modify: `frontend/src/components/overview/DashboardKPIRow.tsx`

- [ ] **Step 1: Replace the fixed 4/8-column grid with a responsive one**

Find line 20:
```tsx
  return (
    <div className={`grid gap-4 mb-6 ${crawl_run ? 'grid-cols-8' : 'grid-cols-4'}`}>
```
Replace with:
```tsx
  return (
    <div className={`grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4 mb-6 ${crawl_run ? 'lg:grid-cols-8' : ''}`}>
```

This gives 2 cards per row on a phone (instead of 4 or 8 squeezed into one row), 4 per row from `sm:` up, and the original 8-wide layout only once there's `lg:` (1024px+) space.

- [ ] **Step 2: Verify in browser at 375px**

Open `/` (Dashboard). Expected: KPI tiles render as a 2-column grid, each tile readable (label + big number not clipped). At ≥640px: 4 columns. At ≥1024px (with an active crawl run showing 8 tiles): 8 columns as before.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/overview/DashboardKPIRow.tsx
git commit -m "fix: make Dashboard KPI row responsive on mobile"
```

---

### Task 2: RisksOpportunitiesPanel.tsx — Stack risk/opportunity/watchpoint columns

**Files:**
- Modify: `frontend/src/components/overview/RisksOpportunitiesPanel.tsx`

- [ ] **Step 1: Stack the 3 columns below `sm`**

Find line 76:
```tsx
    <div className="grid grid-cols-3 gap-4">
```
Replace with:
```tsx
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
```

- [ ] **Step 2: Verify in browser at 375px**

Open `/` (Dashboard), scroll to "Emerging Risks / Opportunities / Watchpoints". Expected: three colored cards stacked vertically, each full width. At ≥640px: 3 columns side by side as before.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/overview/RisksOpportunitiesPanel.tsx
git commit -m "fix: stack Risks/Opportunities/Watchpoints panel on mobile"
```

---

### Task 3: DashboardPage.tsx — Padding, stacked panel rows, hide heatmap on mobile

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Reduce header and content padding on mobile**

Find line 41:
```tsx
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
```
Replace with:
```tsx
      <div className="bg-white border-b border-slate-200 px-4 md:px-6 py-3 flex items-center justify-between flex-shrink-0">
```

Find line 67:
```tsx
      <div className="flex-1 overflow-auto px-6 py-5">
```
Replace with:
```tsx
      <div className="flex-1 overflow-auto px-4 md:px-6 py-5">
```

- [ ] **Step 2: Stack Market Shaping Feed + Event Timeline on mobile**

Find lines 88-98:
```tsx
        {overviewData && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <MarketShapingFeed
              signals7d={overviewData.recent_market_shaping_7d}
              signals30d={overviewData.recent_market_shaping_30d}
              signals90d={overviewData.recent_market_shaping_90d}
              onSelect={setSelectedOverviewSignal}
            />
            <EventTimelinePanel />
          </div>
        )}
```
Replace with:
```tsx
        {overviewData && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <MarketShapingFeed
              signals7d={overviewData.recent_market_shaping_7d}
              signals30d={overviewData.recent_market_shaping_30d}
              signals90d={overviewData.recent_market_shaping_90d}
              onSelect={setSelectedOverviewSignal}
            />
            <EventTimelinePanel />
          </div>
        )}
```

- [ ] **Step 3: Hide the Capability Heatmap on mobile, give Top Movers full width**

Find lines 100-109:
```tsx
        {overviewData && (
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="col-span-1">
              <TopMoversList movers7d={overviewData.top_movers_7d} movers30d={overviewData.top_movers_30d} />
            </div>
            <div className="col-span-2">
              <CapabilityHeatmapV2 rows7d={overviewData.capability_heatmap_7d} rows30d={overviewData.capability_heatmap_30d} />
            </div>
          </div>
        )}
```
Replace with:
```tsx
        {overviewData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="md:col-span-1">
              <TopMoversList movers7d={overviewData.top_movers_7d} movers30d={overviewData.top_movers_30d} />
            </div>
            {/* Capability Heatmap is a dense table visualization — not useful on a phone screen, hidden below md */}
            <div className="hidden md:block md:col-span-2">
              <CapabilityHeatmapV2 rows7d={overviewData.capability_heatmap_7d} rows30d={overviewData.capability_heatmap_30d} />
            </div>
          </div>
        )}
```

- [ ] **Step 4: Verify in browser at 375px**

Open `/` (Dashboard). Expected:
- Header padding tighter, title/button row still fits without horizontal scroll
- Market Shaping Feed and Event Timeline stacked vertically (Feed first, then Timeline)
- Top Movers list shown full-width; Capability Heatmap **not rendered at all**
- Risks/Opportunities/Watchpoints stacked (from Task 2)
- At ≥768px: both rows return to side-by-side, heatmap reappears next to Top Movers

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: make Dashboard responsive, hide capability heatmap on mobile"
```

---

### Task 4: EventCalendarPage.tsx — Mobile padding

**Files:**
- Modify: `frontend/src/pages/EventCalendarPage.tsx`

- [ ] **Step 1: Reduce padding on mobile**

Find lines 6 and 11:
```tsx
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex-shrink-0">
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Event-Kalender</h1>
        <p className="text-[12px] text-slate-500 mt-0.5">Alle Wettbewerber-Events</p>
      </div>

      <div className="flex-1 overflow-auto px-6 py-5">
```
Replace with:
```tsx
      <div className="bg-white border-b border-slate-200 px-4 md:px-6 py-3 flex-shrink-0">
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Event-Kalender</h1>
        <p className="text-[12px] text-slate-500 mt-0.5">Alle Wettbewerber-Events</p>
      </div>

      <div className="flex-1 overflow-auto px-4 md:px-6 py-5">
```

- [ ] **Step 2: Verify in browser at 375px**

Open `/events`. Expected: header and content have tighter side padding, `EventTimelinePanel` rows (already wrap-friendly, no change needed there) still display attendee chips without horizontal overflow.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/EventCalendarPage.tsx
git commit -m "fix: reduce Event Calendar page padding on mobile"
```

---

### Task 5: CompetitorWorkspacePage.tsx — Header stacking, padding, stacked rows

**Files:**
- Modify: `frontend/src/pages/CompetitorWorkspacePage.tsx`

- [ ] **Step 1: Let the header stack on mobile and reduce padding**

Find lines 83-84:
```tsx
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-start justify-between gap-4">
```
Replace with:
```tsx
      <div className="bg-white border-b border-slate-200 px-4 md:px-6 py-4 flex-shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4">
```

- [ ] **Step 2: Let the right-side control cluster take full width on mobile**

Find line 112:
```tsx
          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
```
Replace with:
```tsx
          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-start sm:justify-end">
```

This cluster (period selectors, scorecard period, refresh buttons) already has `flex-wrap`; on mobile it now starts left-aligned under the company name instead of being squeezed against it on the right.

- [ ] **Step 3: Reduce content padding**

Find line 197:
```tsx
      <div className="flex-1 overflow-auto px-6 py-5 space-y-5">
```
Replace with:
```tsx
      <div className="flex-1 overflow-auto px-4 md:px-6 py-5 space-y-5">
```

- [ ] **Step 4: Stack Row 1 (Strategic Posture + Dimension Scores)**

Find line 200:
```tsx
        <div className="grid grid-cols-2 gap-4">
          <StrategicPostureCard summary={activeSummary} />
```
Replace with:
```tsx
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StrategicPostureCard summary={activeSummary} />
```

- [ ] **Step 5: Stack Row 2 (Relative Capability Strength + Moves Panel)**

Find line 240:
```tsx
        <div className="grid grid-cols-2 gap-4">
          <RelativeCapabilityStrengthPanel
```
Replace with:
```tsx
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <RelativeCapabilityStrengthPanel
```

- [ ] **Step 6: Verify in browser at 375px**

Open any `/competitors/:slug` page. Expected:
- Header: logo+name block on top, control buttons (period selectors, scorecard period, crawl, refresh) wrapping below it, no horizontal scroll
- Strategic Posture card and Dimension Scores stacked vertically
- Relative Capability Strength and Moves Panel stacked vertically
- Capability Strength vs. Movement scatter plot still renders (already responsive via `ResizeObserver`)
- Risks/Opportunities/Watchpoints stacked (Task 6)
- Signals table shows mobile card view (from June 12 plan, unaffected)
- At ≥768px: both rows return to side-by-side, header returns to single row

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/CompetitorWorkspacePage.tsx
git commit -m "feat: make Competitor Workspace page responsive for mobile"
```

---

### Task 6: RisksOpportunitiesCards.tsx — Stack risk/opportunity/watchpoint columns

**Files:**
- Modify: `frontend/src/components/workspace/RisksOpportunitiesCards.tsx`

- [ ] **Step 1: Stack the 3 columns below `sm`**

Find line 72:
```tsx
    <div className="grid grid-cols-3 gap-4 mt-4">
```
Replace with:
```tsx
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
```

- [ ] **Step 2: Verify in browser at 375px**

Open a `/competitors/:slug` page, scroll to "Top Risks / Opportunities / Watchpoints". Expected: three cards stacked vertically. At ≥640px: 3 columns as before.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workspace/RisksOpportunitiesCards.tsx
git commit -m "fix: stack workspace Risks/Opportunities cards on mobile"
```

---

### Task 7: CompetitorListPage.tsx — Padding and matrix header controls

**Files:**
- Modify: `frontend/src/pages/CompetitorListPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 42:
```tsx
    <div className="p-6">
```
Replace with:
```tsx
    <div className="p-4 md:p-6">
```

- [ ] **Step 2: Let the Capability Strength Matrix header stack its controls**

Find lines 46-57:
```tsx
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-1.5">
            <h2 className="text-base font-semibold text-slate-900">Capability Strength Matrix</h2>
            <button
              onClick={() => setMatrixInfoOpen(true)}
              className="p-0.5 rounded hover:bg-slate-100 transition-colors"
              title="Legende & Erklärung"
            >
              <HelpCircle className="w-4 h-4 text-slate-400" />
            </button>
          </div>
          <div className="flex items-center gap-3">
```
Replace with:
```tsx
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <div className="flex items-center gap-1.5">
            <h2 className="text-base font-semibold text-slate-900">Capability Strength Matrix</h2>
            <button
              onClick={() => setMatrixInfoOpen(true)}
              className="p-0.5 rounded hover:bg-slate-100 transition-colors"
              title="Legende & Erklärung"
            >
              <HelpCircle className="w-4 h-4 text-slate-400" />
            </button>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
```

- [ ] **Step 3: Verify in browser at 375px**

Open `/competitors`. Expected:
- Title + period/recompute/scorecard controls stack vertically, controls wrap onto multiple lines instead of overflowing
- Matrix itself horizontally scrollable (already has `overflow-x-auto` on its wrapper)
- Competitor/Market Source cards already render in 1 column below `md` (existing `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`), no change needed there

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/CompetitorListPage.tsx
git commit -m "fix: make Competitor List page header responsive on mobile"
```

---

### Task 8: MarketTrendsPage.tsx — Mobile padding

**Files:**
- Modify: `frontend/src/pages/MarketTrendsPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 31:
```tsx
    <div className="p-6">
```
Replace with:
```tsx
    <div className="p-4 md:p-6">
```

- [ ] **Step 2: Verify in browser at 375px**

Open `/trends`. Expected: tighter side padding, `FilterBar` wraps its filter chips (already `flex flex-wrap`, no change needed), signal cards already stack 1-up below `lg` via existing `grid-cols-1 lg:grid-cols-2`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/MarketTrendsPage.tsx
git commit -m "fix: reduce Market Trends page padding on mobile"
```

---

### Task 9: CompanyContextPage.tsx — Padding and header wrap

**Files:**
- Modify: `frontend/src/pages/CompanyContextPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 74:
```tsx
    <div className="p-6">
```
Replace with:
```tsx
    <div className="p-4 md:p-6">
```

- [ ] **Step 2: Let the page header wrap on mobile**

Find lines 75-91:
```tsx
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Globe size={24} /> Company Context
        </h1>
        <div className="flex gap-2">
```
Replace with:
```tsx
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Globe size={24} /> Company Context
        </h1>
        <div className="flex gap-2">
```

- [ ] **Step 3: Let the "Außensicht" sub-header wrap on mobile too**

Find lines 162-176:
```tsx
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Eye size={20} /> Außensicht
          </h2>
          <button
            onClick={() => synthesize.mutate()}
            disabled={synthesize.isPending}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
```
Replace with:
```tsx
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Eye size={20} /> Außensicht
          </h2>
          <button
            onClick={() => synthesize.mutate()}
            disabled={synthesize.isPending}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
```

- [ ] **Step 4: Verify in browser at 375px**

Open `/context`. Expected: both header rows wrap their button below the title instead of squeezing; the two `grid-cols-1 md:grid-cols-2` content grids (company name/description, external view cards) already stack on mobile, no change needed there.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CompanyContextPage.tsx
git commit -m "fix: make Company Context page headers responsive on mobile"
```

---

### Task 10: CrawlRunDetailPage.tsx — Mobile padding

**Files:**
- Modify: `frontend/src/pages/CrawlRunDetailPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 65:
```tsx
    <div className="p-6 max-w-5xl mx-auto">
```
Replace with:
```tsx
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
```

- [ ] **Step 2: Verify in browser at 375px**

Open any `/crawl-runs/:id` page. Expected: tighter side padding; the stats grid (already `grid-cols-2 md:grid-cols-4`) shows 2 columns; source rows already wrap their timing labels via `flex gap-4` + `flex-wrap`-free text that truncates — confirm no row causes horizontal scroll (the `truncate` on the hostname span already handles long URLs).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/CrawlRunDetailPage.tsx
git commit -m "fix: reduce Crawl Run Detail page padding on mobile"
```

---

### Task 11: SearchPage.tsx — Header stacking and padding

**Files:**
- Modify: `frontend/src/pages/SearchPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 368:
```tsx
    <div className="p-6">
```
Replace with:
```tsx
    <div className="p-4 md:p-6">
```

- [ ] **Step 2: Let the page header wrap on mobile**

Find lines 369-382:
```tsx
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink">Web Search</h1>
          <p className="text-ink-muted text-sm mt-1">AI-driven search for news, reports, and new sources</p>
        </div>
        <button
          onClick={() => runSearch.mutate()}
          disabled={runSearch.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-accent-blue text-ink rounded hover:opacity-90 disabled:opacity-50 transition-opacity text-sm"
        >
          <Search size={16} />
          {runSearch.isPending ? 'Searching…' : 'Search Run starten'}
        </button>
      </div>
```
Replace with:
```tsx
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink">Web Search</h1>
          <p className="text-ink-muted text-sm mt-1">AI-driven search for news, reports, and new sources</p>
        </div>
        <button
          onClick={() => runSearch.mutate()}
          disabled={runSearch.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-accent-blue text-ink rounded hover:opacity-90 disabled:opacity-50 transition-opacity text-sm flex-shrink-0"
        >
          <Search size={16} />
          {runSearch.isPending ? 'Searching…' : 'Search Run starten'}
        </button>
      </div>
```

- [ ] **Step 3: Let candidate row action buttons wrap instead of overflowing**

Find lines 312-327 (inside `CandidatesTab`'s rendered candidate row):
```tsx
                  <div key={c.id} className="px-4 py-3 hover:bg-app-bg/30 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
```
Replace with:
```tsx
                  <div key={c.id} className="px-4 py-3 hover:bg-app-bg/30 transition-colors">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4">
                      <div className="flex-1 min-w-0">
```

- [ ] **Step 4: Verify in browser at 375px**

Open `/search`. Expected:
- "Web Search" title and "Search Run starten" button stack vertically
- Tab bar (Search Runs / Source Candidates) unaffected, already a simple row of two tabs that fits
- `CandidatesTab` filter row (already `flex flex-wrap`) wraps onto multiple lines
- Each candidate row: domain/status/snippet block above, Approve/Reject buttons below (stacked), instead of being squeezed to the right
- At ≥640px: header and candidate rows return to single-row layout

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SearchPage.tsx
git commit -m "fix: make Web Search page responsive on mobile"
```

---

### Task 12: LoginPage.tsx — Outer padding safety margin

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Add horizontal breathing room on very narrow screens**

Find line 42:
```tsx
    <div className="min-h-screen bg-app-bg flex items-center justify-center">
```
Replace with:
```tsx
    <div className="min-h-screen bg-app-bg flex items-center justify-center px-4">
```

- [ ] **Step 2: Verify in browser at 375px**

Open `/login`. Expected: the `max-w-sm` card no longer touches the viewport edges; form fields and the Sign In button remain full width inside the card.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "fix: add horizontal padding to Login page on narrow screens"
```

---

### Task 13: LogsAdminPage.tsx — Padding and header wrap

**Files:**
- Modify: `frontend/src/pages/LogsAdminPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 96:
```tsx
    <div className="p-6 max-w-full h-screen flex flex-col gap-4">
```
Replace with:
```tsx
    <div className="p-4 md:p-6 max-w-full h-screen flex flex-col gap-4">
```

- [ ] **Step 2: Let the header wrap on mobile**

Find lines 98-107:
```tsx
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Backend Logs</h1>
          <p className="text-sm text-slate-500 mt-0.5">Live-Stream aller Backend-Ereignisse</p>
        </div>
        <div className={`flex items-center gap-1.5 text-sm font-medium ${statusColor}`}>
          <Circle size={8} className="fill-current" />
          {statusLabel}
        </div>
      </div>
```
Replace with:
```tsx
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Backend Logs</h1>
          <p className="text-sm text-slate-500 mt-0.5">Live-Stream aller Backend-Ereignisse</p>
        </div>
        <div className={`flex items-center gap-1.5 text-sm font-medium ${statusColor}`}>
          <Circle size={8} className="fill-current" />
          {statusLabel}
        </div>
      </div>
```

- [ ] **Step 3: Verify in browser at 375px**

Open `/admin/logs`. Expected: title block and connection-status badge wrap onto separate lines if needed; the controls row (already `flex items-center gap-3 flex-wrap`) wraps level/module selects and action buttons across lines; log lines themselves already use `truncate`/`break-all` and won't force horizontal scroll on the container.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LogsAdminPage.tsx
git commit -m "fix: make Logs Admin page responsive on mobile"
```

---

### Task 14: LlmUsageAdminPage.tsx — Responsive KPI grid and padding

**Files:**
- Modify: `frontend/src/pages/LlmUsageAdminPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 171:
```tsx
    <div className="p-6 max-w-5xl space-y-6">
```
Replace with:
```tsx
    <div className="p-4 md:p-6 max-w-5xl space-y-6">
```

- [ ] **Step 2: Make the summary tiles grid responsive**

Find line 178:
```tsx
        <div className="grid grid-cols-4 gap-3">
```
Replace with:
```tsx
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
```

- [ ] **Step 3: Verify in browser at 375px**

Open `/admin/llm-usage`. Expected: "Heute / 7 Tage / 30 Tage / Gesamt" tiles render 2-per-row; the breakdown and price tables already have `overflow-x-auto` wrappers, confirm horizontal scroll works without affecting page layout.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LlmUsageAdminPage.tsx
git commit -m "fix: make LLM Usage Admin page responsive on mobile"
```

---

### Task 15: ScheduleAdminPage.tsx — Padding and form grid stacking

**Files:**
- Modify: `frontend/src/pages/ScheduleAdminPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 272:
```tsx
    <div className="p-8 max-w-2xl mx-auto space-y-6">
```
Replace with:
```tsx
    <div className="p-4 md:p-8 max-w-2xl mx-auto space-y-6">
```

- [ ] **Step 2: Stack the SMTP fields grid on mobile**

Find line 394:
```tsx
            <div className="grid grid-cols-2 gap-3">
```
Replace with:
```tsx
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
```

- [ ] **Step 3: Stack the Re-Analyse fields grid on mobile**

Find line 468:
```tsx
        <div className="grid grid-cols-3 gap-3">
```
Replace with:
```tsx
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
```

- [ ] **Step 4: Verify in browser at 375px**

Open `/admin/schedule`. Expected: section cards already full width (`max-w-2xl` container); SMTP fields (Host/Port/Sender/Username/Password) stack one per row; Re-Analyse fields (Tage/Competitor/Signal-Typ) stack one per row; `DayPicker` (7 fixed `w-9` buttons) fits on 375px without wrapping (7×36px + gaps ≈ 280px, within the `max-w-2xl` minus padding).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ScheduleAdminPage.tsx
git commit -m "fix: make Schedule Admin page forms responsive on mobile"
```

---

### Task 16: SettingsAdminPage.tsx — Setting rows stack on mobile

**Files:**
- Modify: `frontend/src/pages/SettingsAdminPage.tsx`

- [ ] **Step 1: Reduce outer padding**

Find line 163:
```tsx
    <div className="p-6 max-w-3xl space-y-6">
```
Replace with:
```tsx
    <div className="p-4 md:p-6 max-w-3xl space-y-6">
```

- [ ] **Step 2: Let each setting row stack its label and control on mobile**

Find line 70:
```tsx
    <div className="flex items-center gap-3 py-2.5 border-b border-slate-100 last:border-b-0">
```
Replace with:
```tsx
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 py-2.5 border-b border-slate-100 last:border-b-0">
```

This row contains a label block (`flex-1`), a select/input control, and Save/Reset icon buttons. On mobile it now stacks: label+default-value on top, then the control and action buttons on their own row (the control and buttons are small enough — `w-24`/`w-28`/`w-56` inputs plus two `p-1.5` icon buttons — to stay on one line under the label at 375px width).

- [ ] **Step 3: Verify in browser at 375px**

Open `/admin/settings`. Expected: each setting row shows the label + "Default: …" text on its own line, with the select/input/number field and Save/Reset buttons on the line below, left-aligned. At ≥640px: label and control return to a single row.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SettingsAdminPage.tsx
git commit -m "fix: stack Settings Admin rows on mobile"
```
