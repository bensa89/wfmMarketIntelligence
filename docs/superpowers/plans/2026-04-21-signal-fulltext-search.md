# Signal Full-Text Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PostgreSQL full-text search to the Signals API and a search input to the existing FilterBar, enabling keyword search across signal text fields and document metadata (source URL, document title).

**Architecture:** PostgreSQL `tsvector`/`tsquery` with GIN index on the `signals` table. A database trigger keeps the `search_vector` column in sync. The existing `GET /api/signals` endpoint gains a `q` query parameter. On the frontend, the `FilterBar` gets a debounced search input that feeds the `q` param through `useSignals`.

**Tech Stack:** PostgreSQL FTS (unaccent extension, tsvector, GIN index, triggers), SQLAlchemy 2.0, Alembic, FastAPI, React 18, TanStack Query, TypeScript

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/alembic/versions/<hash>_add_signal_search_vector.py` | Migration: add tsvector column, GIN index, trigger, backfill |
| Modify | `backend/app/models/signal.py` | Add `search_vector` column definition |
| Modify | `backend/app/routers/signals.py` | Add `q` and `min_confidence` params to `list_signals` |
| Modify | `backend/app/schemas/signal.py` | No changes needed (SignalRead already has source_url) |
| Modify | `frontend/src/hooks/useSignals.ts` | Add `q` and `min_confidence` to `SignalsFilters` |
| Modify | `frontend/src/components/FilterBar.tsx` | Add search input with debounce and clear button |
| Create | `backend/tests/test_signal_search.py` | Integration tests for search endpoint (PostgreSQL) |
| Modify | `backend/tests/conftest.py` | Add `pg_client` fixture for PostgreSQL-dependent tests |

---

### Task 1: Add `search_vector` Column to Signal Model

**Files:**
- Modify: `backend/app/models/signal.py`

- [ ] **Step 1: Add the TSVECTOR column to the Signal model**

In `backend/app/models/signal.py`, add the import and column:

```python
from sqlalchemy.dialects.postgresql import TSVECTOR
```

Add after the `created_at` column definition:

```python
    search_vector = Column(TSVECTOR, nullable=True)
```

- [ ] **Step 2: Verify syntax by importing the model**

Run: `cd backend && python -c "from app.models.signal import Signal; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/signal.py
git commit -m "feat: add search_vector TSVECTOR column to Signal model"
```

---

### Task 2: Create Alembic Migration for FTS Infrastructure

**Files:**
- Create: `backend/alembic/versions/<hash>_add_signal_search_vector.py`

- [ ] **Step 1: Generate the migration file**

Run: `cd backend && alembic revision --autogenerate -m "add_signal_search_vector"`

- [ ] **Step 2: Edit the generated migration to include trigger function, trigger, GIN index, and backfill**

Replace the `upgrade()` and `downgrade()` functions with:

```python
def upgrade():
    # Enable unaccent extension
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    # Add search_vector column
    op.add_column("signals", sa.Column("search_vector", TSVECTOR, nullable=True))

    # Create trigger function that builds the search vector from signal + document fields
    op.execute("""
    CREATE OR REPLACE FUNCTION signals_search_vector_update() RETURNS trigger AS $$
    DECLARE
        doc_url documents.url%TYPE;
        doc_title documents.title%TYPE;
    BEGIN
        SELECT url, title INTO doc_url, doc_title
        FROM documents WHERE id = NEW.document_id;

        NEW.search_vector :=
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.title, ''))), 'A') ||
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.topic, ''))), 'B') ||
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.summary, ''))), 'B') ||
            setweight(to_tsvector('german', unaccent(COALESCE(NEW.why_it_matters, ''))), 'C') ||
            setweight(to_tsvector('german', unaccent(COALESCE(doc_url, ''))), 'D') ||
            setweight(to_tsvector('german', unaccent(COALESCE(doc_title, ''))), 'D');
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
    CREATE TRIGGER trg_signals_search_vector_update
    BEFORE INSERT OR UPDATE ON signals
    FOR EACH ROW EXECUTE FUNCTION signals_search_vector_update()
    """)

    # Backfill existing rows
    op.execute("UPDATE signals SET search_vector = signals_search_vector_update().search_vector")

    # Create GIN index
    op.execute("CREATE INDEX ix_signals_search_vector ON signals USING GIN (search_vector)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_signals_search_vector")
    op.execute("DROP TRIGGER IF EXISTS trg_signals_search_vector_update ON signals")
    op.execute("DROP FUNCTION IF EXISTS signals_search_vector_update()")
    op.drop_column("signals", "search_vector")
