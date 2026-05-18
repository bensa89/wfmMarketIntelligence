# Competitor Scorecard — Design Spec

**Date:** 2026-05-18
**Status:** Approved for implementation planning

---

## 1. Context and Goals

The WFM Market Intelligence Hub already collects Signals, generates SignalAssessments with movement scores, and computes per-capability benchmarks via `CompetitorCapabilityBenchmark`. This spec adds a **Competitor Scorecard** layer that:

- Aggregates SignalAssessments into a multi-dimensional company-level score per configurable time period
- Runs parallel to (not replacing) the existing benchmark pipeline
- Is persisted as snapshots for historical comparison
- Surfaces on `/competitors` (summary) and `/competitors/:slug` (depth view)

**Non-goals:** This spec does not replace `CompetitorCapabilityBenchmark`. The scorecard is a separate, higher-level view.

---

## 2. Architecture Decision

**Option chosen:** Modular pipeline (DimensionRouter → KPIEngine → ScorecardBuilder) with light assessment enrichment.

- `DimensionRouter` — persists `dimension_targets` and `kpi_targets` on `SignalAssessment` at creation time
- `KPIEngine` — pure functions; no DB access; takes assessment lists, returns KPI values with contributing IDs
- `ScorecardBuilder` — orchestration + persistence of `CompetitorScorecard`
- SQL used only for fetching/filtering candidate assessments, not for KPI computation
- Scorecard business logic lives in Python, not SQL

---

## 3. Data Model Changes

### 3.1 SignalAssessment — new fields

| Field | Type | Default | Populated by |
|---|---|---|---|
| `dimension_targets` | `JSON` (list of dimension keys) | `[]` | DimensionRouter (rules, at assessment creation) |
| `kpi_targets` | `JSON` (list of KPI IDs) | `[]` | DimensionRouter (rules, at assessment creation) |
| `assessment_weight` | `Float` | `1.0` | LLM supplement (when `evidence_strength >= 4` or `movement_strength = market_shaping`) |
| `valid_from` | `DateTime` | `signal.published_at or created_at` | Set at assessment creation |
| `valid_until` | `DateTime` nullable | `null` | Optional expiry; null = no expiry |
| `buyer_relevance` | `SmallInteger` (1–5) nullable | `null` | LLM-populated; initially null |
| `routing_version` | `String(20)` | `"v1"` | Set at routing time |

### 3.2 New model: CompetitorScorecard

Table: `competitor_scorecards`

| Field | Type | Notes |
|---|---|---|
| `id` | `String(36)` UUID | PK |
| `company_id` | `String(36)` FK | indexed |
| `period_type` | `String(10)` | `"30d"`, `"90d"`, `"180d"` |
| `period_start` | `Date` | |
| `period_end` | `Date` | |
| `generated_at` | `DateTime` | |
| `overall_score` | `Float` nullable | `null` if all dimensions null (no data) |
| `overall_trend` | `String(10)` nullable | `"rising"`, `"stable"`, `"declining"`, `null` |
| `dimension_scores` | `JSON` | See §3.3 |
| `top_capabilities` | `JSON` | Ordered list of `{capability_key, score}` |
| `top_moves` | `JSON` | Top 5 `{assessment_id, title, movement_score, signal_class}` |
| `risk_flags` | `JSON` | `{assessment_id, capability_key, movement_strength, title}` |
| `watchpoints` | `JSON` | Deduplicated strings ordered by frequency |
| `benchmark_position` | `JSON` | `{rank, percentile, total_competitors}` |
| `contributing_assessment_ids` | `JSON` | All assessment UUIDs used |
| `is_current` | `Boolean` | `true` for latest snapshot per `(company_id, period_type)` |
| `scorecard_version` | `String(20)` | e.g. `"sc_v1"` |
| `routing_version` | `String(20)` | e.g. `"v1"` |

**Unique constraint:** `(company_id, period_type, generated_at)`
**Index:** `(company_id, period_type, is_current)` for fast current-snapshot queries.

### 3.3 dimension_scores JSON shape

