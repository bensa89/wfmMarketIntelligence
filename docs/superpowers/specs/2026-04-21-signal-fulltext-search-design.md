# Signal Full-Text Search Design

## Goal

Add full-text search to the Signals listing, covering all signal text fields plus metadata (source URL, document title). Integrated into the existing `GET /api/signals` endpoint and the existing `FilterBar` UI component.

## Approach

PostgreSQL Full-Text Search (FTS) with `tsvector`/`tsquery`, GIN index, and `unaccent` extension. No external search engine dependency.

## Database Changes

### Alembic Migration

1. Enable `unaccent` extension (`CREATE EXTENSION IF NOT EXISTS unaccent`)
2. Add `search_vector` column of type `TSVECTOR` to `signals` table
3. Create GIN index `ix_signals_search_vector` on `signals.search_vector`
4. Add PostgreSQL trigger `trg_signals_search_vector_update` that automatically refreshes `search_vector` on INSERT or UPDATE

### Search Vector Composition

The trigger builds the search vector from these fields with PostgreSQL weights:

| Field | Source | Weight |
|---|---|---|
| title | `signals.title` | A (highest) |
| topic | `signals.topic` | B |
| summary | `signals.summary` | B |
| why_it_matters | `signals.why_it_matters` | C |
| source_url | `documents.url` | D |
| document_title | `documents.title` | D |

The trigger function uses `setweight(to_tsvector('german', unaccent(COALESCE(field, ''))), weight)` and concatenates all with `||`.

Since `document.url` and `document.title` live on the `documents` table, the trigger performs a `SELECT url, title FROM documents WHERE id = NEW.document_id` to access those fields. The trigger fires on signal INSERT or UPDATE, looking up the related document.

### Text Search Configuration Language

Using `'german'` as the FTS configuration since the UI is in German and most competitor content is German-language. If the content mix shifts to primarily English, this should be changed to `'english'`. The `unaccent` extension handles Umlaut normalization regardless of language config.

### Initial Backfill

The migration includes a one-time `UPDATE signals SET search_vector = ...` to populate existing rows.

## API Changes

### `GET /api/signals` — New Query Parameter

| Parameter | Type | Description |
|---|---|---|
| `q` | `Optional[str]` | Full-text search query |

When `q` is provided:

- Convert to `plainto_tsquery('german', unaccent(q))`
- Filter with `Signal.search_vector.op('@@')(query)`
- Sort by `ts_rank(search_vector, query) DESC`, then `created_at DESC`
- Existing filters (`company_id`, `signal_type`, `min_relevance`, `max_age_days`) combine with AND

When `q` is not provided, behavior is unchanged (sort by `created_at DESC`).

### Additional Filter

| Parameter | Type | Description |
|---|---|---|
| `min_confidence` | `Optional[float]` | Minimum confidence score threshold |

This filter was missing and is added alongside the search feature.

### Schema Changes

- `SignalsFilters` (used by `useSignals` hook): add `q?: string`, `min_confidence?: number`
- `SignalRead`: no changes needed (already includes `source_url` and `from_search`)

## Backend Implementation

### `backend/app/routers/signals.py`

In the `list_signals` endpoint:

```python
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TSVECTOR

if q:
    query_expr = func.plainto_tsquery('german', func.unaccent(q))
    stmt = stmt.where(Signal.search_vector.op('@@')(query_expr))
    stmt = stmt.order_by(
        func.ts_rank(Signal.search_vector, query_expr).desc(),
        Signal.created_at.desc()
    )
```

The `selectinload(Signal.document)` is already present for `source_url` enrichment — no additional eager loading needed for the search vector itself.

### `backend/app/models/signal.py`

Add `search_vector` column:

```python
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import TSVECTOR

search_vector = Column(TSVECTOR, nullable=True)
```

### `backend/app/schemas/signal.py`

No changes to `SignalRead`. The `q` parameter is a query param, not a schema field.

## Frontend Changes

### `FilterBar` Component

Add a text search input at the top of the FilterBar:

- Input field with search icon, placeholder "Signale durchsuchen..."
- Debounced (300ms) — updates `q` filter param only after pause
- Clear button (X) appears when text is present
- Controlled component: `value` bound to filter state

### `useSignals` Hook

Update `SignalsFilters` interface:

```typescript
interface SignalsFilters {
  company_id?: string;
  signal_type?: SignalType;
  min_relevance?: number;
  min_confidence?: number;  // new
  max_age_days?: number;
  q?: string;               // new
}
```

Pass `q` and `min_confidence` as query parameters in the API call.

### Page Integration

No changes needed in `Dashboard.tsx`, `CompetitorDetail.tsx`, or `MarketTrends.tsx` — they all use `FilterBar` and `useSignals`, so the search propagates automatically.

## Data Flow

1. User types search term in FilterBar
2. After 300ms debounce, `q` is added to filters
3. `useSignals` sends `GET /api/signals?q=...` (plus existing filters)
4. Backend converts `q` to `plainto_tsquery('german', unaccent(q))`
5. PostgreSQL matches against `search_vector` using GIN index
6. Results ranked by `ts_rank`, returned as normal signal list
7. Frontend renders results in existing signal tables/cards

## Testing

### Backend Tests

- Test `GET /api/signals?q=` returns all signals (empty search = no filter)
- Test `GET /api/signals?q=keyword` returns only matching signals
- Test search combined with `company_id`, `signal_type`, `min_relevance` filters
- Test `min_confidence` filter
- Test ranking: signals with keyword in title rank higher than in summary
- Test `unaccent`: "hiring" matches "Hire", Umlaut handling

Note: SQLite test fixtures cannot use FTS. Tests requiring FTS logic must use PostgreSQL or mock the tsquery behavior. Integration tests should use the running dev PostgreSQL.

### Frontend Tests

- FilterBar renders search input
- Debounce works (300ms delay before API call)
- Clear button resets search
- `useSignals` passes `q` parameter to API