```

Also ensure the migration imports `from sqlalchemy.dialects.postgresql import TSVECTOR` — Alembic may not autogenerate this, so add it manually to the imports at the top of the migration file.

- [ ] **Step 3: Run the migration against the dev database**

Run: `docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`
Expected: Migration runs without errors.

- [ ] **Step 4: Verify the trigger works by inserting a test signal**

Run a quick psql check:

```bash
docker compose -f docker-compose.dev.yml exec db psql -U postgres -d wfm -c "SELECT id, title, search_vector FROM signals LIMIT 3;"
```

Expected: `search_vector` column is populated with tsvector values for existing signals.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add FTS migration with tsvector, trigger, GIN index, backfill"
```

---

### Task 3: Add Search and `min_confidence` to the Signals Router

**Files:**
- Modify: `backend/app/routers/signals.py`

- [ ] **Step 1: Add `q` and `min_confidence` parameters to `list_signals`**

Update the `list_signals` endpoint in `backend/app/routers/signals.py`:

Add import at the top:
```python
from sqlalchemy import func
```

Replace the `list_signals` function with:

```python
@router.get("", response_model=List[SignalRead])
def list_signals(
    q: Optional[str] = None,
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    min_relevance: Optional[float] = None,
    min_confidence: Optional[float] = None,
    max_age_days: Optional[int] = 365,
    db: Session = Depends(get_db),
):
    query = db.query(Signal).options(selectinload(Signal.document))
    if q:
        query_expr = func.plainto_tsquery("german", func.unaccent(q))
        query = query.filter(Signal.search_vector.op("@@")(query_expr))
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_relevance is not None:
        query = query.filter(Signal.relevance_score >= min_relevance)
    if min_confidence is not None:
        query = query.filter(Signal.confidence_score >= min_confidence)
    if max_age_days and max_age_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        query = query.filter(Signal.created_at >= cutoff)
    if q:
        query_expr = func.plainto_tsquery("german", func.unaccent(q))
        query = query.order_by(
            func.ts_rank(Signal.search_vector, query_expr).desc(),
            Signal.created_at.desc(),
        )
    else:
        query = query.order_by(Signal.created_at.desc())
    signals = query.all()
    return [_to_signal_read(s) for s in signals]
```

- [ ] **Step 2: Verify the endpoint starts without errors**

Run: `cd backend && python -c "from app.routers.signals import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/signals.py
git commit -m "feat: add q and min_confidence params to signals list endpoint"
```

---

### Task 4: Add Integration Tests for Search Endpoint

Since the test suite uses SQLite (no FTS support), we add tests that work with PostgreSQL. These tests require a running dev database but validate the FTS behavior end-to-end.

**Files:**
- Create: `backend/tests/test_signal_search.py`

- [ ] **Step 1: Write integration tests for the search endpoint**

Create `backend/tests/test_signal_search.py`:

```python
import pytest
import os

SKIP_SEARCH = not os.environ.get("DATABASE_URL", "").startswith("postgres")


@pytest.fixture
def seed_search_signals(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from sqlalchemy import func

    company = Company(name="SearchCorp", slug="searchcorp", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    source = Source(
        company_id=company.id,
        url="https://searchcorp.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()

    doc1 = Document(
        source_id=source.id,
        url="https://searchcorp.com/blog/ai-strategy",
        title="AI Strategy Update",
        content_hash="search1",
    )
    doc2 = Document(
        source_id=source.id,
        url="https://searchcorp.com/blog/hiring-engineers",
        title="We Are Hiring Engineers",
        content_hash="search2",
    )
    doc3 = Document(
        source_id=source.id,
        url="https://searchcorp.com/blog/partnership",
        title="New Partnership Announcement",
        content_hash="search3",
    )
    db_session.add_all([doc1, doc2, doc3])
    db_session.commit()

    s1 = Signal(
        document_id=doc1.id,
        company_id=company.id,
        title="AI Strategy Shift",
        signal_type=SignalType.ai_announcement,
        summary="Company shifts focus to generative AI across all products.",
        relevance_score=0.9,
        confidence_score=0.85,
    )
    s2 = Signal(
        document_id=doc2.id,
        company_id=company.id,
        title="Engineering Hiring Wave",
        signal_type=SignalType.hiring_signal,
        summary="Multiple senior engineering positions opened in Munich.",
        relevance_score=0.6,
        confidence_score=0.7,
    )
    s3 = Signal(
        document_id=doc3.id,
        company_id=company.id,
        title="Strategic Partnership",
        signal_type=SignalType.partnership,
        topic="partnering with cloud providers",
        summary="Company announced a strategic partnership with a major cloud provider.",
        relevance_score=0.75,
        confidence_score=0.9,
    )
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    # Refresh search_vector using the trigger
    for s in [s1, s2, s3]:
        db_session.refresh(s)
    db_session.commit()

    return company, [s1, s2, s3], [doc1, doc2, doc3]


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_by_title(client, seed_search_signals):
    response = client.get("/api/signals?q=AI+Strategy")
    assert response.status_code == 200
    titles = [s["title"] for s in response.json()]
    assert "AI Strategy Shift" in titles


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_by_summary(client, seed_search_signals):
    response = client.get("/api/signals?q=generative")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert any("AI Strategy Shift" in s["title"] for s in response.json())


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_by_source_url(client, seed_search_signals):
    response = client.get("/api/signals?q=hiring-engineers")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_combined_with_filters(client, seed_search_signals):
    response = client.get("/api/signals?q=AI&signal_type=ai_announcement")
    assert response.status_code == 200
    assert all(s["signal_type"] == "ai_announcement" for s in response.json())


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_no_match(client, seed_search_signals):
    response = client.get("/api/signals?q=xyznonexistentterm123")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.skipif(SKIP_SEARCH, reason="Search tests require PostgreSQL FTS")
def test_search_ranking_title_higher_than_summary(client, seed_search_signals):
    response = client.get("/api/signals?q=partnership")
    assert response.status_code == 200
    results = response.json()
    # "Strategic Partnership" has "partnership" in the title (weight A),
    # so it should rank first
    if len(results) >= 2:
        assert results[0]["title"] == "Strategic Partnership"


def test_filter_by_min_confidence(client, db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType

    company = Company(name="ConfCorp", slug="confcorp", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://confcorp.com/sig", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://confcorp.com/sig/1", content_hash="conf1")
    db_session.add(doc)
    db_session.commit()

    s1 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="High Confidence",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.5,
        confidence_score=0.9,
    )
    s2 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="Low Confidence",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.5,
        confidence_score=0.3,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    response = client.get("/api/signals?min_confidence=0.8")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "High Confidence"
```