```json
{
  "capability_strength": {
    "score": 72.4,
    "trend": "rising",
    "kpis": {
      "cap_weighted_score": {
        "value": 68.0,
        "contributing_ids": ["uuid1", "uuid2"]
      },
      "cap_strong_move_count_raw": { "value": 4, "contributing_ids": [...] },
      "cap_strong_move_count_weighted": { "value": 3.6, "contributing_ids": [...] },
      "cap_market_shaping_ratio": { "value": 0.25, "contributing_ids": [...] }
    }
  },
  "activity": { ... },
  "market_impact": { ... },
  "customer_proof": { ... },
  "momentum": { ... }
}
```

A dimension with zero contributing assessments has `score: null` and empty `kpis`. This is valid — it means no data, not zero strength.

---

## 4. DimensionRouter

**Location:** `backend/app/scorecard/dimension_router.py`

Stateless mapper. Takes a `SignalAssessment`, returns `dimension_targets`, `kpi_targets`, `assessment_weight`, `routing_version`. Runs at assessment creation (inside `assess_signal()`), persisting results onto the assessment. Re-runnable for backfills.

### 4.1 Rule layer (deterministic)

| Condition | Dimension targets | KPI targets | Weight modifier |
|---|---|---|---|
| Any `signal_class` | `activity` | `act_count_raw`, `act_count_weighted`, `act_weighted_strength` | 1.0 |
| `movement_strength in [strong, market_shaping]` | `activity` | `act_strong_count_raw`, `act_strong_count_weighted` | 1.0 |
| `signal_class = product_capability_move` | `capability_strength`, `market_impact` | `cap_weighted_score`, `mkt_move_quality` | 1.0 |
| `signal_class = market_expansion_move` | `market_impact` | `mkt_weighted_visibility`, `mkt_strategic_quality` | 1.0 |
| `signal_class = market_expansion_move` AND `evidence_strength >= 4` | `capability_strength` | `cap_weighted_score` | 0.7 |
| `signal_class in [ecosystem_move, positioning_move]` | `market_impact`, `customer_proof` | `mkt_strategic_quality`, `cp_ecosystem_count_raw` | 1.0 |
| `signal_class = ecosystem_move` AND `evidence_strength >= 4` | `customer_proof` | `cp_weighted_evidence` | 1.0 |
| `visibility_impact = high` | `market_impact` | `mkt_high_visibility_count_raw`, `mkt_weighted_visibility` | 1.0 |
| `signal_class = hiring_signal` | `activity`, `momentum` | `act_count_raw`, `mom_hiring_velocity` | activity=0.6, momentum=1.0 |
| `signal_class = thought_leadership_signal` AND `visibility_impact = high` AND `movement_strength in [strong, market_shaping]` | `activity`, `market_impact` | `act_count_raw`, `mkt_weighted_visibility` | activity=0.5, market_impact=0.4 |
| `signal_class = thought_leadership_signal` (all other cases) | `activity` | `act_count_raw` | 0.5 |

**Rule override semantics:** The "Any `signal_class`" row is the base rule. When a more specific rule targets the same dimension, the specific rule's weight **replaces** (not stacks with) the base weight for that dimension. Example: `hiring_signal` contributes to `activity` at weight 0.6 — not 1.0 + 0.6. `thought_leadership_signal` contributes to `activity` at 0.5 (strict conditions) or 0.5 (catch-all) — not 1.0 + 0.5. Multiple specific rules for different dimensions remain additive across dimensions, not within a single dimension.

**Capability aggregation note:** `cap_weighted_score` averages per-capability scores, not the sum. A competitor with 10 signals all in one capability scores the same on that capability as one with 2 signals — volume is captured by `act_count_weighted`. Breadth is not penalised; depth is not inflated by volume.

### 4.2 LLM supplement layer

The existing assessor LLM prompt is extended with two optional fields:
- `buyer_relevance` (1–5): how directly relevant is this move to a buyer decision?
- `assessment_weight` override (0.5–2.0)

The LLM supplement **only runs** when `evidence_strength >= 4` OR `movement_strength = market_shaping`. Otherwise the rule defaults apply.

### 4.3 Versioning

```python
ROUTING_VERSION = "v1"  # bump when rules change
```

On bump, a backfill job re-routes all existing assessments by re-running the rule layer.

---

## 5. KPIEngine

**Location:** `backend/app/scorecard/kpi_engine.py`

