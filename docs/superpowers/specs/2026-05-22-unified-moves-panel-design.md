# Unified Moves Panel — Design Spec

**Date:** 2026-05-22  
**Status:** Approved  
**Scope:** `CompetitorWorkspacePage` only

---

## Problem

The competitor workspace currently shows two separate panels for move intelligence:

- **TopMovesTimeline** (Row 2, half-width): scorecard-curated top moves for the selected period (30d/90d), ranked by `movement_score`
- **RecentMovesTimeline** (Row 5, full-width): raw chronological feed of `recent_assessments`, up to 15 items

Users cannot easily tell which assessments are new. The two panels are redundant in intent and split attention.

---

## Goal

Unify both panels into one `MovesPanel` component with two tabs, placed in Row 2 (half-width, next to `RelativeCapabilityStrengthPanel`). Users can immediately see new assessments and navigate between a chronological view and a score-ranked view.

---

## New Component: `MovesPanel`

**File:** `frontend/src/components/workspace/MovesPanel.tsx`

### Props

```tsx
interface MovesPanelProps {
  recentAssessments: SignalFeedItem[];
  topMoves: ScorecardTopMove[] | null | undefined;
  loading?: boolean;
  onSelectSignal: (signalId: string) => void;
  onSelectRecentSignal: (item: SignalFeedItem) => void;
}
```

### Tab 1 — Recent Moves

- **Data source:** `recentAssessments` (`SignalFeedItem[]`) from `data.recent_assessments`
- **Sort:** `published_at || created_at` descending
- **"New" badge:** The 3 newest items get a small green "New" pill — purely date-based, no tracking
- **Per-item display:** title (2-line clamp), capability label, relative timestamp, `MovementBadge` + `ScoreBadge`
- **Click:** calls `onSelectRecentSignal(item)` → opens `SignalDetailDrawer`

### Tab 2 — Top Moves

- **Data source:** `topMoves` (`ScorecardTopMove[]`) from `scorecard?.top_moves`
- **Sort:** `movement_score` descending (already sorted by backend)
- **Loading state:** skeleton (same as current `TopMovesTimeline`)
- **Per-item display:** title (2-line clamp), `signal_class` label, `assessed_at` relative timestamp, `ScoreBadge`
- **Click:** calls `onSelectSignal(signalId)` → opens `ScorecardSignalDrawer`

### Tab Bar

- Two tab buttons: "Recent" | "Top Moves"
- Default active tab: "Recent"
- Tab indicator: indigo underline (matches existing tab style in app)

---

## Layout Changes in `CompetitorWorkspacePage`

| Before | After |
|---|---|
| Row 2: `RelativeCapabilityStrengthPanel` + `TopMovesTimeline` | Row 2: `RelativeCapabilityStrengthPanel` + `MovesPanel` |
| Row 5: `RecentMovesTimeline` | Row 5: removed |

- `TopMovesTimeline` import removed from `CompetitorWorkspacePage`
- `RecentMovesTimeline` import removed from `CompetitorWorkspacePage`
- `selectedSignal` state and `SignalDetailDrawer` remain — now fed via `onSelectRecentSignal`

---

## Files Touched

| File | Change |
|---|---|
| `frontend/src/components/workspace/MovesPanel.tsx` | **New** |
| `frontend/src/pages/CompetitorWorkspacePage.tsx` | Replace `TopMovesTimeline` → `MovesPanel`, remove `RecentMovesTimeline` from Row 5 |
| `frontend/src/components/workspace/RecentMovesTimeline.tsx` | No change (kept, unused) |
| `frontend/src/components/scorecard/TopMovesTimeline.tsx` | No change (still used in `CompetitorDetail.tsx`) |

---

## Out of Scope

- `CompetitorDetail.tsx` — still uses `TopMovesTimeline` standalone; not changed
- "Seen/unread" tracking — not needed; "New" is purely the 3 newest by date
- Period-filter on Recent tab — always shows all recent moves regardless of 30d/90d selector
