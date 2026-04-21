# Signal Deduplication Design

## Problem

Crawling overview pages (e.g. `haufe.de/personal/`) creates a Signal from the overview content (teaser summaries). Discovery then finds linked detail articles (e.g. `haufe.de/personal/hr-management/employer-branding...html`), crawls them, and creates another Signal for the same topic — but with more depth. This produces duplicate Signals covering the same event/change.

Additional issue: `analyse_document()` has no guard against creating multiple Signals for the same Document (e.g. on re-analysis after content change or manual re-trigger).

## Solution: Three-Part Approach

### Part 1: Overview Page Detection in Pipeline

**What:** Apply `_is_article_content()` check to the Source main page before analysis.

**Where:** `backend/app/crawler/pipeline.py` — `run_crawl_source()`

**Logic:**
```
Source crawled → Fetch → Extract → _is_article_content(html)?
  ├── Yes → analyse + Discovery (current behavior)
  └── No  → Discovery only, skip analysis, no Signal created
```

**Implementation:**
- Import `_is_article_content` from `app.crawler.discovery` into `pipeline.py`
- After extraction, before calling `analyse_document()`, check `_is_article_content(fetch_result.html)`
- If false: set `source.crawl_status = CrawlStatus.known` (or new status), skip analysis, proceed to Discovery
- Discovery pages already use `_is_article_content()` — no change needed there

### Part 2: document_id Dedup Guard in analyse_document()

**What:** Prevent creating multiple Signals for the same Document.

**Where:** `backend/app/analyser/pipeline.py` — `analyse_document()`

**Logic:**
- Before `db.add(signal)`, query: `db.query(Signal).filter(Signal.document_id == doc.id).first()`
- If a Signal already exists for this `document_id` → skip creation, just set `doc.is_analysed = True`
- This is a simple safety net, not semantic dedup

### Part 3: LLM Merge Endpoint

**What:** Manual cleanup endpoint that uses LLM to identify and merge duplicate Signals.

**Endpoint:** `POST /api/signals/deduplicate`

**Query params:** `company_id` (required), `max_age_days` (optional, default 90)

**New files:**
- `backend/app/analyser/dedup.py` — core dedup logic + LLM prompt
- Updated `backend/app/routers/signals.py` — new endpoint

**Flow:**
1. Load all Signals for `company_id` within `max_age_days`, ordered by `relevance_score DESC`
2. If > 100 Signals: batch into groups of 100
3. For each batch, send to LLM:
   ```
   You are analyzing market intelligence signals for duplicates.
   
   Signals:
   1. [uuid1] "Title1" | summary1 | relevance: 0.8 | topic: X
   2. [uuid2] "Title2" | summary2 | relevance: 0.6 | topic: Y
   ...
   
   Find groups of signals that describe the same underlying event, announcement, or change.
   Two signals are duplicates if they refer to the same specific occurrence, even with different wording.
   Signals about similar but distinct events are NOT duplicates.
   
   Return JSON only:
   {"merge_groups": [["uuid1", "uuid2"], ["uuid3", "uuid4", "uuid5"]]}
   ```
4. For each merge group: keep the Signal with the highest `relevance_score`, merge better fields from others if applicable, delete the rest
5. Return: `{merged_count: N, removed_ids: [...], kept_signals: [...]}`

**Merge logic per group:**
- Primary Signal = highest `relevance_score`
- For `summary` and `why_it_matters`: keep whichever is longer/more detailed (by word count)
- Delete all other Signals in the group
- Return list of kept Signals with their final state

**Error handling:**
- LLM call failure → return error, no data changed
- Parse failure → return error with raw LLM response for debugging
- No duplicates found → return `{merged_count: 0, removed_ids: [], kept_signals: []}`

## Files to Change

| File | Change |
|------|--------|
| `backend/app/crawler/pipeline.py` | Import `_is_article_content`, add check before analysis |
| `backend/app/analyser/pipeline.py` | Add `document_id` dedup guard in `analyse_document()` |
| `backend/app/analyser/dedup.py` | New file: LLM dedup prompt + merge logic |
| `backend/app/routers/signals.py` | Add `POST /deduplicate` endpoint |
| `backend/app/schemas/signal.py` | Add `DedupResult` response schema |

## Edge Cases

- **Source page has 0 words:** `_is_article_content()` returns `False` → no Signal, Discovery still runs
- **Source page is a real article:** `_is_article_content()` returns `True` → analyzed as before
- **Empty Signals table:** dedup endpoint returns `{merged_count: 0}`
- **All Signals are unique:** LLM returns empty `merge_groups` → no changes
- **Re-analysis after content change:** `document_id` dedup prevents second Signal; existing Signal should be updated (future improvement, not in scope)