- [ ] **Step 2: Run existing tests to confirm nothing is broken**

Run: `cd backend && python -m pytest tests/ -v --ignore=tests/test_signal_search.py`
Expected: All existing tests pass.

- [ ] **Step 3: Run the min_confidence test (works on SQLite)**

Run: `cd backend && python -m pytest tests/test_signal_search.py::test_filter_by_min_confidence -v`
Expected: PASS

- [ ] **Step 4: Create a script to run search tests against PostgreSQL**

Create `backend/tests/run_search_tests.sh`:

```bash
#!/usr/bin/env bash
# Run FTS integration tests against the dev PostgreSQL database
# Requires: docker compose dev stack running with the database populated
export DATABASE_URL="postgresql://wfm:wfm@localhost:5435/wfm"
cd backend && python -m pytest tests/test_signal_search.py -v
```

Run: `chmod +x backend/tests/run_search_tests.sh`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_signal_search.py backend/tests/run_search_tests.sh
git commit -m "test: add FTS search and min_confidence integration tests"
```

---

### Task 5: Add `q` and `min_confidence` to `useSignals` Hook

**Files:**
- Modify: `frontend/src/hooks/useSignals.ts`

- [ ] **Step 1: Update `SignalsFilters` and the hook implementation**

In `frontend/src/hooks/useSignals.ts`, update the `SignalsFilters` interface and the `useSignals` function:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { Signal, SignalType } from '../types';

export interface SignalsFilters {
  company_id?: string;
  signal_type?: SignalType;
  min_relevance?: number;
  min_confidence?: number;
  max_age_days?: number;
  q?: string;
}

export function useSignals(filters?: SignalsFilters) {
  const params: Record<string, string> = {};
  if (filters?.company_id) params.company_id = filters.company_id;
  if (filters?.signal_type) params.signal_type = filters.signal_type;
  if (filters?.min_relevance !== undefined) params.min_relevance = String(filters.min_relevance);
  if (filters?.min_confidence !== undefined) params.min_confidence = String(filters.min_confidence);
  if (filters?.max_age_days !== undefined) params.max_age_days = String(filters.max_age_days);
  if (filters?.q) params.q = filters.q;

  return useQuery<Signal[]>({
    queryKey: ['signals', params],
    queryFn: () => apiGet<Signal[]>('/signals', params),
    select: (data) =>
      [...data].sort((a, b) => {
        // When searching, server already sorts by ts_rank + created_at,
        // so only sort by date when NOT searching
        if (filters?.q) return 0;
        const dateA = a.published_at ? new Date(a.published_at).getTime() : new Date(a.created_at).getTime();
        const dateB = b.published_at ? new Date(b.published_at).getTime() : new Date(b.created_at).getTime();
        return dateB - dateA;
      }),
  });
}

export function useSignal(id: string) {
  return useQuery<Signal>({
    queryKey: ['signals', id],
    queryFn: () => apiGet<Signal>(`/signals/${id}`),
    enabled: !!id,
  });
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useSignals.ts
git commit -m "feat: add q and min_confidence params to useSignals hook"
```

