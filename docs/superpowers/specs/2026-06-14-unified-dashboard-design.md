# Unified Dashboard Design

**Date:** 2026-06-14  
**Status:** Approved  
**Route:** `/` (replaces current Dashboard.tsx content)  
**Scope:** Merge `/overview` panels into `/`, keep `/overview` route untouched

---

## Goal

Replace the current `Dashboard.tsx` (`/`) with a unified page that puts the strategic overview (KPIs, KI-Briefing, competitors, risks/opportunities) at the top, followed by the existing operational signal panels below. The primary use case is a quick daily check: KPIs and KI-Briefing at a glance, without needing to navigate between two pages.

---

## Layout

### Zone 1 — Übersicht (top)

Panels imported from `OverviewPage` / overview components. Rendered in this order:

1. **IntelligenceBriefingPanel** — full width
2. **Merged KPI bar** — full width (see KPI Merge section below)
3. **3-col grid:**
   - col 1: `TopMoversList`
   - col 2–3: `CapabilityHeatmapV2`
4. **2-col grid:**
   - col 1: `MarketShapingFeed`
   - col 2: `RisksOpportunitiesPanel`
5. **EventTimelinePanel** — full width

### Visual Separator

A dashed divider with label "Signal Details & Analyse" separates the two zones. No interactivity — purely visual.

### Zone 2 — Signal Details (bottom)

Existing `Dashboard.tsx` panels, unchanged, in their current order:

1. Crawl-Trigger button
2. `TopSignalsPanel` + `SignalsOverTimeChart` (2-col layout)
3. `SignalTypeDistribution` + `CompanySignalHeatmap`
4. `FilterBar` + `SignalFeedTable`

---

## KPI Merge

`OverviewKPIBar` (from `useOverview()`) and `DeltaKpiCards` (from individual signal hooks) are **merged into a single row**. The existing `OverviewKPIBar` component is kept as-is. `DeltaKpiCards` is removed.

If `OverviewKPIBar` is missing metrics that `DeltaKpiCards` uniquely surfaced (e.g. "neue seit letztem Crawl", "Kandidaten"), those metrics are added to `OverviewKPIBar` or displayed as supplementary chips beside it — whichever requires less new code.

---

## Removed Components

These two components are removed from `Dashboard.tsx` (replaced by their overview equivalents above):

| Removed | Replaced by |
|---|---|
| `BriefingPanel` | `IntelligenceBriefingPanel` |
| `DeltaKpiCards` | Merged into `OverviewKPIBar` |

---

## Data Dependencies

Zone 1 requires `useOverview()` hook (already used in `OverviewPage`). Dashboard.tsx must import and call this hook in addition to its existing hooks.

All other data hooks remain unchanged.

---

## What Does NOT Change

- `/overview` route and `OverviewPage.tsx` — untouched
- All Zone 2 components — no logic or prop changes
- Sidebar navigation — no changes
- `FilterBar`, `SignalFeedTable` filtering logic — unchanged
- Auth, routing, Layout — unchanged

---

## Out of Scope

- Redesigning individual panels
- Adding new data to `useOverview()`
- Mobile/responsive changes beyond what already exists
- Removing `/overview` from the sidebar
