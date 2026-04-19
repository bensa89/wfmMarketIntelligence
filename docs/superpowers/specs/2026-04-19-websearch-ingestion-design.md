# Web Search Ingestion — Design Spec

**Date:** 2026-04-19  
**Status:** Approved

## Overview

Extends the existing crawl-based monitoring system with an AI-driven web search ingestion channel. Web search is not a replacement for crawling — crawling observes known domains, search finds external documents and identifies new potential sources. Both channels feed into the same Document/Signal pipeline.

**Search API:** Tavily  
**Triggering:** Manual (admin clicks "Search Run starten")  
**Query generation:** Fully AI-generated from Company data + InternalCompanyContext  
**Architecture approach:** Hybrid — SearchResult with optional Document link (Option C)

---

## Data Model

### New Tables

**SearchQuery**
```
id (UUID, PK)
query_text (str)
company_id (UUID FK → Company, nullable)   -- null for trend queries
topic (str, nullable)                       -- free-text for trend queries
search_intent (str)                         -- e.g. "ai_announcement", "partnership"
generated_at (datetime)
```

**SearchRun**
```
id (UUID, PK)
search_query_id (UUID FK → SearchQuery)
executed_at (datetime)
status (enum: pending | running | done | error)
result_count (int, nullable)
error_message (str, nullable)
```

**SearchResult**
```
id (UUID, PK)
search_run_id (UUID FK → SearchRun)
title (str)
url (str, indexed)
domain (str)
snippet (str)
discovered_at (datetime)
relevance_score (float, nullable)           -- from Tavily score
processing_status (enum: pending | fetched | skipped | error)
linked_document_id (UUID FK → Document, nullable)
```

**SourceCandidate**
```
id (UUID, PK)
url (str)
domain (str)
title (str)
snippet (str)
found_via_query (str)                       -- the query_text that surfaced this domain
company_id (UUID FK → Company, nullable)
source_type_guess (SourceType enum)
relevance_score (float)
status (enum: candidate | approved | rejected | monitored)
created_at (datetime)
```

### Existing Table Modification

**Document** — add one column:
```
from_search (bool, default False)
```

Marks whether a Document was ingested via web search rather than crawling.

---

## Backend Pipeline

### Module: `backend/app/searcher/`

```
searcher/
  __init__.py
  query_generator.py   -- LLM call: Company + Context → list of SearchQuery objects
  client.py            -- Tavily API wrapper
  pipeline.py          -- Orchestration: generate → search → evaluate → fetch → analyse → candidates
```

### Router: `backend/app/routers/search.py` → `/api/search/`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/search/run` | Run search for all active companies + trends |
| POST | `/api/search/run/{company_id}` | Run search for single company |
| GET | `/api/search/runs` | List SearchRuns (filter: company_id, status) |
| GET | `/api/search/results` | List SearchResults (filter: run_id, status, company_id) |
| GET | `/api/source-candidates` | List SourceCandidates (filter: status, company_id) |
| POST | `/api/source-candidates/{id}/approve` | Approve candidate → create Source, set status=monitored |
| POST | `/api/source-candidates/{id}/reject` | Reject candidate → set status=rejected |

### Flow Detail

```
POST /api/search/run
  for each active Company:
    1. query_generator.py → LLM call → list of (query_text, search_intent)
    2. Save SearchQuery records
    3. For each query:
       a. client.py → Tavily search → raw results
       b. Save SearchRun (status=running)
       c. For each result:
          - Save SearchResult (title, url, domain, snippet, relevance_score)
          - If relevance_score >= settings.search_relevance_threshold (default 0.5):
              - URL already in Document table? → set linked_document_id, skip fetch
              - Else: fetch → extract → dedup via content_hash → Document(from_search=True)
                      → analyse_document() → Signal
          - Else: processing_status = "skipped"
          - Domain not in active Sources AND not already a SourceCandidate?
              → create SourceCandidate(status=candidate)
       d. Update SearchRun(status=done, result_count=N)

  + one additional run for trend queries (company_id=null):
    - Based on InternalCompanyContext.relevant_competitive_areas
    - Same flow, no company_id on SearchQuery/SourceCandidate
```

### `query_generator.py`

Single LLM call per company. Prompt includes:
- Company name, type, website
- InternalCompanyContext fields: target_industries, core_capabilities, strategic_priorities, relevant_competitive_areas
- Instruction to generate 6–10 queries covering intents: product_update, ai_announcement, partnership, pricing, hiring, event, analyst_coverage, positioning

