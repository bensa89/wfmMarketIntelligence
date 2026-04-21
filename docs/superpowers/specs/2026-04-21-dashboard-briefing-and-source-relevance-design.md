# Design: LLM Dashboard Briefing & Discovered Page Auto-Ignore

## Overview

Two features to reduce signal overload and improve source quality management:

1. **LLM Dashboard Briefing** — A Claude-generated summary after each crawl (and on-demand) that synthesizes the most important developments and tells the user what to focus on.
2. **Discovered Page Auto-Ignore** — After a discovered page is analyzed, if all resulting signals have relevance < 0.3, the page is automatically marked inactive. Relevance is surfaced on the Sources admin page.

---

## Feature 1: LLM Dashboard Briefing

### Model

New table `crawl_briefings`:

| Field | Type | Notes |
|---|---|---|
| `id` | String(36) UUID | PK |
| `crawl_run_id` | String(36) FK nullable | Links to `CrawlRun`, null for manually triggered briefings |
| `content` | Text | LLM-generated markdown briefing |
| `generated_at` | DateTime | UTC timestamp |

### Backend

**New router** `backend/app/routers/briefings.py` mounted at `/api/briefings`:

- `GET /latest` — Returns the most recently generated briefing ordered by `generated_at DESC` (or 404 if none exists)
- `POST /generate` — Generates a new briefing using Claude. Accepts optional `crawl_run_id` in body.

**LLM context assembled for each generation:**
- New signals since the last crawl (count, breakdown by company)
- Top 10 signals by relevance score (title, company, signal_type, relevance_score, why_it_matters)
- Most active company (highest new signal count)
- Signal type distribution across new signals
- New vs. changed document counts from the last crawl

**Prompt goal:** "Summarize the most important market intelligence developments. What changed, who is most active, what should I look at first?"

**Auto-trigger:** In `backend/app/routers/crawl.py`, after the crawl run loop completes, call the briefing generation logic internally (not via HTTP, direct function call).

### Frontend

**New component** `frontend/src/components/dashboard/BriefingPanel.tsx`:
- Placed in the left column of the dashboard, below `CrawlSummaryCard`
- Renders the `content` field as markdown (reuse `MarkdownViewer`)
- Shows `generated_at` timestamp
- "Neu generieren" button that calls `POST /api/briefings/generate` with loading state
- Shows placeholder text if no briefing exists yet

**New hook** `frontend/src/hooks/useBriefing.ts` wrapping `GET /latest` and `POST /generate`.

---

## Feature 2: Discovered Page Auto-Ignore

### Model Change

Add field to `discovered_pages` table:

| Field | Type | Notes |
|---|---|---|
| `last_signal_relevance` | Float nullable | Max relevance_score across all signals for this page's document |

Requires a new Alembic migration.

### Pipeline Logic

In `backend/app/crawler/discovery.py`, after `_save_and_analyse` for both new and changed pages:

1. Find the `Document` for the discovered page URL
2. Query all `Signal` records for that document
3. If signals exist AND all `relevance_score < 0.3`:
   - Set `DiscoveredPage.is_active = False`
   - Set `DiscoveredPage.status = DiscoveredPageStatus.ignored`
4. Set `DiscoveredPage.last_signal_relevance = max(signal.relevance_score for signal in signals)` (or None if no signals)

The check runs directly after first crawl — no minimum crawl count required.

### Frontend — Sources Admin Page

The Sources admin page should display per-source discovered pages with:

- `last_signal_relevance` shown as a colored badge:
  - Green (≥ 0.3): relevant
  - Red (< 0.3): low relevance
  - Grey (null): not yet analyzed
- Pages with `is_active=False` and auto-ignored status show an "Auto-ignoriert" chip
- Existing manual re-activate toggle remains functional via `PATCH /api/discovered-pages/{id}`

The `DiscoveredPageRead` schema needs `last_signal_relevance` added.

---

## Data Flow Summary

### Briefing Generation
```
Crawl completes
  → assemble signal stats from DB
  → call Claude API with context
  → persist CrawlBriefing
  → GET /latest returns it to dashboard
```

### Discovered Page Relevance Check
```
discover_and_crawl finds new/changed page
  → _save_and_analyse creates Document + calls analyser
  → analyser creates Signal(s) with relevance_score
  → check: all signals for this document < 0.3?
    → yes: is_active=False, status=ignored
    → no: keep active
  → set last_signal_relevance = max(relevance scores)
```

---

## Out of Scope

- Deduplication between listing-page signals and sub-page signals (separate concern)
- Batch retroactive re-evaluation of existing discovered pages
- Briefing history UI (only latest briefing shown)
