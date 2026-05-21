# Capability Strength Explainability & Panel Consolidation

**Date:** 2026-05-21  
**Status:** Approved

## Goal

Make the "Relative Capability Strength" panel on the Competitor Workspace understandable to users:
1. Explain what terms/metrics mean (tooltips + glossar)
2. Show how the score is computed (sub-score breakdown)
3. Trace scores back to concrete assessments/signals

Simultaneously: consolidate `CapabilityActivity` (CapabilityRadar.tsx) into the panel to eliminate redundant capability listings.

---

## 1. Panel Consolidation

### Remove
- `CapabilityRadar` component (`components/workspace/CapabilityRadar.tsx`) is removed from `CompetitorWorkspacePage`
- Its import and usage in `CompetitorWorkspacePage.tsx` is removed

### Updated `RelativeCapabilityStrengthPanel`

**New prop:**
```ts
capabilityDistribution?: CapabilityCount[]  // from workspace data, passed down from page
```

**Per-row additions:**
- **Momentum color** on the strength bar: color derived from `avg_movement_score` in `capabilityDistribution` matched by `capability_key`
  - Orange (`#f97316`) = score ≥ 80
  - Purple (`#8b5cf6`) = score ≥ 60
  - Blue (`#3b82f6`) = score ≥ 30
  - Slate (`#64748b`) = score < 30
  - Fallback (no distribution data): blue (`bg-blue-500`, current default)
- **Signal count badge**: small text `{source_signal_count} signals` shown next to ConfidenceIndicator (already in `CompetitorBenchmarkDetail`)

**Column header row** (new, above the rows):
- Labels: Score | Tier | Rank | Δ | Conf. | Signals
- Each label has a small `<InfoTooltip>` icon with hover explanation (see Tooltips section)

**Panel header:**
- Existing title "Relative Capability Strength" stays
- Add `<HelpCircle>` button (Lucide icon) to the right of the title → opens `CapabilityExplainDrawer` in panel-mode
- Period toggle stays (top right)

---

## 2. Tooltips on Column Headers

Use a small reusable `<InfoTooltip text="..." />` component (inline hover tooltip, similar to existing patterns).

| Column | Tooltip text |
|---|---|
| Score | Score 0–100. Gewichteter Durchschnitt aus 5 Sub-Scores: Capability Depth (35%), Execution Momentum (25%), Market Proof (20%), Strategic Focus (10%), Evidence Coverage (10%). |
| Tier | Leader (≥75), Strong (≥55), Emerging (≥30), Weakly Evidenced (<30 oder zu wenig Belege). Wird bei niedriger Confidence um eine Stufe reduziert. |
| Rank | Position im Vergleich zu allen Wettbewerbern für diese Capability im gewählten Zeitraum. |
| Δ | Veränderung des Scores zur Vorperiode (positiv = gestärkt, negativ = geschwächt). |
| Conf. | Confidence-Score 0–1: basiert auf Anzahl der Assessments, Evidence Coverage und durchschnittlichem Konfidenzwert der Assessments. |
| Signals | Anzahl der Assessments, die in diesem Zeitraum dieser Capability zugeordnet wurden. |

**Momentum bar tooltip** (on hover over the strength bar):
- Shows the `avg_movement_score` value and the color legend:
  - 🟠 ≥80 — sehr hohe Aktivitätsintensität
  - 🟣 ≥60 — hohe Intensität
  - 🔵 ≥30 — mittlere Intensität
  - ⚫ <30 — geringe Intensität

---

## 3. Adaptive `CapabilityExplainDrawer`

New component: `components/workspace/CapabilityExplainDrawer.tsx`

Slide-in from right (same pattern as `ExplainabilityDrawer`). Two modes, single component.

### Props
```ts
interface CapabilityExplainDrawerProps {
  open: boolean;
  onClose: () => void;
  mode: 'panel' | 'capability';
  // capability mode only:
  slug?: string;
  detail?: CompetitorBenchmarkDetail;
  periodType?: BenchmarkPeriodType;
  avgMovementScore?: number; // from capabilityDistribution
  onSelectSignal?: (signalId: string) => void;
}
```

### Panel Mode (`mode='panel'`)

Triggered by the `?` button in the panel header.

Content:
1. **Was ist der Relative Capability Score?** — kurze Erklärung des Konzepts (benchmark, nicht absoluter Score, relativ zu eigenen Signalen im Zeitraum)
2. **Score-Formel:** visuelle Darstellung der Gewichtung (5 Sub-Scores mit %)
3. **Sub-Score-Erklärungen:** tabellarisch, jeder Sub-Score mit Name + 2-Satz-Erklärung
4. **Tier-Definitionen:** Leader / Strong / Emerging / Weakly Evidenced mit Score-Grenzen
5. **Momentum-Farblegende:** Erklärung der 4 Farben mit Score-Schwellen

### Capability Mode (`mode='capability'`)

Triggered by clicking a capability row.

Drawer title: `{capability label}` + `<TierBadge>` inline

Content sections:

**Section 1 — Sub-Score Breakdown**
- 5 horizontal bar rows (0–5 scale), each with:
  - Label + `<InfoTooltip>` mit Sub-Score-Erklärung
  - Bar (colored by value: grün=4-5, amber=2-3, rot=0-1)
  - Numeric value
