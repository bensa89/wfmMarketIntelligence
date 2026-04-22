# V1 Intelligence Layer — Design Spec

**Date:** 2026-04-22
**Scope:** Executive Overview, Competitor Workspace, Signals Feed

## Summary

Extend the existing WFM Market Intelligence Hub with a structured Intelligence Layer on top of Signals. New entities: `SignalAssessment` (per-signal interpretation) and `CompetitorSummary` (aggregated per-competitor view). Three new frontend pages with dedicated routing. Existing pipeline, models, and API endpoints remain unchanged.

## Decisions

| Question | Decision |
|---|---|
| Assessment generation | Hybrid: inline after crawl if `relevance_score >= ASSESSMENT_THRESHOLD` (env-configurable, default 0.4) |
| Existing signals | Backfill via one-time script `backend/scripts/backfill_assessments.py` |
| CompetitorSummary trigger | Auto after crawl (for companies with new signals) + on-demand via POST |
| Frontend integration | New separate pages: `/overview`, `/competitors/:slug`, `/signals` |
| Overall approach | Thin Assessment Layer (Ansatz 1) — minimal invasiveness, no caching needed at V1 scale |

---

## 1. Data Model

### `signal_assessments`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| signal_id | UUID FK → signals.id | UNIQUE, cascade delete |
| company_id | UUID FK → companies.id | Denormalized for fast filtering |
| capability_primary | VARCHAR | One of 16 capability keys |
| capability_secondary | JSONB | Array of capability keys |
| signal_class | VARCHAR | Enum (see below) |
| evidence_strength | SMALLINT | 1–5 |
| visibility_impact | VARCHAR | low \| medium \| high |
| strategic_weight | SMALLINT | Derived from capability metadata |
| movement_score | SMALLINT | Rule-computed (0–100), not LLM |
| movement_strength | VARCHAR | weak \| relevant \| strong \| market_shaping |
| confidence | FLOAT | 0.0–1.0, from LLM |
| strategic_intent_guess | TEXT | |
| gameplay_tags | JSONB | Array of strings |
| assessment_summary | TEXT | 2–3 sentences |
| implication_for_us | TEXT | 1–2 sentences |
| watch_items | JSONB | Array of strings |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**signal_class enum values:**
`product_capability_move | positioning_move | ecosystem_move | thought_leadership_signal | hiring_signal | weak_signal | market_expansion_move`

### `competitor_summaries`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK → companies.id | |
| period_type | VARCHAR | 7d \| 30d \| 90d \| quarter |
| period_start | DATE | |
| period_end | DATE | |
| strategic_posture | VARCHAR | e.g. "aggressive_expansion" |
| positioning_summary | TEXT | |
| top_capabilities | JSONB | Array of capability keys |
| capability_assessment | JSONB | Array of `{key, label, activity_level, notes}` |
| top_risks | JSONB | Array of strings |
| top_opportunities | JSONB | Array of strings |
| watchpoints | JSONB | Array of strings |
| avg_movement_score | FLOAT | |
| signal_count | INTEGER | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

No UNIQUE constraint on `(company_id, period_type)` — newest per period fetched via `ORDER BY created_at DESC LIMIT 1`.

### `CapabilityDefinition` (no DB table)

TypeScript constant (`src/constants/capabilities.ts`) + Python dict (`assessor/capabilities.py`). Same 16 keys on both sides.

**Keys:**
`demand_forecasting | shift_scheduling | intraday_management | time_attendance | compliance_rules | employee_self_service | manager_experience | mobile_experience | analytics_insights | ai_copilot | workflow_automation | integration_hub | platform_ecosystem | vertical_solutions | data_foundation | optimization_engine`

Each entry has: `key, label, visibility_to_user, strategic_weight (1–10), default_evolution_band, description`

---

## 2. Backend Architecture

### New module: `backend/app/assessor/`

```
backend/app/assessor/
├── pipeline.py       # assess_signal(signal, db) → SignalAssessment | None
├── rules.py          # Rule-based pre-scoring + movement_score calculation
├── prompts.py        # System prompt + user prompt template
├── parser.py         # JSON parsing, Pydantic v2 validation, retry logic
├── summarizer.py     # generate_competitor_summary(company, period_type, db)
└── capabilities.py   # CAPABILITIES dict (16 keys + metadata)
```

### Scoring Formula (`rules.py`)

