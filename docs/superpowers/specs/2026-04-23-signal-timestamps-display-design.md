# Signal Timestamps Display — Design

**Date:** 2026-04-23  
**Status:** Approved

## Goal

Show both the source article publication date and the signal analysis date in the Signal Feed and Signal Detail Drawer, so users can distinguish between when something was published and when it was assessed.

## Data Available

Both timestamps are already present in `SignalFeedItem`:
- `published_at: string | null` — article publication date (from `signal.published_at`)
- `created_at: string` — when the signal was created/analysed (always present)
- `assessment.created_at` — when the assessment was generated (available if assessed)

## New Components & Utilities

### `DateWithTooltip` (`frontend/src/components/DateWithTooltip.tsx`)
- Props: `date: string | null`, optional `label?: string`
- Renders relative date text (`formatDistanceToNow`) with a styled Tailwind hover tooltip showing the absolute date (`formatAbsolute`)
- If `date` is null: renders `"–"` with no tooltip
- Reusable across the app

### `formatAbsolute` in `frontend/src/utils/dates.ts`
- New function alongside existing `formatDistanceToNow`
- Returns `"19. Apr 2026, 14:32"` using `de-DE` locale
- Returns `"–"` if date is null or invalid

## Signal Feed Table (`SignalFeedTable.tsx`)

The current single "Date" column (`published_at || created_at`, no distinction) becomes a stacked single column:

```
Datum
──────────────────────
3 days ago            ← article published_at (DateWithTooltip), omitted if null
analysiert: 5 days ago ← signal created_at (DateWithTooltip), smaller/dimmed
```

- Column header stays: `"Datum"`
- Article date: normal weight, `text-slate-600`
- "Analysiert" line: `text-[11px] text-slate-400 mt-0.5`, prefixed with `"analysiert: "`
- Both wrapped in `DateWithTooltip`

## Signal Detail Drawer (`SignalDetailDrawer.tsx`)

The header currently shows one date line (`published_at || created_at`). Replace with:

```
Competitor Name  ·  Artikel: 3 days ago  ·  Analysiert: 5 days ago
```

- Each date is a `DateWithTooltip` inline span with a short label prefix
- If `published_at` is null: the "Artikel" entry is omitted entirely
- Separator `·` between items, consistent with existing style

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/utils/dates.ts` | Add `formatAbsolute` |
| `frontend/src/components/DateWithTooltip.tsx` | New component |
| `frontend/src/components/signals/SignalFeedTable.tsx` | Replace Date column with stacked version |
| `frontend/src/components/signals/SignalDetailDrawer.tsx` | Update header date display |

No backend changes required — all data is already returned by the API.
