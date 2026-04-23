# Signal Timestamps Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show both the source article publication date and the signal analysis date in the Signal Feed table and Signal Detail Drawer, using a stacked layout with styled hover tooltips showing absolute dates.

**Architecture:** Add a `formatAbsolute` utility, build a reusable `DateWithTooltip` component using Tailwind's `group` hover pattern, then update `SignalFeedTable` (stacked dates in one column) and `SignalDetailDrawer` (two inline date labels in the header). No backend changes — all data already returned by the API.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, existing `SignalFeedItem` type

---

## File Map

| File | Action |
|------|--------|
| `frontend/src/utils/dates.ts` | Add `formatAbsolute` |
| `frontend/src/components/DateWithTooltip.tsx` | Create new component |
| `frontend/src/components/signals/SignalFeedTable.tsx` | Replace single Date column with stacked layout |
| `frontend/src/components/signals/SignalDetailDrawer.tsx` | Update header date display |

---

### Task 1: Add `formatAbsolute` to dates utility

**Files:**
- Modify: `frontend/src/utils/dates.ts`

- [ ] **Step 1: Add the function**

Open `frontend/src/utils/dates.ts` and append this function after the existing exports:

```typescript
export function formatAbsolute(dateStr: string | null | undefined): string {
  if (!dateStr) return '–';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '–';
  return date.toLocaleString('de-DE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `dates.ts`

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/utils/dates.ts
rtk git commit -m "feat: add formatAbsolute date utility (de-DE locale)"
```

---

### Task 2: Create `DateWithTooltip` component

**Files:**
- Create: `frontend/src/components/DateWithTooltip.tsx`

This component shows a relative date string; on hover, a styled tooltip appears with the absolute date.

- [ ] **Step 1: Create the component**

```typescript
// frontend/src/components/DateWithTooltip.tsx
import { formatDistanceToNow, formatAbsolute } from '../utils/dates';

interface Props {
  date: string | null | undefined;
}

export default function DateWithTooltip({ date }: Props) {
  if (!date) return <span className="text-slate-400">–</span>;

  return (
    <span className="relative group/dt inline-block">
      <span className="cursor-default">{formatDistanceToNow(date)}</span>
      <span className="
        absolute bottom-full left-0 mb-1 z-50
        whitespace-nowrap
        px-2 py-1 rounded
        bg-slate-800 text-white text-[11px]
        opacity-0 group-hover/dt:opacity-100
        pointer-events-none
        transition-opacity duration-150
      ">
        {formatAbsolute(date)}
      </span>
    </span>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/components/DateWithTooltip.tsx
rtk git commit -m "feat: add DateWithTooltip component with absolute date on hover"
```

---

### Task 3: Update SignalFeedTable — stacked date column

**Files:**
- Modify: `frontend/src/components/signals/SignalFeedTable.tsx`

Currently: one `"Date"` column using `formatDistanceToNow(item.published_at || item.created_at)`.  
Target: one `"Datum"` column, stacked — article date on top (if available), "analysiert" date below in smaller dimmed text.

- [ ] **Step 1: Add import for DateWithTooltip**

At the top of `frontend/src/components/signals/SignalFeedTable.tsx`, add:

```typescript
import DateWithTooltip from '../DateWithTooltip';
```

Remove the existing import of `formatDistanceToNow` from `'../../utils/dates'` if it's only used for the date column (check first — if used elsewhere, keep it).

- [ ] **Step 2: Update the column header**

Find the header row array:
```typescript
{['Signal', 'Competitor', 'Capability', 'Strength', 'Confidence', 'Date'].map((h) => (
```

Change `'Date'` to `'Datum'`:
```typescript
{['Signal', 'Competitor', 'Capability', 'Strength', 'Confidence', 'Datum'].map((h) => (
```

- [ ] **Step 3: Replace the date cell**

Find the existing date `<td>`:
```typescript
<td className="py-3 text-slate-600 whitespace-nowrap">
  {formatDistanceToNow(item.published_at || item.created_at)}
</td>
```

Replace with:
```typescript
<td className="py-3 text-slate-600">
  {item.published_at && (
    <div>
      <DateWithTooltip date={item.published_at} />
    </div>
  )}
  <div className="text-[11px] text-slate-400 mt-0.5">
    analysiert: <DateWithTooltip date={item.created_at} />
  </div>
</td>
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/components/signals/SignalFeedTable.tsx
rtk git commit -m "feat: show stacked article + analysed dates in signal feed table"
```

---

### Task 4: Update SignalDetailDrawer — header date display

**Files:**
- Modify: `frontend/src/components/signals/SignalDetailDrawer.tsx`

Currently the header shows:
```
{company_name} · {formatDistanceToNow(published_at || created_at)}
```

Target:
```
{company_name} · Artikel: {DateWithTooltip} · Analysiert: {DateWithTooltip}
```
Artikel line omitted if `published_at` is null.

- [ ] **Step 1: Add import for DateWithTooltip**

At the top of `frontend/src/components/signals/SignalDetailDrawer.tsx`, add:

```typescript
import DateWithTooltip from '../DateWithTooltip';
```

Remove the import of `formatDistanceToNow` from `'../../utils/dates'` if it's no longer used elsewhere in the file.

- [ ] **Step 2: Replace the header date line**

Find:
```typescript
<div className="flex items-center gap-2 mt-1.5">
  <span className="text-[11px] text-slate-500">{item.company_name}</span>
  <span className="text-slate-300">·</span>
  <span className="text-[11px] text-slate-500">{formatDistanceToNow(item.published_at || item.created_at)}</span>
</div>
```

Replace with:
```typescript
<div className="flex items-center gap-2 mt-1.5 flex-wrap">
  <span className="text-[11px] text-slate-500">{item.company_name}</span>
  {item.published_at && (
    <>
      <span className="text-slate-300">·</span>
      <span className="text-[11px] text-slate-500">
        Artikel: <DateWithTooltip date={item.published_at} />
      </span>
    </>
  )}
  <span className="text-slate-300">·</span>
  <span className="text-[11px] text-slate-500">
    Analysiert: <DateWithTooltip date={item.created_at} />
  </span>
</div>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 4: Start dev server and verify visually**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence && docker compose -f docker-compose.dev.yml up -d
```

Then open the Signal Feed in browser and verify:
- Table "Datum" column shows article date + "analysiert: X" below
- Hovering each date shows absolute date tooltip
- Signals without `published_at` show only "analysiert" line
- Clicking a signal opens the drawer with "Artikel: X · Analysiert: Y" in the header
- Hovering those dates also shows absolute tooltip

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/components/signals/SignalDetailDrawer.tsx
rtk git commit -m "feat: show article and analysed dates in signal detail drawer header"
```
