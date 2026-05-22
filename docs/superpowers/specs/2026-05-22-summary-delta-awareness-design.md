# Summary Delta Awareness — Design Spec

**Date:** 2026-05-22
**Status:** Ready for implementation

---

## Problem

After clicking "Refresh" on the Competitor Workspace page, the Top Risks, Opportunities, and Watchpoints panels replace their content silently. The user cannot tell which items are new threats/opportunities that emerged since the last analysis, and which are ongoing concerns that have persisted. The same blind spot exists in the strategic posture text.

---

## Goal

When a new `CompetitorSummary` is generated, the LLM compares it to the previous one and:
1. Flags each risk/opportunity/watchpoint as **new** or **ongoing**
2. Produces a short "what changed" sentence for the strategic posture card

These flags persist in the database (JSON column) and are visible on every page load until the next Refresh overwrites them.

---

## Scope

- Touches: `summarizer.py`, `prompts.py`, `parser.py`, `intelligence.ts`, `RisksOpportunitiesCards.tsx`, `StrategicPostureCard.tsx`
- No DB migration required (JSON columns)
- No new API endpoints
- First-ever summary per company/period: `is_new` omitted, `what_changed` is `null`

---

## Data Model Changes

### `RiskItem` (JSON, stored in `top_risks`, `top_opportunities`, `watchpoints`)

```json
{
  "text": "Accelerated AI R&D could erode our differentiation.",
  "signal_ids": ["abc123"],
  "is_new": true
}
```

`is_new: true` = item did not exist in the previous summary (LLM decision).
`is_new: false` = item persists from the previous summary.
`is_new` absent = no previous summary existed (first run).

### `CompetitorSummary` (JSON, new top-level field `what_changed`)

```json
{
  "what_changed": "AI investment signals intensified significantly vs last period; the compliance push is new this cycle."
}
```

`what_changed: null` = no previous summary existed.

`what_changed` requires a new `Text` column on `CompetitorSummary` — the only DB change. It is additive, backward-compatible, and requires an Alembic revision. Existing rows get `NULL` automatically, no data migration needed.

---

## Backend Changes

### 1. `summarizer.py` — fetch previous summary

Before building the prompt, query the most recent existing `CompetitorSummary` for the same `company_id` + `period_type`. This is safe because the new summary has not yet been saved at this point in the function:

```python
previous = (
    db.query(CompetitorSummary)
    .filter_by(company_id=company.id, period_type=period_type_enum)
    .order_by(CompetitorSummary.created_at.desc())
    .first()
)
```

Pass it to `build_summary_prompt` as a new optional `previous_summary` parameter.

After parsing, save `parsed.what_changed` into `summary.what_changed`.

### 2. `prompts.py` — delta instructions

`build_summary_prompt` gains an optional `previous_summary: dict | None` parameter.

When `previous_summary` is provided, append a "Previous summary" block to the prompt:

```
Previous summary ({period_label} — prior run):
- Positioning: {previous_summary.positioning_summary}
- Risks: {json list of previous risk texts}
- Opportunities: {json list of previous opportunity texts}
- Watchpoints: {json list of previous watchpoint texts}

Delta instructions:
- For each item in top_risks, top_opportunities, and watchpoints: add "is_new": true if this item has no clear semantic equivalent in the previous list above, "is_new": false if it persists.
- Add a top-level "what_changed" field: 1-2 sentences describing what materially shifted since last period (new themes, dropped concerns, intensity changes). Be concrete, not generic.
```

When `previous_summary` is absent, the delta instructions are omitted and `what_changed` defaults to `null`.

### 3. `parser.py` — parse new fields

`SummaryData` dataclass (or equivalent) gains:
- `what_changed: str | None`

`RiskItemData` gains:
- `is_new: bool | None`

Parser reads `is_new` from each item dict and `what_changed` from the top-level response. Missing fields default to `None` (backward-compatible).

### 4. DB migration

Add `what_changed = Column(Text, nullable=True)` to `CompetitorSummary`.
Generate an Alembic revision. Existing rows get `NULL` automatically.

---

## Frontend Changes

### 5. `intelligence.ts`

```ts
export interface RiskItem {
  text: string;
  signal_ids?: string[];
  is_new?: boolean;          // new
}

export interface CompetitorSummary {
  // ... existing fields ...
  what_changed?: string | null;  // new
}
```

### 6. `RisksOpportunitiesCards.tsx`

In `CitedItemList`, render a "NEW" pill next to the item text when `item.is_new === true`:

```tsx
{item.is_new === true && (
  <span className="ml-1.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-{accentColor}-100 text-{accentColor}-700 uppercase tracking-wide">
    NEW
  </span>
)}
```

- Top Risks panel: accent = `red`
- Opportunities panel: accent = `green`
- Watchpoints panel: accent = `amber`

Items with `is_new === false` or `is_new` absent: rendered as-is, no badge.

### 7. `StrategicPostureCard.tsx`

Below `positioning_summary`, if `summary.what_changed` is present:

```tsx
{summary.what_changed && (
  <p className="text-[11px] text-slate-500 italic mt-2 flex items-start gap-1">
    <span>↺</span>
    {summary.what_changed}
  </p>
)}
```

---

## Behaviour Summary

| Scenario | `is_new` on items | `what_changed` |
|---|---|---|
| First summary ever | absent | `null` |
| Subsequent refresh | `true` / `false` | LLM-generated sentence |
| Previous summary existed but LLM omits field | `null` (parser default) | `null` |

---

## Out of Scope

- Dropped items (items in previous summary but not in current) are not shown
- Historical diff view (comparing any two arbitrary summaries)
- `is_new` on `capability_assessment` items