Pure functions only. No DB access, no side effects. Takes weighted assessment lists, returns `KPIValue(value: float | None, contributing_ids: list[str])`.

### 5.1 Effective weight

Applied before all KPI calculations. Decay adjusts contribution weight, not KPI values:

```python
RECENCY_DECAY_MAX = 0.30  # floor: recency_weight >= 0.70 — defined here, imported by ScorecardBuilder

recency_weight = 1.0 - (age_days / period_days) * RECENCY_DECAY_MAX
effective_weight = assessment_weight * recency_weight
```

Raw counts use integer counting (no weight). Weighted counts use `effective_weight`.

### 5.2 Capability Strength KPIs

| KPI | Formula | Range | Clamp |
|---|---|---|---|
| `cap_weighted_score` | Mean of per-capability scores. Per capability: `Σ(movement_score × ew × evidence_strength/3) / Σ(ew × evidence_strength/3)`. Returns `null` if no assessments route here. | 0–100 | yes |
| `cap_strong_move_count_raw` | Integer count where `movement_strength in [strong, market_shaping]` | 0–N | no |
| `cap_strong_move_count_weighted` | `Σ(ew)` for same | 0–N | no |
| `cap_market_shaping_ratio` | `Σ(ew for market_shaping) / Σ(ew total)`. `null` if zero total. | 0–1 | yes |

### 5.3 Activity KPIs

| KPI | Formula | Range | Clamp |
|---|---|---|---|
| `act_count_raw` | Integer count of all assessments in period | 0–N | no |
| `act_count_weighted` | `Σ(ew)` | 0–N | no |
| `act_strong_count_raw` | Integer count where `movement_strength in [strong, market_shaping]` | 0–N | no |
| `act_strong_count_weighted` | `Σ(ew)` for same | 0–N | no |
| `act_weighted_strength` | `Σ(movement_score × ew) / Σ(ew)`. `null` if zero total. | 0–100 | yes |
| `act_signal_class_diversity` | `H(p) / log(K)` where `H` = Shannon entropy over weighted `signal_class` distribution, `K = 7` (total `SignalClass` enum values). `0.0` when `act_count_raw = 0`. **When `K` changes (new enum values added), update this constant.** | 0–1 | yes |

### 5.4 Market Impact KPIs

| KPI | Formula | Range | Clamp |
|---|---|---|---|
| `mkt_high_visibility_count_raw` | Integer count where `visibility_impact = high` | 0–N | no |
| `mkt_high_visibility_count_weighted` | `Σ(ew)` for same | 0–N | no |
| `mkt_weighted_visibility` | `Σ(vis_w × movement_score × ew) / Σ(vis_w × ew)`. `vis_w`: low=0.3, medium=0.7, high=1.0. `null` if zero total. | 0–100 | yes |
| `mkt_move_quality` | `Σ(movement_score × ew) / Σ(ew)` filtered to `[product_capability_move, market_expansion_move, ecosystem_move]`. `null` when no qualifying assessments. | 0–100 | yes when not null |
| `mkt_strategic_quality` | `Σ(evidence_strength × confidence × ew) / Σ(ew)` for strategic classes. Raw range 0–5, scaled `× 20` → 0–100. `null` if zero total. | 0–100 | yes |

### 5.5 Customer Proof KPIs

| KPI | Formula | Range | Clamp |
|---|---|---|---|
| `cp_ecosystem_count_raw` | Integer count of `[ecosystem_move, positioning_move]` | 0–N | no |
| `cp_ecosystem_count_weighted` | `Σ(ew)` for same | 0–N | no |
| `cp_weighted_evidence` | `Σ(evidence_strength × confidence × ew) / Σ(ew)` for customer-adjacent classes. Raw 0–5, scaled `× 20` → 0–100. `null` if zero total. | 0–100 | yes |
| `cp_high_evidence_ratio` | `Σ(ew for evidence_strength >= 4) / Σ(ew total)`. `null` if zero total. | 0–1 | yes |
| `cp_validation_score` | `(cp_weighted_evidence × 0.6) + (cp_high_evidence_ratio × 100 × 0.4)`. Clamped after sum. `null` if either input is null. | 0–100 | yes |

