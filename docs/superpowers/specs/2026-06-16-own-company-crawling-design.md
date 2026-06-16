# Design: Own Company Crawling + ExternalCompanyView

**Date:** 2026-06-16  
**Status:** Approved

## Goal

Allow the own company to be crawled like competitors, generating an "outside view" of external communication. This view serves two purposes:

1. **Dynamic context enrichment** — a LLM-synthesized `ExternalCompanyView` supplements the manually maintained `InternalCompanyContext` when analyzing competitor signals.
2. **Direct comparison** — the own company appears in `/competitors` with the same scorecard metrics, and in the digest with a dedicated "Unsere externe Kommunikation" section.

The manual `InternalCompanyContext` is not replaced — it remains authoritative for internal knowledge (strategy, non-public capabilities). The `ExternalCompanyView` adds what the world actually sees.

---

## Architecture Overview

```
Own website crawled → Documents
    ↓ (adapted analysis prompt)
Signals (company.type = own_company)
    ↓ (existing assessor pipeline)
SignalAssessments → CompetitorScorecard
    ↓                    ↓
Digest section      Scorecard + Benchmark
"Unsere Kommunikation"  (with "Wir" badge)
    ↓
ExternalCompanyView (LLM synthesis)
    ↓
Injected into competitor analysis prompts
```

---

## 1. Data Model Changes

### 1a. CompanyType Enum

Add `own_company` as a third value alongside `competitor` and `market_source`.

**Migration note:** PostgreSQL requires `ALTER TYPE ... ADD VALUE`. This cannot be run inside a transaction, so the Alembic migration must use `op.execute()` with `connection.execution_options(isolation_level="AUTOCOMMIT")`. A data migration step in the same migration updates the existing own-company row from `competitor` → `own_company`.

### 1b. New model: `ExternalCompanyView` (singleton)

Table: `external_company_view`

| Column | Type | Notes |
|---|---|---|
| `id` | String(36) | UUID PK |
| `summary` | Text | LLM-synthesized overview of external presence |
| `key_messages` | JSON | Core messages extracted from public content |
| `observed_capabilities` | JSON | Capabilities inferred from public content |
| `observed_differentiators` | JSON | Differentiators as communicated externally |
| `observed_target_markets` | JSON | Target markets as communicated externally |
| `tone_and_positioning` | Text | Tone, style, and positioning observations |
| `signal_count_used` | Int | Number of own-company signals used in synthesis |
| `generated_at` | DateTime | When synthesis was last run |
| `updated_at` | DateTime | Auto-updated on save |

Accessed as singleton (same pattern as `InternalCompanyContext`).

---

## 2. Analysis Pipeline Changes

### 2a. Adapted prompt for own-company content

New function `build_self_analysis_prompt(markdown, context)` in `analyser/prompts.py`.

Same JSON output schema as the existing prompt (no parser changes needed). Different framing:
- System role: "You are analyzing your own company's external communication"
- `why_it_matters` → "what this reveals about our external positioning"
- `relevance_score` → strategic significance of this message (0–1)
- `signal_type`, `topic`, `summary`, all other fields: identical semantics

### 2b. Pipeline dispatch

In `analyser/pipeline.py`: detect `document.source.company.type == CompanyType.own_company` → use `build_self_analysis_prompt()` instead of the standard prompt.

---

## 3. Synthesis Pipeline (new)

New module: `synthesizer/` (or added to `assessor/`).

### 3a. Prompt

`build_synthesis_prompt(signals: list[Signal]) -> str`

Takes N recent own-company signals and instructs the LLM to synthesize a structured `ExternalCompanyView`. Output: JSON matching `ExternalCompanyView` fields.

### 3b. Pipeline

`run_synthesis(db) -> ExternalCompanyView`
- Fetches all own-company signals (ordered by `created_at` desc, capped at a reasonable limit, e.g. 100)
- Calls LLM with synthesis prompt
- Upserts the `ExternalCompanyView` singleton

### 3c. Triggers

| Trigger | Mechanism |
|---|---|
| Manual | `POST /api/context/synthesize-external-view` |
| Automatic | End of `crawl/pipeline.py` full-crawl run: if any new own-company signals were created → call `run_synthesis()` |

---

## 4. Context Enrichment in Competitor Analysis

`build_analysis_prompt(markdown, context, external_view=None)` in `analyser/prompts.py` gains an optional `external_view` parameter.

If `ExternalCompanyView` exists, a second context block is appended to the prompt:

```
Our External Presence (how we appear publicly):
Key Messages: ...
Observed Capabilities: ...
Observed Differentiators: ...
Observed Target Markets: ...
Tone & Positioning: ...
```

The analyser pipeline fetches `ExternalCompanyView` before building competitor analysis prompts and passes it in.

---

## 5. Scorecard Integration

- `recompute-all` in `routers/scorecards.py` (line 290): extend filter to include `own_company` alongside `competitor`.
- `benchmark/aggregation.py` and `benchmark/queries.py`: same filter extension.
- `ScorecardBuilder` already works on any `company_id` — no changes needed.
- The own company will appear in the benchmark ranking with the same score dimensions as competitors.

---

## 6. Digest Changes

### 6a. Digest candidates / events

`digester/candidates.py` and `digester/events.py` currently filter on `CompanyType.competitor`. These filters stay as-is — own-company signals are intentionally excluded from the competitor signal sections.

### 6b. New digest section: "Unsere externe Kommunikation"

New function in `digester/` that queries signals where `company.type = own_company` within the digest period. Rendered as a dedicated section in the digest.

---

## 7. API Changes

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/context/synthesize-external-view` | Trigger LLM synthesis of ExternalCompanyView |
| `GET` | `/api/context/external-view` | Fetch current ExternalCompanyView |

Existing `/api/companies`, `/api/scorecards`, `/api/signals` endpoints work unchanged — they are company-type-agnostic.

---

## 8. Frontend Changes

### Context page
- New "Außensicht" panel showing `ExternalCompanyView` fields (read-only, generated content).
- "Außensicht aktualisieren" button → `POST /api/context/synthesize-external-view`.
- Shows `generated_at` timestamp and `signal_count_used`.

### Competitors list (`/competitors`)
- Own company included in list.
- Visual "Wir" badge (distinct color) to differentiate from competitors.
- Own company pinned to top of list or visually separated.

### Competitor detail (`/competitors/<own-slug>`)
- Full scorecard detail page, identical to competitor pages.
- No structural changes needed.

### Digest
- New "Unsere externe Kommunikation" section rendered below or alongside competitor sections.

---

## 9. Migration Plan

1. Alembic migration:
   - Add `own_company` to `CompanyType` enum (AUTOCOMMIT required).
   - Create `external_company_view` table.
   - Data migration: update existing own-company row `type = competitor → own_company`.

2. No existing signals, documents, or sources are affected — all linked by `company_id` UUID.

---

## Out of Scope

- Scheduling / automatic crawl triggers for own company (uses existing crawl infrastructure).
- Replacing `InternalCompanyContext` with `ExternalCompanyView` — both coexist intentionally.
- Per-signal diff between internal and external perception (possible future feature).