```python
movement_score = round(
    signal.relevance_score * 35       # max 35
  + signal.confidence_score * 20      # max 20
  + evidence_strength * 6             # max 30  (1–5 scale → 6–30)
  + {"low": 0, "medium": 8, "high": 15}[visibility_impact]
  - (10 if signal_class == "thought_leadership_signal" else 0)
)
movement_score = max(0, min(100, movement_score))

# Thresholds
# < 30  → weak
# 30–59 → relevant
# 60–79 → strong
# >= 80 → market_shaping
```

`strategic_weight` is copied from `CAPABILITIES[capability_primary].strategic_weight`.

### Pipeline Integration (`analyser/pipeline.py`)

Single addition after signal is saved:

```python
if signal.relevance_score >= settings.ASSESSMENT_THRESHOLD:
    from app.assessor.pipeline import assess_signal
    assess_signal(signal, db)
```

`ASSESSMENT_THRESHOLD` defaults to `0.4`, overridable via env var.

### New API Endpoints (`routers/intelligence.py`)

```
GET  /api/overview
     Response: {
       top_movers_7d: CompetitorMoverItem[],
       top_movers_30d: CompetitorMoverItem[],
       capability_heatmap: CapabilityHeatmapCell[][],
       recent_market_shaping: SignalWithAssessment[],
       emerging_risks: string[],
       emerging_opportunities: string[]
     }

GET  /api/competitors/{slug}/workspace
     Response: {
       competitor_profile: Company,
       summary_30d: CompetitorSummary | null,
       summary_90d: CompetitorSummary | null,
       recent_assessments: SignalWithAssessment[],
       capability_distribution: CapabilityCount[],
       timeline_of_moves: TimelineEntry[]
     }

GET  /api/signals/feed
     Query params: company_id, capability, signal_type, movement_strength,
                   min_confidence, from_date, to_date, sort_by, page, page_size
     Response: {
       items: SignalFeedItem[],
       total: int,
       page: int,
       page_size: int
     }
     SignalFeedItem includes: signal + assessment + company + source + document (url, title)

POST /api/signals/{id}/assess
     (Re-)generates assessment for one signal. Returns SignalAssessment.

POST /api/competitors/{id}/summarize
     Body: { period_type: "7d"|"30d"|"90d"|"quarter" }
     Generates CompetitorSummary on-demand. Returns CompetitorSummary.
```

Existing endpoints (`/api/signals`, `/api/companies`, etc.) remain **unchanged**.

### Backfill Script (`backend/scripts/backfill_assessments.py`)

- Iterates all signals with `relevance_score >= ASSESSMENT_THRESHOLD` and no existing assessment
- Calls `assess_signal()` for each
- Configurable batch size and concurrency
- Idempotent: safe to run multiple times

### Post-Crawl Summary Trigger

In `routers/crawl.py`, after CrawlRun completes: for each company that received new signals in the run, spawn background thread calling `generate_competitor_summary(company, "7d", db)` and `generate_competitor_summary(company, "30d", db)`.

---

## 3. Frontend Architecture

### New Routes

```
/overview              → OverviewPage
/competitors/:slug     → CompetitorWorkspacePage
/signals               → SignalsFeedPage
```

Existing routes (including `/`) remain unchanged.

### Component Structure

```
src/
├── pages/
│   ├── OverviewPage.tsx
│   ├── CompetitorWorkspacePage.tsx
│   └── SignalsFeedPage.tsx
│
├── components/
│   ├── overview/
│   │   ├── TopMoversList.tsx
│   │   ├── CapabilityHeatmapV2.tsx
│   │   ├── MarketShapingFeed.tsx
│   │   ├── RisksOpportunitiesPanel.tsx
│   │   └── OverviewKPIBar.tsx
│   │
│   ├── workspace/
│   │   ├── CompetitorHeader.tsx
│   │   ├── StrategicPostureCard.tsx
│   │   ├── CapabilityRadar.tsx
│   │   ├── RecentMovesTimeline.tsx
│   │   ├── RisksOpportunitiesCards.tsx
│   │   └── SummaryPeriodTabs.tsx
│   │
│   └── signals/
│       ├── SignalFeedFilters.tsx
│       ├── SignalFeedTable.tsx
│       ├── SignalDetailDrawer.tsx
│       ├── MovementBadge.tsx
│       └── ConfidenceBar.tsx
│
├── hooks/
│   ├── useOverview.ts
│   ├── useCompetitorWorkspace.ts
│   ├── useSignalsFeed.ts
│   ├── useAssessSignal.ts
│   └── useSummarizeCompetitor.ts
│
└── constants/
    └── capabilities.ts
```