### 5.6 Momentum KPIs

Requires both current and prior period assessment lists.

| KPI | Formula | Range | Clamp |
|---|---|---|---|
| `mom_period_delta` | `act_weighted_strength_current − act_weighted_strength_prior`. `null` if either is null. | −100–100 | yes |
| `mom_strong_move_acceleration` | `act_strong_count_weighted_current − act_strong_count_weighted_prior`. `null` if prior period has no data. | unclamped | no |
| `mom_hiring_velocity` | `Σ(ew)` for `hiring_signal` class in current period. `null` if no hiring signals. | 0–N | no |
| `mom_trend` | `"rising"` if `mom_period_delta > MOMENTUM_RISING_THRESHOLD`, `"declining"` if `< MOMENTUM_DECLINING_THRESHOLD`, else `"stable"`. `null` if `mom_period_delta` is null. | enum | — |

---

## 6. ScorecardBuilder

**Location:** `backend/app/scorecard/builder.py`

### 6.1 Module-level constants

```python
MOMENTUM_RISING_THRESHOLD = 5.0
MOMENTUM_DECLINING_THRESHOLD = -5.0
SCORECARD_VERSION = "sc_v1"
# RECENCY_DECAY_MAX lives in kpi_engine.py and is imported here — do not redefine
DIMENSION_WEIGHTS = {
    "capability_strength": 0.30,
    "market_impact":       0.25,
    "activity":            0.20,
    "customer_proof":      0.15,
    "momentum":            0.10,
}
```

All threshold/weight changes require a `SCORECARD_VERSION` bump.

### 6.2 Build flow

```
ScorecardBuilder.build(company_id, period_type, db)

1. resolve_period(period_type)
   → period_start, period_end, prev_period_start, prev_period_end

2. fetch_assessments(company_id, period_start, period_end, db)
   SQL: WHERE company_id = ?
        AND valid_from <= period_end
        AND (valid_until IS NULL OR valid_until >= period_start)
   Returns [] (not error) if empty.

3. fetch_prior_assessments(company_id, prev_period_start, prev_period_end, db)
   Same overlap query for prior window. Used only for momentum KPIs.

4. ensure_routed(assessments, db)
   For any assessment where routing_version != ROUTING_VERSION:
   call DimensionRouter.route(assessment), persist updated fields.

5. group_by_dimension(assessments)
   → Dict[dimension_key, List[assessment]]
   Each assessment may appear in multiple groups per its dimension_targets.

6. For each dimension:
   KPIEngine.compute_dimension(dimension_key, assessments, prior_assessments?)
   → DimensionResult(score: float | None, kpis: Dict[str, KPIValue], trend: str | None)
   If no assessments route to a dimension: score = None, kpis = {}.

7. compute_overall_score(dimension_results)
   Weighted average over non-null dimensions only.
   Weights re-normalised to sum to 1.0 after nulls excluded.
   Returns None if all dimensions null.

8. assemble_top_moves(assessments, n=5)
   Top N by (movement_score × effective_weight), deduplicated by signal_id.

9. assemble_risk_flags(assessments)
   movement_strength = market_shaping AND capability strategic_weight >= 8.

10. assemble_watchpoints(assessments)
    Union of watch_items from ALL contributing_assessment_ids (not only top moves).
    Deduplicated by string equality after whitespace strip.
    Ordered by frequency of occurrence across assessments (most common first).

11. flip_current_flag(company_id, period_type, db)
    UPDATE SET is_current = False
    WHERE company_id = ? AND period_type = ? AND is_current = True

12. persist(CompetitorScorecard, db)
    INSERT new row with is_current = True, benchmark_position = None initially.

13. compute_benchmark_position(company_id, period_type, db)
    SELECT all is_current = True rows for period_type (including just-inserted row).
    Rank by overall_score DESC. Null overall_score ranked last.
    Returns {rank, percentile, total_competitors}.
    If only one competitor: rank=1, percentile=100, total=1.

14. UPDATE scorecard.benchmark_position with result from step 13.
```

### 6.3 Pipeline integration