- Below: "Gesamtscore: {score}/100" mit Formel-Hinweis

Sub-score tooltip texts:
| Sub-Score | Tooltip |
|---|---|
| Capability Depth | Qualität und Substanz der Signale: Wie stark deuten Produkt-Moves, Positionierung und Evidenzstärke auf echte Capability-Tiefe hin? |
| Execution Momentum | Signal-Dichte + durchschnittlicher Bewegungsscore + Anteil starker Moves. Wie aktiv und kraftvoll agiert der Wettbewerber? |
| Market Proof | Externe Belege: Ecosystem-Moves, Kunden-Referenzen, hoher Visibility-Impact. Wie sichtbar ist die Capability am Markt? |
| Strategic Focus | Anteil aller Assessments, der auf diese Capability entfällt + Positionierungs-Moves. Wie stark priorisiert der Wettbewerber diese Fähigkeit? |
| Evidence Coverage | Kombination aus Quellen-Diversität, Confidence der Assessments und Aktualität (Freshness). Wie verlässlich ist die Datenbasis? |

**Section 2 — Activity**
- Signal-Count: `{source_signal_count} Assessments im Zeitraum`
- Momentum: farbiger Badge mit `avg_movement_score` Wert + Farbskala-Legende (kompakt)
- Period label: z.B. "Letzten 30 Tage"

**Section 3 — Contributing Assessments**
- Loaded lazily via `useCapabilityAssessments(slug, cap_key, periodType)` — only fetched when drawer opens
- Loading skeleton while fetching
- List: `{title}` | `{signal_class}` | movement score badge | klickbar → ruft `onSelectSignal(signal_id)` auf
- Falls >10: "… und {n} weitere" link (kein Pagination nötig, max 20 laden)
- Leer-State: "Keine Assessments für diesen Zeitraum"

---

## 4. New Backend Endpoint

### Route
`GET /api/benchmark/competitors/{slug}/capabilities/{cap_key}/assessments`

**Query params:** `period_type: str = '30d'`

### Response Schema
```python
class CapabilityAssessmentItem(BaseModel):
    assessment_id: str
    signal_id: str
    title: str
    movement_score: int
    signal_class: str
    created_at: datetime

class CapabilityAssessmentsResponse(BaseModel):
    capability_key: str
    label: str
    period_type: str
    assessments: list[CapabilityAssessmentItem]
    total_count: int
```

### Implementation
- Query `Assessment` model filtered by: company slug, capability_key, created_at within period window
- Order by `movement_score DESC`, limit 20
- Reuses existing `queries.py` pattern in `app/benchmark/`

---

## 5. Frontend Hook

```ts
// hooks/useBenchmark.ts — new addition
export function useCapabilityAssessments(
  slug: string,
  capKey: string | null,
  periodType: BenchmarkPeriodType,
  enabled: boolean
)
```

- `enabled: false` until drawer opens (lazy fetch)
- Query key: `['benchmark', 'capability-assessments', slug, capKey, periodType]`
- Stale time: 5 min

---

## 6. Page-Level Wiring (`CompetitorWorkspacePage`)

New state:
```ts
const [capabilityExplainMode, setCapabilityExplainMode] = useState<'panel' | 'capability' | null>(null);
const [selectedCapabilityDetail, setSelectedCapabilityDetail] = useState<CompetitorBenchmarkDetail | null>(null);
```

- Panel `?` button → `setCapabilityExplainMode('panel')`
- Row click → `setCapabilityExplainMode('capability')` + `setSelectedCapabilityDetail(detail)`
- `onSelectSignal` → reuses existing `setSelectedScorecardSignalId` (already wired to `ScorecardSignalDrawer`)

`capability_distribution` from `data.summary_30d` / `data.summary_90d` (depending on `activePeriod`) passed as prop to panel.

---

## 7. Files Changed / Created

| File | Change |
|---|---|
| `components/workspace/RelativeCapabilityStrengthPanel.tsx` | Major update: column headers, tooltips, momentum color, signal count, info button, row click handler |
| `components/workspace/CapabilityExplainDrawer.tsx` | **New** — adaptive drawer (panel + capability mode) |
| `components/workspace/CapabilityRadar.tsx` | **Removed** (merged into panel) |
| `components/workspace/InfoTooltip.tsx` | **New** — small reusable hover tooltip component |
| `pages/CompetitorWorkspacePage.tsx` | Remove CapabilityRadar, add drawer state, wire props |
| `hooks/useBenchmark.ts` | Add `useCapabilityAssessments` |
| `types/benchmark.ts` | Add `CapabilityAssessmentItem`, `CapabilityAssessmentsResponse` |
| `backend/app/routers/benchmark.py` | Add new endpoint |
| `backend/app/schemas/benchmark.py` | Add response schemas |
| `backend/app/benchmark/queries.py` | Add assessments query function |

---

## Out of Scope

- Pagination for assessments (max 20, "… und N weitere" suffices)
- Editing or re-weighting sub-scores
- Mobile layout optimization
- Changes to the Benchmark Overview page or CapabilityLeaderboardDrawer
