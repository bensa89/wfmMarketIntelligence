# Dashboard Watchpoints & Signal-Links Design

**Date:** 2026-06-15  
**Status:** Approved

## Summary

Extend the Dashboard's Risks/Opportunities panel to:
1. Add a third **Watchpoints** column (cross-competitor, aggregated from 30d CompetitorSummary records)
2. Upgrade Risks and Opportunities from plain strings to rich `RiskItem` objects — with **NEW badges**, **company attribution** (logo + name), and **clickable signal links** that open the existing signal modal

Pattern source: `RisksOpportunitiesCards` on competitor detail page (`/competitors/:slug`)

---

## 1. Backend — `GET /api/intelligence/overview`

**File:** `backend/app/routers/intelligence.py`

### Change

In `get_overview()`, the aggregation loop over `companies_with_summaries` currently strips `RiskItem` objects to plain strings. Instead, build rich dicts:

```python
OverviewRiskItem = {
    "text": str,
    "signal_ids": list[str],   # preserved from CompetitorSummary RiskItem
    "is_new": bool,            # preserved from CompetitorSummary RiskItem
    "company_id": str,
    "company_name": str,
    "company_slug": str,
}
```

- Build `emerging_risks`, `emerging_opportunities`, `emerging_watchpoints` as `list[OverviewRiskItem]`
- Deduplication by `text` (case-insensitive, first occurrence wins — keeps company attribution of earliest)
- Max 10 items each
- `watchpoints` sourced from `CompetitorSummary.watchpoints` (same 30d latest per company)

### Return shape (additions/changes)

```json
{
  "emerging_risks": [OverviewRiskItem, ...],
  "emerging_opportunities": [OverviewRiskItem, ...],
  "emerging_watchpoints": [OverviewRiskItem, ...]
}
```

No new models or migrations needed.

---

## 2. Frontend Types — `intelligence.ts`

**File:** `frontend/src/types/intelligence.ts`

### `RiskItem` — add optional fields

```ts
export interface RiskItem {
  text: string;
  signal_ids?: string[];
  is_new?: boolean;
  company_id?: string;
  company_name?: string;
  company_slug?: string;
}
```

### `OverviewResponse` — upgrade fields

```ts
export interface OverviewResponse {
  // ...existing fields...
  emerging_risks: RiskItem[];           // was: string[]
  emerging_opportunities: RiskItem[];   // was: string[]
  emerging_watchpoints: RiskItem[];     // new
}
```

---

## 3. Frontend Component — `RisksOpportunitiesPanel`

**File:** `frontend/src/components/overview/RisksOpportunitiesPanel.tsx`

### Props

```ts
interface Props {
  risks: RiskItem[];
  opportunities: RiskItem[];
  watchpoints: RiskItem[];
  onSelectSignal?: (signalId: string) => void;
}
```

### Layout

3-column grid (was 2-column): **Risks (red)** | **Opportunities (green)** | **Watchpoints (amber)**

### Per-item rendering

Reuses the `CitedItemList` pattern from `RisksOpportunitiesCards`:
- Clickable when `signal_ids?.[0]` exists → calls `onSelectSignal(firstSignalId)`
- NEW badge when `is_new === true`
- `+N` indicator when `signal_ids.length > 1`

### Company attribution

Below each item text, when `company_name` is present:
```
[CompanyLogo slug=company_slug size=12] company_name
```
Rendered as a subdued line (`text-[10px] text-slate-400`) underneath the item text.

---

## 4. Dashboard Page

**File:** `frontend/src/pages/Dashboard.tsx`

### Changes

- Import `ScorecardSignalDrawer` from `components/scorecard/ScorecardSignalDrawer`
- Add state: `const [selectedRiskSignalId, setSelectedRiskSignalId] = useState<string | null>(null)`
- Pass to panel:
  ```tsx
  <RisksOpportunitiesPanel
    risks={overviewData.emerging_risks}
    opportunities={overviewData.emerging_opportunities}
    watchpoints={overviewData.emerging_watchpoints}
    onSelectSignal={setSelectedRiskSignalId}
  />
  ```
- Render modal:
  ```tsx
  <ScorecardSignalDrawer
    signalId={selectedRiskSignalId}
    onClose={() => setSelectedRiskSignalId(null)}
  />
  ```

---

## Out of scope

- No changes to the competitor workspace page
- No new API endpoints
- No database migrations
- No changes to how `CompetitorSummary` is generated or stored