Called from `assess_signal()` in `backend/app/assessor/pipeline.py`, immediately after `BenchmarkAggregationService.recompute_company()`. Runs synchronously in the same DB session. Exceptions are caught and logged — must not block signal assessment persistence. Recomputes all three period types (`30d`, `90d`, `180d`) on every trigger.

---

## 7. API Endpoints

All under `/api/scorecards/`, all require HTTP Basic Auth.

New router: `backend/app/routers/scorecards.py`. Mounted in `main.py`.

### 7.1 Scorecard endpoints

**`GET /api/scorecards/{company_slug}?period_type=30d`**
- `period_type` is required (no default). Returns 400 if omitted.
- Returns single `ScorecardRead` or 404 if no scorecard exists for this company + period.

**`GET /api/scorecards/{company_slug}/history?period_type=30d&limit=10`**
- All snapshots for a competitor + period, ordered by `generated_at` desc.
- Returns list of `ScorecardHistoryItem` (lightweight: score, trend, generated_at, scorecard_version).

**`GET /api/scorecards/{company_slug}/explain?period_type=30d`**
- Reads from persisted `dimension_scores` JSON. No recompute.
- Caps contributing assessment detail at **top 5 per dimension** by weighted contribution.
- Returns `ScorecardExplain`:
  ```json
  {
    "overall_score": 74.2,
    "dimension_breakdown": [
      {
        "dimension": "market_impact",
        "score": 81.0,
        "weight": 0.25,
        "effective_weight": 0.31,
        "weighted_contribution": 25.1,
        "top_contributing_assessments": [
          { "assessment_id": "...", "title": "...", "movement_score": 82, "signal_class": "product_capability_move" }
        ],
        "total_contributing": 12,
        "kpi_detail": { ... }
      }
    ],
    "null_dimensions": ["momentum"],
    "score_formula": "Weighted average of non-null dimensions. Weights re-normalised: shown as effective_weight.",
    "routing_version": "v1",
    "scorecard_version": "sc_v1"
  }
  ```
  `effective_weight` = re-normalised weight after null dimensions excluded.

**`POST /api/scorecards/{company_slug}/recompute`**
- Triggers `ScorecardBuilder.build()` for all period types.
- Returns slim acknowledgment only:
  ```json
  {
    "status": "ok",
    "company_slug": "atoss",
    "recomputed_periods": ["30d", "90d", "180d"],
    "scorecard_ids": { "30d": "uuid", "90d": "uuid", "180d": "uuid" },
    "generated_at": "2026-05-18T..."
  }
  ```

**`POST /api/scorecards/recompute-all?period_type=30d`**
- Recomputes all competitors sequentially for given period type.
- Returns: `{ "recomputed": 8, "errors": [{ "company_slug": "...", "error": "..." }] }`

### 7.2 Benchmark endpoints

**`GET /api/scorecards/benchmark?period_type=30d&page=1&page_size=20`**
- `page_size` max 50.
- Response:
  ```json
  {
    "items": [...],
    "total": 12,
    "page": 1,
    "page_size": 20,
    "pages": 1,
    "period_type": "30d",
    "capability_leaders": { "ai_copilot": { "company_slug": "...", "score": 91.0 }, ... },
    "highest_momentum": { "company_slug": "...", "mom_period_delta": 18.4 },
    "threat_flags": [{ "company_slug": "...", "capability": "shift_scheduling", "movement_strength": "market_shaping" }]
  }
  ```

**`GET /api/scorecards/benchmark/capability/{capability_key}?period_type=30d&page=1&page_size=20`**
- Paginated. Returns all competitors ranked by `cap_weighted_score` for a single capability with Wardley band context.

### 7.3 Schemas

New Pydantic v2 schemas in `backend/app/schemas/scorecard.py`:
- `ScorecardRead` — full scorecard (dimension_scores, contributing_ids, metadata)
- `ScorecardHistoryItem` — score, trend, generated_at, scorecard_version
- `ScorecardExplain` — capped explainability payload (top 5 per dimension)
- `BenchmarkScorecardItem` — single row in benchmark table
- `BenchmarkScorecardView` — paginated benchmark response with capability_leaders, highest_momentum, threat_flags
- `ScorecardRecomputeAck` — slim recompute acknowledgment

---

## 8. Frontend

Frontend changes are implemented in a **separate plan file** (`frontend-scorecard-plan`). Design summary:

### 8.1 `/competitors` — ScorecardSummaryStrip per row

Each competitor row gains a scorecard summary strip:
- Overall score badge
- Trend indicator (rising ↑ / stable → / declining ↓)
- Top 2 dimension scores as compact pills
- Rank badge (e.g. `#2 of 8`)

**Shared period state:** A single period selector at the page level (`30d / 90d / 180d`) drives all rows. State lives in the page component, passed down as props. Defaults to `30d`.

**Data fetching:** `useBenchmarkScorecard(period_type)` called once at page level; scorecard data fanned out by `company_id` to each row component.

**No-data copy:** When scorecard is null or has `overall_score: null`:
> *"No scorecard data for this period"*
Score badge shows `—` instead of a number. Dimension pills hidden. Trend indicator hidden.

**Loading state:** Each strip shows a skeleton placeholder (score badge + 2 pill skeletons) while loading. List does not jump layout.

### 8.2 `/competitors/:slug` — Scorecard tab

A new **Scorecard** tab added to the competitor detail page alongside existing tabs/sections.

**Shared period state:** Period selector within the tab. State lives in the tab component. Defaults to `30d`. Does not affect other tabs.

**Tab layout (two columns):**

Left column:
- `DimensionScoreGrid` — 5 `DimensionScoreCard` components. Each shows: score (or `—`), trend arrow, highest-value KPI as a callout line.
- `RiskFlagsPanel` — market-shaping signals in high-weight capabilities. Empty state: *"No high-risk signals in this period."*

Right column:
- `CapabilityStrengthPanel` — top capabilities ranked by `cap_weighted_score` with Wardley band. Empty state: *"No capability data in this period."*
- `TopMovesTimeline` — top 5 moves. Clicking a move opens existing `SignalDetailDrawer`. Empty state: *"No moves recorded in this period."*
- `WatchpointsPanel` — watchpoints ordered by frequency. Empty state: *"No watchpoints in this period."*

**Top bar:**
- Period selector
- `generated_at` label: *"Last updated May 18, 2026"*
- "Why this score?" button → opens `ExplainabilityDrawer` (lazy-fetched on open)
- "Recompute" button → calls `POST …/recompute`, shows spinner, refreshes on resolve. Disabled while loading.

**No-data state (entire tab):** When no scorecard exists for the selected period:
> *"No scorecard available for this period. Scorecards are generated automatically when new signals are analysed. You can also trigger a manual recompute above."*
Recompute button still visible.

**Loading state:** On period change or initial load, dimension cards show individual score skeletons. Panels show skeleton rows. Layout does not shift.

**ExplainabilityDrawer:**
- Slide-in from right.
- Dimension breakdown table: dimension name, score, effective weight, weighted contribution.
- Per dimension: top 5 contributing assessments (title, movement_score, signal_class) + `total_contributing` count (e.g. *"…and 7 more"*).
- Score formula note: *"Overall score is a weighted average of non-null dimensions. Weights are re-normalised when dimensions have no data."*
- Routing version + scorecard version shown at footer.
- Loading state: skeleton table rows while `useScorecardExplain` resolves.
- No-data state: *"Explainability data unavailable for this period."*

### 8.3 New components

| Component | Location |
|---|---|
| `ScorecardSummaryStrip` | `frontend/src/components/scorecard/ScorecardSummaryStrip.tsx` |
| `DimensionScoreGrid` | `frontend/src/components/scorecard/DimensionScoreGrid.tsx` |
| `DimensionScoreCard` | `frontend/src/components/scorecard/DimensionScoreCard.tsx` |
| `CapabilityStrengthPanel` | `frontend/src/components/scorecard/CapabilityStrengthPanel.tsx` |
| `TopMovesTimeline` | `frontend/src/components/scorecard/TopMovesTimeline.tsx` |
| `RiskFlagsPanel` | `frontend/src/components/scorecard/RiskFlagsPanel.tsx` |
| `WatchpointsPanel` | `frontend/src/components/scorecard/WatchpointsPanel.tsx` |
| `ExplainabilityDrawer` | `frontend/src/components/scorecard/ExplainabilityDrawer.tsx` |

### 8.4 New hooks