Output JSON schema:
```json
[
  {"query_text": "Quinyx AI scheduling 2025", "search_intent": "ai_announcement"},
  {"query_text": "Quinyx partnership announcement", "search_intent": "partnership"}
]
```

Separate call for trend queries: generates 4–6 generic WFM market queries from `relevant_competitive_areas`.

Configurable via `settings.search_queries_per_company` (default 8).

### `client.py`

Thin Tavily wrapper:
```python
search(query: str) -> list[TavilyResult]
```
`TavilyResult`: title, url, content (used as snippet), score, raw_content (optional full text).

Uses `TAVILY_API_KEY` from settings/env.

### Dedup Behaviour

- URL already in Document → link `SearchResult.linked_document_id`, set `processing_status=fetched`, no re-analysis
- Same content_hash as existing Document → standard dedup path (already handled by existing pipeline)
- Domain already has an active Source → no SourceCandidate created
- Domain already has a SourceCandidate (any status) → no duplicate created

### Error Handling

- Tavily API error on a single run → SearchRun(status=error, error_message=...), continue other queries
- Fetch/extract error on a result → SearchResult(processing_status=error), continue
- LLM analysis error → same handling as existing analyser (exception logged, document saved without signal)
- Query generation failure → skip that company, log error

---

## Frontend

### New Page: `/search`

New nav entry "Search" between "Sources" and "Weekly Digest".

**Tab 1 — Search Runs**
- "Search Run starten" button → `POST /api/search/run`, shows loading state
- Table of recent SearchRuns: date, company, status badge, result count
- Row expand → SearchResults list with per-result status badge (fetched / skipped / error) and clickable URL

**Tab 2 — Source Candidates**
- Status filter tabs: All / Candidate / Approved / Rejected
- Per candidate: domain, title, snippet, company, relevance score, guessed source type, status badge
- Actions:
  - "Approve" → dialog to confirm/edit source label + source type → `POST /api/source-candidates/{id}/approve` → creates Source record
  - "Reject" → `POST /api/source-candidates/{id}/reject`

### Dashboard Extension

Signal cards get a small source badge: "Crawl" or "Search" based on `Document.from_search`. No additional filter required in v1.

### New Types (`frontend/src/types/index.ts`)

```typescript
SearchRunStatus = 'pending' | 'running' | 'done' | 'error'
SearchResultStatus = 'pending' | 'fetched' | 'skipped' | 'error'
SourceCandidateStatus = 'candidate' | 'approved' | 'rejected' | 'monitored'

SearchQuery { id, query_text, company_id, topic, search_intent, generated_at }
SearchRun { id, search_query_id, executed_at, status, result_count, error_message }
SearchResult { id, search_run_id, title, url, domain, snippet, discovered_at, relevance_score, processing_status, linked_document_id }
SourceCandidate { id, url, domain, title, snippet, found_via_query, company_id, source_type_guess, relevance_score, status, created_at }
```

### New Hooks

```
useRunSearch()            -- POST /api/search/run mutation
useRunSearchForCompany()  -- POST /api/search/run/{company_id} mutation
useSearchRuns()           -- GET /api/search/runs
useSearchResults()        -- GET /api/search/results
useSourceCandidates()     -- GET /api/source-candidates
useApproveCandidate()     -- POST /api/source-candidates/{id}/approve
useRejectCandidate()      -- POST /api/source-candidates/{id}/reject
```

---

## Configuration

New env/settings fields:
```
TAVILY_API_KEY              (required)
SEARCH_RELEVANCE_THRESHOLD  (float, default 0.5)
SEARCH_QUERIES_PER_COMPANY  (int, default 8)
```

---

## Integration Principles

- `searcher/` module is a peer of `crawler/` and `analyser/` — no cross-imports, communicates via shared DB session and calling `analyser.pipeline.analyse_document()`
- `Document.from_search` is the only modification to existing models
- Source Candidate approval reuses existing Source creation logic from `routers/sources.py`
- Existing crawl/discovery pipeline is untouched

---

## Out of Scope (v1)

- Scheduled/automatic search runs (cron-based)
- SSE streaming progress for search runs (returns synchronously like original `/api/crawl/run`)
- Per-result manual re-analysis trigger
- Search query editing in frontend (queries are fully AI-generated)
- Deduplication of SourceCandidates across runs beyond domain-level check