---

### Task 6: Add Search Input to FilterBar

**Files:**
- Modify: `frontend/src/components/FilterBar.tsx`

- [ ] **Step 1: Add search input to FilterBar with debounce and clear button**

Update `FilterBar.tsx` to include a search input:

Add imports at the top:

```tsx
import { useState, useEffect, useRef } from 'react';
import type { SignalType, CompanyType } from '../types';
```

Update the `FilterBarProps` interface to include the new props:

```tsx
interface FilterBarProps {
  signalType: SignalType | '';
  onSignalTypeChange: (v: SignalType | '') => void;
  minRelevance: number;
  onMinRelevanceChange: (v: number) => void;
  companyId?: string;
  onCompanyChange?: (v: string) => void;
  companies?: { id: string; name: string; type: CompanyType }[];
  onlyNew?: boolean;
  onOnlyNewChange?: (v: boolean) => void;
  lastMonth?: boolean;
  onLastMonthChange?: (v: boolean) => void;
  searchQuery?: string;
  onSearchQueryChange?: (v: string) => void;
}
```

Replace the component implementation — add the search state and debounce logic at the top of the function body, and add the search input JSX before the existing filters:

```tsx
export default function FilterBar({
  signalType,
  onSignalTypeChange,
  minRelevance,
  onMinRelevanceChange,
  companyId,
  onCompanyChange,
  companies,
  onlyNew,
  onOnlyNewChange,
  lastMonth,
  onLastMonthChange,
  searchQuery = '',
  onSearchQueryChange,
}: FilterBarProps) {
  const [localSearch, setLocalSearch] = useState(searchQuery);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    setLocalSearch(searchQuery);
  }, [searchQuery]);

  const handleSearchInput = (value: string) => {
    setLocalSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onSearchQueryChange?.(value);
    }, 300);
  };

  const clearSearch = () => {
    setLocalSearch('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    onSearchQueryChange?.('');
  };

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {onSearchQueryChange && (
        <div className="relative">
          <svg
            className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={localSearch}
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="Signale durchsuchen..."
            className="text-[12px] py-1.5 h-8 pl-8 pr-7 bg-white border border-slate-200 rounded-lg text-slate-600 w-56 focus:outline-none focus:border-blue-300"
          />
          {localSearch && (
            <button
              onClick={clearSearch}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      )}

      {companies && onCompanyChange && (
```

The rest of the existing filter buttons remain unchanged. Close the component normally.

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/FilterBar.tsx
git commit -m "feat: add debounced search input to FilterBar"
```

---

### Task 7: Wire Up Search in Dashboard, CompetitorDetail, and MarketTrends Pages

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/CompetitorDetail.tsx`
- Modify: `frontend/src/pages/MarketTrends.tsx`

- [ ] **Step 1: Read each page to understand how FilterBar and useSignals are used**

Read and understand how each page passes filters to `useSignals` and props to `FilterBar`. Add `searchQuery` state and wire it through.

The pattern for each page is:

1. Add `const [searchQuery, setSearchQuery] = useState('');` state
2. Pass `q: searchQuery` into the `useSignals` filters
3. Pass `searchQuery={searchQuery}` and `onSearchQueryChange={setSearchQuery}` to `FilterBar`

- [ ] **Step 2: Update Dashboard.tsx**

Add search state and wire it:

```tsx
const [searchQuery, setSearchQuery] = useState('');
```

Include `q: searchQuery` in the `useSignals` filters object.

Pass to FilterBar:
```tsx
searchQuery={searchQuery}
onSearchQueryChange={setSearchQuery}
```

- [ ] **Step 3: Update CompetitorDetail.tsx**

Same pattern: add `searchQuery` state, include `q: searchQuery` in `useSignals` filters, pass `searchQuery` and `onSearchQueryChange` to FilterBar.

- [ ] **Step 4: Update MarketTrends.tsx**

Same pattern.

- [ ] **Step 5: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/CompetitorDetail.tsx frontend/src/pages/MarketTrends.tsx
git commit -m "feat: wire search query through Dashboard, CompetitorDetail, MarketTrends"
```

---

### Task 8: End-to-End Verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass (search tests that require PostgreSQL are skipped on SQLite).

- [ ] **Step 2: Run the dev stack and verify migration**

Run: `docker compose -f docker-compose.dev.yml up -d && docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`
Expected: Migration applies successfully.

- [ ] **Step 3: Start the frontend dev server and manually test**

Run: `cd frontend && npm run dev`

Verify in the browser:
1. Dashboard page shows the search input in the FilterBar
2. Type a keyword and confirm signals are filtered by search
3. Clear the search input with the X button
4. Confirm existing filters still work alongside search

- [ ] **Step 4: Commit any final fixes**

If any issues were found and fixed, commit them.