| Hook | Endpoint |
|---|---|
| `useScorecard(slug, period_type)` | `GET /api/scorecards/{slug}?period_type=` |
| `useScorecardExplain(slug, period_type)` | `GET /api/scorecards/{slug}/explain?period_type=` (lazy) |
| `useScorecardHistory(slug, period_type)` | `GET /api/scorecards/{slug}/history?period_type=` |
| `useBenchmarkScorecard(period_type, page)` | `GET /api/scorecards/benchmark` |

### 8.5 New TypeScript types

```typescript
type ScorecardKPIValue = { value: number | null; contributing_ids: string[] }
type ScorecardDimension = { score: number | null; trend: 'rising' | 'stable' | 'declining' | null; kpis: Record<string, ScorecardKPIValue> }
type CompetitorScorecard = {
  id: string; company_id: string; period_type: string
  period_start: string; period_end: string; generated_at: string
  overall_score: number | null; overall_trend: 'rising' | 'stable' | 'declining' | null
  dimension_scores: Record<string, ScorecardDimension>
  top_capabilities: Array<{ capability_key: string; score: number | null }>
  top_moves: Array<{ assessment_id: string; title: string; movement_score: number; signal_class: string }>
  risk_flags: Array<{ assessment_id: string; capability_key: string; movement_strength: string; title: string }>
  watchpoints: string[]
  benchmark_position: { rank: number; percentile: number; total_competitors: number } | null
  contributing_assessment_ids: string[]
  is_current: boolean; scorecard_version: string; routing_version: string
}
type ScorecardExplainAssessment = { assessment_id: string; title: string; movement_score: number; signal_class: string }
type ScorecardExplainDimension = { dimension: string; score: number | null; weight: number; effective_weight: number; weighted_contribution: number | null; top_contributing_assessments: ScorecardExplainAssessment[]; total_contributing: number; kpi_detail: Record<string, ScorecardKPIValue> }
type ScorecardExplain = { overall_score: number | null; dimension_breakdown: ScorecardExplainDimension[]; null_dimensions: string[]; score_formula: string; routing_version: string; scorecard_version: string }
type BenchmarkScorecardItem = { company_id: string; slug: string; name: string; overall_score: number | null; rank: number; percentile: number; dimension_scores: Record<string, ScorecardDimension>; overall_trend: string | null; scorecard_version: string }
type BenchmarkScorecardView = { items: BenchmarkScorecardItem[]; total: number; page: number; page_size: number; pages: number; period_type: string; capability_leaders: Record<string, { company_slug: string; score: number }>; highest_momentum: { company_slug: string; mom_period_delta: number } | null; threat_flags: Array<{ company_slug: string; capability: string; movement_strength: string }> }
```

---

## 9. Testing Strategy

Each layer is tested independently:

- **DimensionRouter** — unit tests: given assessment fields, assert `dimension_targets`, `kpi_targets`, `assessment_weight`. One test per routing rule. Test rule interactions (e.g. `market_expansion_move` with `evidence_strength = 3` vs `= 4`).
- **KPIEngine** — unit tests: pure function inputs → assert output values and contributing_ids. Test null semantics (empty list returns null). Test recency decay edge cases (age_days = 0, age_days = period_days). Test Shannon entropy normalization.
- **ScorecardBuilder** — integration tests with SQLite fixture (same pattern as existing `conftest.py`). Test: build with zero assessments produces null scorecard. Test: is_current flip. Test: benchmark position with single competitor. Test: benchmark position with multiple competitors.
- **API** — HTTP tests via `client` fixture. Test 400 on missing `period_type`. Test 404 on unknown slug. Test explain payload cap (mock assessments > 5 per dimension). Test pagination params.
- **Frontend** — no-data state renders correct copy. Loading state renders skeleton. Period selector updates data fetch. Explainability drawer lazy-loads only on open.

---

## 10. Migration

New Alembic migration required for:
1. New columns on `signal_assessments` (§3.1)
2. New table `competitor_scorecards` (§3.2)

All new `signal_assessments` columns are nullable or have defaults — no data migration needed for existing rows. Existing assessments will be re-routed lazily via `ensure_routed()` on next scorecard build, or via a one-time backfill command.