### Layout Principles

**OverviewPage** — 60-second scan, no scroll needed for core:
- KPI bar (signal count, avg movement score, active competitors) — full width top
- Top Movers (7d/30d tabs) — left column
- Capability Heatmap V2 (competitor × capability, colored by avg movement_score) — right column
- Market Shaping Feed + Risks/Opportunities — bottom row

**CompetitorWorkspacePage** — Context → Detail:
- CompetitorHeader (name, strategic_posture badge, website link)
- SummaryPeriodTabs (30d / 90d) → StrategicPostureCard + CapabilityRadar side-by-side
- RecentMovesTimeline (chronological assessments)
- RisksOpportunitiesCards (bottom)

**SignalsFeedPage** — Operative work surface:
- SignalFeedFilters sticky at top (competitor, capability, signal_type, movement_strength, confidence range, date range)
- SignalFeedTable paginated: title, company, capability, MovementBadge, ConfidenceBar, date
- Click row → SignalDetailDrawer (slide-in): full assessment, implication_for_us, watch_items, source link, document link
- "Unassessed" state shown for signals without assessment (badge: gray "pending")

### Shared Constants

`src/constants/capabilities.ts` — 16 capability definitions. Used in filter dropdowns, heatmap axes, workspace radar.

---

## 4. LLM Integration

### Assessment Prompt

**System prompt** (low temperature 0.1):
> You are a competitive intelligence analyst for a Workforce Management software company. Return structured JSON only. No prose. No explanation outside the JSON object.

**User prompt template** — includes: company_name, signal_type, title, topic, summary, why_it_matters, relevance_score, confidence_score, internal context (core_capabilities, strategic_priorities, differentiators), available capability_keys, exact JSON schema to return.

**Response schema** (Pydantic v2 `AssessmentLLMOutput`):
```
capability_primary, capability_secondary[], signal_class,
evidence_strength (1–5), visibility_impact (low|medium|high),
strategic_intent_guess, gameplay_tags[], assessment_summary,
implication_for_us, watch_items[], confidence (0.0–1.0)
```

### Competitor Summary Prompt

Aggregates N most recent assessments for a company in the period. Asks LLM to synthesize: `strategic_posture`, `positioning_summary`, `top_capabilities`, `capability_assessment`, `top_risks`, `top_opportunities`, `watchpoints`.

### Parser + Retry (`assessor/parser.py`)

```python
MAX_RETRIES = 2
for attempt in range(MAX_RETRIES + 1):
    raw = call_llm(prompt)
    try:
        return AssessmentLLMOutput.model_validate_json(raw)
    except ValidationError:
        if attempt == MAX_RETRIES:
            log.warning("Assessment parsing failed after retries, signal_id=%s", signal_id)
            return None   # Signal saved without assessment — no crawl crash
```

On failure: signal is saved without assessment. Frontend shows "pending/unassessed" state. No crawl abort.

---

## Assumptions

1. V1 scale: < 50 competitors, < 10,000 signals — no query caching needed (raw SQL joins are fast enough)
2. `movement_score` is always rule-computed, never set by LLM — deterministic, cheap to recompute
3. `competitor_summaries` without UNIQUE constraint allows history; consumers always fetch newest per period
4. CapabilityDefinition is code-only in V1 — no admin UI, no DB table
5. No auth changes — existing HTTP Basic Auth covers all new endpoints
6. Backfill script runs once manually; subsequent assessments are generated inline by pipeline
7. German language in prompts is NOT required for assessments (internal tool, English is fine)
8. `signal_assessments.strategic_weight` is copied from `CAPABILITIES[capability_primary].strategic_weight` at assessment creation time — stored denormalized so the score remains stable if capability metadata changes
9. `gameplay_tags` are free-form strings generated by the LLM (e.g. "land-and-expand", "price-pressure", "ai-narrative") — no fixed enum in V1
10. `emerging_risks` and `emerging_opportunities` in the `/api/overview` response are aggregated from the most recent `competitor_summaries` (per company, newest per period_type=30d), collecting all `top_risks` / `top_opportunities` entries, deduplicating by text similarity (simple exact-match dedup in V1)
