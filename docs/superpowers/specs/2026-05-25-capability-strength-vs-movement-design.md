# Capability Strength vs. Movement Panel — Design Spec

**Date:** 2026-05-25
**Status:** Approved for implementation

---

## Overview

A new full-width panel on the `CompetitorWorkspacePage` that renders a 4-quadrant scatter chart of capability strength (Y) vs. movement score (X). Each capability is a dot; an arrow shows its 2D trajectory in chart space. Clicking a dot opens the existing `CapabilityExplainDrawer`.

---

## Placement

New Row 3 in `CompetitorWorkspacePage`, inserted between the Moves row and the Risks/Opportunities section:

```
Row 1: Strategic Posture | Dimension Scores
Row 2: Capability Strength (bar) | Moves
Row 3: [Capability Strength vs. Movement] ← NEW (full width)
Row 4: Risks / Opportunities
```

---

## Component: `CapabilityStrengthVsMovement`

### File
`frontend/src/components/benchmark/CapabilityStrengthVsMovement.tsx`
(existing draft — rewrite to match this spec)

### Props

```ts
interface CapabilityStrengthVsMovementProps {
  slug: string;
  onCapabilityClick: (detail: CompetitorBenchmarkDetail) => void;
}
```

### Data

Fetched internally via `useCompetitorBenchmark(slug, period)`. Mapped from `CompetitorBenchmarkDetail`:

| Field | Chart use |
|---|---|
| `relative_strength_score` | Y position + dot radius |
| `strength_delta` | Y component of arrow vector |
| `momentum_score` (from `BenchmarkMatrixCell`) or movement proxy | X position + X component of arrow vector |
| `tier` | dot color |
| `confidence` | tooltip |
| `source_signal_count` | tooltip |

> **Note on movement / X-axis value:** `CompetitorBenchmarkDetail` exposes `strength_delta` but not a standalone "movement score". Use `strength_delta` as a proxy for movement (represents change in relative strength). If a dedicated movement field becomes available from the API, swap it in. The X axis is therefore `strength_delta` centred at 0.

---

## Chart Layout

### Axes

- **X-axis:** Movement / strength delta. Centre = 0. Left = decline (negative delta), right = growth (positive delta).
- **Y-axis:** Current `relative_strength_score`. Bottom = 0, top = 100.
- Quadrant dividers: vertical line at x=0, horizontal line at y=50.

### Quadrant Labels

| Position | Label |
|---|---|
| Top-right | Accelerating Strongholds |
| Top-left | Established but Quiet |
| Bottom-right | Emerging Bets |
| Bottom-left | Low Relevance |

### Dots

- **Radius:** `8 + (relative_strength_score / 100) * 14` px (range 8–22 px)
- **Fill color:** tier
  - `leader` → `#059669`
  - `strong` → `#2563eb`
  - `emerging` → `#f59e0b`
  - `weakly_evidenced` → `#d1d5db`
- **Opacity:** 0.85 at rest, 1.0 on hover

### Labels (beside dots)

- Positioned to the right of the dot edge with 6 px offset
- Text: short capability label (first significant word from `CAPABILITIES[key].label`)
- Font: 11px, color matches tier color
- `pointer-events: none` to avoid interfering with dot interaction

### Arrows (2D trajectory vector)

Arrow represents the velocity vector in chart space:
- **Direction:** `atan2(strength_delta, strength_delta)` — since we only have one delta value, the arrow points directly up (positive) or down (negative) along Y, with no X component until a separate movement-delta field is available. Once a `movement_delta` field exists, direction becomes `atan2(strength_delta, movement_delta)`.
- **Length:** `clamp(|strength_delta| * 1.5, 6, 40)` px
- **Stroke width:** `1 + clamp(|strength_delta| / 30, 0, 1.5)` (thin for small deltas, thicker for large)
- **Color:** same as tier color, opacity 0.7
- **Arrowhead:** small filled triangle at tip
- **Hidden when:** `strength_delta` is null or 0

### Coordinate mapping

```
svgX = padding + ((value - minX) / rangeX) * plotWidth
svgY = padding + plotHeight - ((value - minY) / rangeY) * plotHeight
```

Min/max are derived from data with symmetric X range (mirrored around 0 for visual balance).

---

## Interactions

### Hover
SVG `<g>` tooltip rendered above dot:
- Full capability label
- Strength: `{relative_strength_score}`
- Δ Strength: `{strength_delta > 0 ? '+' : ''}{strength_delta}`
- Tier badge (text)
- Confidence: `{Math.round(confidence * 100)}%`

### Click
Calls `onCapabilityClick(detail)` with the full `CompetitorBenchmarkDetail` object → opens existing `CapabilityExplainDrawer` on the page. No new drawer needed.

---

## Panel Header

- Title: "Capability Strength vs. Movement"
- Info icon (HelpCircle) → toggles explanation tooltip
- Period toggle: `30d / 90d / 180d` (own state, matching `RelativeCapabilityStrengthPanel` pattern)

---

## States

| State | Treatment |
|---|---|
| Loading | Skeleton placeholder matching panel height |
| No data / empty capabilities | Centered empty message |
| Capability with null delta | Dot rendered, no arrow |

---

## Page Integration

In `CompetitorWorkspacePage`:

```tsx
import { CapabilityStrengthVsMovement } from '../components/benchmark/CapabilityStrengthVsMovement';

// In JSX, after Row 2:
<CapabilityStrengthVsMovement
  slug={slug ?? ''}
  onCapabilityClick={(detail) => {
    setSelectedCapabilityDetail(detail);
    setCapabilityExplainMode('capability');
  }}
/>
```

No additional state or hooks needed at the page level.

---

## Out of scope

- Collision avoidance for overlapping labels (accept overlaps for now)
- Diagonal arrows (requires a second delta field not yet in the API; placeholder for future)
- Zoom / pan interactions
