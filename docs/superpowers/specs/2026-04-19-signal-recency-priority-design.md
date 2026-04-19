# Signal Recency Priority & Cleanup

**Date:** 2026-04-19
**Status:** Approved

## Problem

Signals have no recency awareness — crawling processes all sources equally, the LLM prompt ignores timeliness, `published_at` is never populated, and old signals accumulate indefinitely. Signals older than 1 year are not useful and should be removed.

## Design Decisions

- **Hard delete** for signals older than 1 year (no soft filter / historical archive)
- **Crawl priority** based on `last_crawled_at` (oldest/never-crawled first)
- **Recency in relevance_score** — LLM prompt instructs the model to factor timeliness into the existing `relevance_score` field (no new fields)
- **Default API filter** `max_age_days=365` on signal listing endpoints

## Changes

### 1. Signal API: Date Filter & Default Cutoff

**`GET /api/signals`** gains two new query parameters:

- `max_age_days` (int, default=365) — filters out signals where `created_at` is older than N days. Pass `0` to disable.
- Sort order remains `created_at desc`.

Implementation in `backend/app/routers/signals.py`:

```python
from datetime import datetime, timezone, timedelta

@router.get("", response_model=List[SignalRead])
def list_signals(
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    min_relevance: Optional[float] = None,
    max_age_days: Optional[int] = 365,
    db: Session = Depends(get_db),
):
    query = db.query(Signal).options(selectinload(Signal.document))
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_relevance is not None:
        query = query.filter(Signal.relevance_score >= min_relevance)
    if max_age_days and max_age_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        query = query.filter(Signal.created_at >= cutoff)
    signals = query.order_by(Signal.created_at.desc()).all()
    return [_to_signal_read(s) for s in signals]
```

### 2. Hard Delete Endpoint

**`DELETE /api/signals/purge?older_than_days=365`**

Deletes all signals (and their cascading documents) older than N days. Returns a count of deleted records.

```python
@router.delete("/purge")
def purge_old_signals(
    older_than_days: int = 365,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    old_signals = db.query(Signal).filter(Signal.created_at < cutoff).all()
    deleted_signals = len(old_signals)
    for signal in old_signals:
        db.delete(signal)
    db.commit()
    return {"deleted_signals": deleted_signals, "older_than_days": older_than_days}
```

Must be defined **before** the `/{signal_id}` route to avoid path conflicts.

### 3. Crawl Priority by Recency

In `backend/app/crawler/pipeline.py` and `backend/app/routers/crawl.py`:

When fetching all active sources, sort by `last_crawled_at` ascending with nulls first, so never-crawled or long-untouched sources are processed first.

```python
active_sources = (
    db.query(Source)
    .filter(Source.is_active == True)
    .order_by(Source.last_crawled_at.asc().nullsfirst())
    .all()
)
```

Applies to:
- `crawl_all_sources()` in `crawl.py`
- Source ID list in `_sse_generator` in `crawl.py`
- Any other place `Source.is_active == True` queries are used for crawl ordering

### 4. Analyser Prompt: Recency in relevance_score

Add to `build_analysis_prompt()` in `backend/app/analyser/prompts.py`:

```
Also consider recency: more recent developments should receive a higher relevance_score than older, stale information.
```

This goes in the instruction text, not in the JSON schema.

### 5. Populate `published_at` on Signal

In `backend/app/analyser/pipeline.py`, set `published_at` on the new Signal:

```python
signal = Signal(
    document_id=doc.id,
    company_id=company_id,
    title=signal_data.title,
    signal_type=signal_data.signal_type,
    topic=signal_data.topic,
    summary=signal_data.summary,
    why_it_matters=signal_data.why_it_matters,
    relevance_score=signal_data.relevance_score,
    confidence_score=signal_data.confidence_score,
    published_at=doc.published_at or doc.crawled_at,
)
```

### 6. LLM JSON Schema: Optional `published_at`

Update the prompt's JSON schema to include an optional `published_at` field:

```
"published_at": "ISO-8601 date string of when the content was originally published, or null if unknown"
```

Update `backend/app/analyser/parser.py` `SignalData` to include `published_at: Optional[str] = None`, and parse it into a datetime if present.

### 7. Migrations

No schema changes required — `Signal.published_at` and `Document.published_at` already exist. All changes are logic-only.

## Data Flow

1. **Crawl**: Sources sorted by `last_crawled_at` (oldest/never first)
2. **Document**: `published_at` extracted from HTML when available
3. **Analysis**: Prompt mentions recency; LLM may provide `published_at`
4. **Signal**: `published_at = doc.published_at or doc.crawled_at`
5. **API list**: Default filter `max_age_days=365`
6. **Cleanup**: `DELETE /api/signals/purge` removes old data

## Out of Scope

- Automatic/scheduled purge (manual endpoint suffices for now)
- Decay functions on relevance_score
- New database columns or migrations
- Frontend changes