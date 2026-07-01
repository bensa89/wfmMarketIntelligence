# Competitor Signal Stats Panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two panels to the competitor detail page (total signal count over time, and signal count by category) backed by a new backend aggregation endpoint.

**Architecture:** A new FastAPI endpoint `GET /api/intelligence/competitors/{slug}/signals/stats?days=30|90` fetches the company's signals in the period as lightweight rows and aggregates `total`, a gap-free `timeline` (daily buckets for 30d, weekly for 90d), and `by_category` counts in Python (portable across the Postgres production DB and the SQLite test DB — no `date_trunc`). The frontend adds a React Query hook and two `recharts`-based panel components, wired into `CompetitorWorkspacePage.tsx` in a new row above the existing signals table, reusing the page's existing `activePeriod` (`30d`/`90d`) state.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (sync), pytest + SQLite (backend tests); React 19, TypeScript, `@tanstack/react-query`, `recharts` (new dependency), Tailwind CSS (frontend).

## Global Constraints

- Date field for timeline bucketing: `Signal.published_at`, falling back to `Signal.created_at` when `published_at` is `NULL` — per spec.
- Granularity: `days=30` → `granularity: "day"`; `days=90` → `granularity: "week"` (ISO week, bucket date = Monday of that week) — per spec.
- Timeline must be gap-free: every day/week bucket in the requested range appears, with `count: 0` where there are no signals — per spec.
- `by_category` must include all 8 `SignalType` values, even with `count: 0`, sorted by `count` descending — per spec.
- No new DB table, no caching/persistence — always computed live — per spec.
- New panels reuse the page's existing 30d/90d toggle; no separate time-range control — per spec.
- Card styling must match existing convention: `bg-white border border-slate-200 rounded-xl p-4`, section title `text-[13px] font-semibold text-slate-800`, empty-state `text-slate-400 text-[12px]`.

---

## Task 1: Backend — signal stats aggregation endpoint

**Files:**
- Modify: `backend/app/routers/intelligence.py`
- Test: `backend/tests/test_intelligence_router.py`

**Interfaces:**
- Produces: `GET /api/intelligence/competitors/{slug}/signals/stats?days=30` (or `days=90`), returning:
  ```json
  {
    "total": 0,
    "period_days": 30,
    "granularity": "day",
    "timeline": [{"bucket": "2026-06-01", "count": 0}],
    "by_category": [{"signal_type": "product_update", "count": 0}]
  }
  ```
  `days` query param accepts only `30` or `90` (FastAPI `Query(30)` with validation); any other value → `422`. Unknown `slug` → `404` with body `{"detail": "Competitor not found"}` (matches existing `get_competitor_workspace` behavior).

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_intelligence_router.py` (append at end of file; reuse the existing `_make_signal_with_date` helper pattern already in this file, extended to accept `signal_type` and `published_at`):

```python
def _make_signal(
    db_session,
    company,
    *,
    signal_type: SignalType = SignalType.other,
    created_at: datetime,
    published_at: datetime | None = None,
) -> Signal:
    ts = created_at.timestamp()
    source = Source(company_id=company.id, url=f"https://stats-{ts}.example.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.flush()
    doc = Document(source_id=source.id, url=f"https://stats-{ts}.example.com/1", content_hash=f"h{ts}")
    db_session.add(doc)
    db_session.flush()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="Test", signal_type=signal_type, relevance_score=0.5,
        created_at=created_at, published_at=published_at,
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def _make_company(db_session, name: str) -> Company:
    company = Company(name=name, slug=name.lower().replace(" ", "-"), type=CompanyType.competitor)
    db_session.add(company)
    db_session.flush()
    db_session.commit()
    return company


def test_signal_stats_404_for_unknown_slug(client):
    resp = client.get("/api/intelligence/competitors/nonexistent-slug/signals/stats")
    assert resp.status_code == 404


def test_signal_stats_rejects_invalid_days(client, db_session):
    company = _make_company(db_session, "Stats Co Invalid")
    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=45")
    assert resp.status_code == 422


def test_signal_stats_total_and_category_counts(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Totals")
    _make_signal(db_session, company, signal_type=SignalType.product_update, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))
    _make_signal(db_session, company, signal_type=SignalType.product_update, created_at=now - timedelta(days=2), published_at=now - timedelta(days=2))
    _make_signal(db_session, company, signal_type=SignalType.hiring_signal, created_at=now - timedelta(days=3), published_at=now - timedelta(days=3))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["period_days"] == 30
    assert data["granularity"] == "day"

    by_cat = {row["signal_type"]: row["count"] for row in data["by_category"]}
    assert by_cat["product_update"] == 2
    assert by_cat["hiring_signal"] == 1
    assert by_cat["other"] == 0
    assert len(data["by_category"]) == 8
    counts = [row["count"] for row in data["by_category"]]
    assert counts == sorted(counts, reverse=True)


def test_signal_stats_excludes_other_companies_and_out_of_range_signals(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Scope")
    other_company = _make_company(db_session, "Stats Co Other")
    _make_signal(db_session, company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))
    _make_signal(db_session, company, created_at=now - timedelta(days=40), published_at=now - timedelta(days=40))
    _make_signal(db_session, other_company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_signal_stats_timeline_is_gap_free_daily(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Timeline Daily")
    _make_signal(db_session, company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    data = resp.json()
    assert data["granularity"] == "day"
    assert len(data["timeline"]) == 31
    buckets = [row["bucket"] for row in data["timeline"]]
    assert buckets == sorted(buckets)
    assert sum(row["count"] for row in data["timeline"]) == 1


def test_signal_stats_timeline_is_weekly_for_90d(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Timeline Weekly")
    _make_signal(db_session, company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=90")
    data = resp.json()
    assert data["granularity"] == "week"
    assert len(data["timeline"]) == 13
    assert sum(row["count"] for row in data["timeline"]) == 1


def test_signal_stats_falls_back_to_created_at_when_published_at_missing(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Fallback")
    _make_signal(db_session, company, created_at=now - timedelta(days=2), published_at=None)

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    data = resp.json()
    assert data["total"] == 1
    assert sum(row["count"] for row in data["timeline"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_intelligence_router.py -k signal_stats -v`
Expected: FAIL with `404` (route doesn't exist yet) for every new test.

- [ ] **Step 3: Implement the endpoint**

In `backend/app/routers/intelligence.py`, add `from datetime import date` to the existing `from datetime import datetime, timezone, timedelta` import (change to `from datetime import datetime, timezone, timedelta, date`). Then add the new route directly after `get_competitor_workspace` (after the closing of that function, before the `@router.get("/signals/feed")` line):

```python
@router.get("/competitors/{slug}/signals/stats")
def get_competitor_signal_stats(
    slug: str,
    days: int = Query(30),
    db: Session = Depends(get_db),
) -> dict:
    if days not in (30, 90):
        raise HTTPException(status_code=422, detail="days must be 30 or 90")

    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Competitor not found")

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    granularity = "day" if days == 30 else "week"

    rows = (
        db.query(Signal.signal_type, Signal.published_at, Signal.created_at)
        .filter(Signal.company_id == company.id)
        .all()
    )

    def _effective_date(row) -> date:
        dt = row.published_at or row.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date()

    in_range = [row for row in rows if _effective_date(row) >= period_start.date()]

    def _bucket_key(d: date) -> date:
        if granularity == "day":
            return d
        return d - timedelta(days=d.weekday())  # Monday of that ISO week

    bucket_counts: dict[date, int] = {}
    for row in in_range:
        key = _bucket_key(_effective_date(row))
        bucket_counts[key] = bucket_counts.get(key, 0) + 1

    # Build a fixed-length, deterministic bucket list ending at "today"'s bucket,
    # rather than aligning both ends to week boundaries — aligning both ends
    # makes the bucket count vary (13 or 14) depending on today's weekday.
    if granularity == "day":
        num_buckets = days + 1
        step = timedelta(days=1)
    else:
        num_buckets = -(-days // 7)  # ceil(days / 7) == 13 for days=90
        step = timedelta(days=7)

    range_end = _bucket_key(now.date())
    range_start = range_end - step * (num_buckets - 1)
    timeline = []
    cursor = range_start
    while cursor <= range_end:
        timeline.append({"bucket": cursor.isoformat(), "count": bucket_counts.get(cursor, 0)})
        cursor += step

    category_counts: dict[str, int] = {t.value: 0 for t in SignalType}
    for row in in_range:
        category_counts[row.signal_type.value] += 1

    by_category = sorted(
        ({"signal_type": k, "count": v} for k, v in category_counts.items()),
        key=lambda r: r["count"],
        reverse=True,
    )

    return {
        "total": len(in_range),
        "period_days": days,
        "granularity": granularity,
        "timeline": timeline,
        "by_category": by_category,
    }
```

Add `SignalType` to the existing signal model import: change `from app.models.signal import Signal` to `from app.models.signal import Signal, SignalType`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_intelligence_router.py -k signal_stats -v`
Expected: PASS for all 7 new tests.

- [ ] **Step 5: Run the full backend suite**

Run: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v`
Expected: PASS, no regressions (51+ tests, all green).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/intelligence.py backend/tests/test_intelligence_router.py
git commit -m "feat: add competitor signal stats aggregation endpoint"
```

---

## Task 2: Frontend — types, hook, and dependency

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/types/intelligence.ts`
- Create: `frontend/src/hooks/useCompetitorSignalStats.ts`

**Interfaces:**
- Consumes: `apiGet<T>(path: string, params?: Record<string, string>): Promise<T>` from `frontend/src/api/client.ts`
- Produces:
  - Type `SignalStatsResponse` (exported from `frontend/src/types/intelligence.ts`):
    ```ts
    export interface SignalStatsTimelinePoint {
      bucket: string;
      count: number;
    }
    export interface SignalStatsCategoryCount {
      signal_type: SignalType;
      count: number;
    }
    export interface SignalStatsResponse {
      total: number;
      period_days: 30 | 90;
      granularity: 'day' | 'week';
      timeline: SignalStatsTimelinePoint[];
      by_category: SignalStatsCategoryCount[];
    }
    ```
  - Hook `useCompetitorSignalStats(slug: string, days: 30 | 90)` returning a React Query result of `SignalStatsResponse`, used by Task 3 components.

- [ ] **Step 1: Add `recharts` dependency**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npm install recharts@^3.9.1
```

Verify `frontend/package.json` now lists `"recharts": "^3.9.1"` under `dependencies`.

- [ ] **Step 2: Add the response types**

In `frontend/src/types/intelligence.ts`, add after the `WorkspaceResponse` interface (after line 158):

```ts
export interface SignalStatsTimelinePoint {
  bucket: string;
  count: number;
}

export interface SignalStatsCategoryCount {
  signal_type: SignalType;
  count: number;
}

export interface SignalStatsResponse {
  total: number;
  period_days: 30 | 90;
  granularity: 'day' | 'week';
  timeline: SignalStatsTimelinePoint[];
  by_category: SignalStatsCategoryCount[];
}
```

Confirm `SignalType` is already imported/defined in this file (it's used by `TimelineEntry` on line 104) — no new import needed.

- [ ] **Step 3: Write the hook**

Create `frontend/src/hooks/useCompetitorSignalStats.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SignalStatsResponse } from '../types/intelligence';

export function useCompetitorSignalStats(slug: string, days: 30 | 90) {
  return useQuery<SignalStatsResponse>({
    queryKey: ['intelligence', 'signal-stats', slug, days],
    queryFn: () =>
      apiGet<SignalStatsResponse>(`/intelligence/competitors/${slug}/signals/stats`, {
        days: String(days),
      }),
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] **Step 4: Typecheck**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc -b`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/types/intelligence.ts frontend/src/hooks/useCompetitorSignalStats.ts
git commit -m "feat: add recharts dependency, signal stats types and hook"
```

---

## Task 3: Frontend — SignalTimelinePanel and SignalCategoryPanel components

**Files:**
- Create: `frontend/src/components/workspace/SignalTimelinePanel.tsx`
- Create: `frontend/src/components/workspace/SignalCategoryPanel.tsx`
- Test: `frontend/src/components/workspace/__tests__/SignalTimelinePanel.test.tsx`
- Test: `frontend/src/components/workspace/__tests__/SignalCategoryPanel.test.tsx`

**Interfaces:**
- Consumes: `SignalStatsResponse`, `SignalStatsTimelinePoint`, `SignalStatsCategoryCount` from `frontend/src/types/intelligence.ts` (Task 2); `useCompetitorSignalStats` from `frontend/src/hooks/useCompetitorSignalStats.ts` (Task 2)
- Produces:
  - `SignalTimelinePanel({ slug, days }: { slug: string; days: 30 | 90 })` — default export
  - `SignalCategoryPanel({ slug, days }: { slug: string; days: 30 | 90 })` — default export

First check whether the project has an existing test file for a workspace component to confirm the test setup pattern (render + testing-library). Run:

```bash
find /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend/src -name "*.test.tsx" | head -5
```

If a `__tests__` convention or a `.test.tsx`-next-to-component convention is found, follow that existing convention instead of the `__tests__/` path listed above — adjust file paths accordingly but keep the same test content.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/workspace/__tests__/SignalTimelinePanel.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SignalTimelinePanel from '../SignalTimelinePanel';
import * as hookModule from '../../../hooks/useCompetitorSignalStats';
import type { SignalStatsResponse } from '../../../types/intelligence';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('SignalTimelinePanel', () => {
  it('shows the total count and chart when data is present', () => {
    const data: SignalStatsResponse = {
      total: 5,
      period_days: 30,
      granularity: 'day',
      timeline: [
        { bucket: '2026-06-01', count: 2 },
        { bucket: '2026-06-02', count: 3 },
      ],
      by_category: [],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalTimelinePanel slug="acme" days={30} />);
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });

  it('shows an empty state when total is 0', () => {
    const data: SignalStatsResponse = {
      total: 0, period_days: 30, granularity: 'day', timeline: [], by_category: [],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalTimelinePanel slug="acme" days={30} />);
    expect(screen.getByText(/no signals/i)).toBeInTheDocument();
  });

  it('shows an error state when the request fails', () => {
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data: undefined, isLoading: false, error: new Error('fail'),
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalTimelinePanel slug="acme" days={30} />);
    expect(screen.getByText(/failed/i)).toBeInTheDocument();
  });
});
```

Create `frontend/src/components/workspace/__tests__/SignalCategoryPanel.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SignalCategoryPanel from '../SignalCategoryPanel';
import * as hookModule from '../../../hooks/useCompetitorSignalStats';
import type { SignalStatsResponse } from '../../../types/intelligence';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('SignalCategoryPanel', () => {
  it('renders a label per non-zero category, hiding zero-count categories', () => {
    const data: SignalStatsResponse = {
      total: 3, period_days: 30, granularity: 'day', timeline: [],
      by_category: [
        { signal_type: 'product_update', count: 2 },
        { signal_type: 'hiring_signal', count: 1 },
        { signal_type: 'other', count: 0 },
      ],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalCategoryPanel slug="acme" days={30} />);
    expect(screen.getByText(/product update/i)).toBeInTheDocument();
    expect(screen.getByText(/hiring signal/i)).toBeInTheDocument();
    expect(screen.queryByText(/^other$/i)).not.toBeInTheDocument();
  });

  it('shows an empty state when all categories are 0', () => {
    const data: SignalStatsResponse = {
      total: 0, period_days: 30, granularity: 'day', timeline: [],
      by_category: [{ signal_type: 'other', count: 0 }],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalCategoryPanel slug="acme" days={30} />);
    expect(screen.getByText(/no signals/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx vitest run src/components/workspace/__tests__/SignalTimelinePanel.test.tsx src/components/workspace/__tests__/SignalCategoryPanel.test.tsx`
Expected: FAIL — `SignalTimelinePanel`/`SignalCategoryPanel` modules don't exist yet.

- [ ] **Step 3: Implement `SignalTimelinePanel`**

Create `frontend/src/components/workspace/SignalTimelinePanel.tsx`:

```tsx
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useCompetitorSignalStats } from '../../hooks/useCompetitorSignalStats';
import type { SignalStatsTimelinePoint } from '../../types/intelligence';

interface Props {
  slug: string;
  days: 30 | 90;
}

function formatBucketLabel(bucket: string, granularity: 'day' | 'week'): string {
  const d = new Date(`${bucket}T00:00:00Z`);
  if (granularity === 'week') {
    const onejan = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const week = Math.ceil(((d.getTime() - onejan.getTime()) / 86400000 + onejan.getUTCDay() + 1) / 7);
    return `KW ${week}`;
  }
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
}

export default function SignalTimelinePanel({ slug, days }: Props) {
  const { data, isLoading, error } = useCompetitorSignalStats(slug, days);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-[13px] font-semibold text-slate-800">Signal-Aktivität</h2>
        {data && (
          <span className="text-[11px] text-slate-400">
            {data.total} Signal{data.total === 1 ? '' : 's'} in den letzten {days} Tagen
          </span>
        )}
      </div>

      {isLoading && <p className="text-slate-400 text-[12px]">Lädt…</p>}
      {error && <p className="text-red-500 text-[12px]">Fehler: Daten konnten nicht geladen werden (failed).</p>}
      {data && data.total === 0 && (
        <p className="text-slate-400 text-[12px]">No signals in this period.</p>
      )}
      {data && data.total > 0 && (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data.timeline as SignalStatsTimelinePoint[]}>
            <XAxis
              dataKey="bucket"
              tickFormatter={(v: string) => formatBucketLabel(v, data.granularity)}
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              axisLine={{ stroke: '#e2e8f0' }}
              tickLine={false}
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={24} />
            <Tooltip
              labelFormatter={(v: string) => formatBucketLabel(v, data.granularity)}
              formatter={(value: number) => [value, 'Signals']}
            />
            <Bar dataKey="count" fill="#3b82f6" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Implement `SignalCategoryPanel`**

Create `frontend/src/components/workspace/SignalCategoryPanel.tsx`:

```tsx
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useCompetitorSignalStats } from '../../hooks/useCompetitorSignalStats';

interface Props {
  slug: string;
  days: 30 | 90;
}

function categoryLabel(signalType: string): string {
  return signalType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function SignalCategoryPanel({ slug, days }: Props) {
  const { data, isLoading, error } = useCompetitorSignalStats(slug, days);
  const nonZero = data?.by_category.filter((c) => c.count > 0) ?? [];
  const chartData = nonZero.map((c) => ({ label: categoryLabel(c.signal_type), count: c.count }));

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <h2 className="text-[13px] font-semibold text-slate-800 mb-3">Signals nach Kategorie</h2>

      {isLoading && <p className="text-slate-400 text-[12px]">Lädt…</p>}
      {error && <p className="text-red-500 text-[12px]">Fehler: Daten konnten nicht geladen werden (failed).</p>}
      {data && nonZero.length === 0 && (
        <p className="text-slate-400 text-[12px]">No signals in this period.</p>
      )}
      {data && nonZero.length > 0 && (
        <ResponsiveContainer width="100%" height={Math.max(120, nonZero.length * 32)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 11, fill: '#475569' }}
              axisLine={false}
              tickLine={false}
              width={140}
            />
            <Tooltip formatter={(value: number) => [value, 'Signals']} />
            <Bar dataKey="count" fill="#3b82f6" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx vitest run src/components/workspace/__tests__/SignalTimelinePanel.test.tsx src/components/workspace/__tests__/SignalCategoryPanel.test.tsx`
Expected: PASS for all 5 tests.

- [ ] **Step 6: Typecheck**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc -b`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/workspace/SignalTimelinePanel.tsx frontend/src/components/workspace/SignalCategoryPanel.tsx frontend/src/components/workspace/__tests__/SignalTimelinePanel.test.tsx frontend/src/components/workspace/__tests__/SignalCategoryPanel.test.tsx
git commit -m "feat: add signal timeline and category panels"
```

---

## Task 4: Wire the new panels into CompetitorWorkspacePage

**Files:**
- Modify: `frontend/src/pages/CompetitorWorkspacePage.tsx`

**Interfaces:**
- Consumes: `SignalTimelinePanel` and `SignalCategoryPanel` from Task 3 (both take `{ slug: string; days: 30 | 90 }`); existing `activePeriod` state (`'30d' | '90d'`) already defined at `frontend/src/pages/CompetitorWorkspacePage.tsx:33`.

- [ ] **Step 1: Add imports**

In `frontend/src/pages/CompetitorWorkspacePage.tsx`, add after the existing `RisksOpportunitiesCards` import (after line 17):

```tsx
import SignalTimelinePanel from '../components/workspace/SignalTimelinePanel';
import SignalCategoryPanel from '../components/workspace/SignalCategoryPanel';
```

- [ ] **Step 2: Add a `days` derivation from `activePeriod`**

`activePeriod` is typed `'30d' | '90d'` but the panels take `30 | 90`. Add this line right after the `activeSummary` line (currently line 74, `const activeSummary = ...`):

```tsx
const statsDays: 30 | 90 = activePeriod === '30d' ? 30 : 90;
```

- [ ] **Step 3: Add the new row above the Signals panel**

In the JSX, insert a new row directly before the `{/* Row 5: All signals for this competitor */}` comment (before line 275):

```tsx
        {/* Row 4.5: Signal activity over time + by category */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SignalTimelinePanel slug={slug ?? ''} days={statsDays} />
          <SignalCategoryPanel slug={slug ?? ''} days={statsDays} />
        </div>

```

- [ ] **Step 4: Typecheck and build**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc -b`
Expected: no errors.

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual verification**

Start the dev stack if not already running:

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml up -d
```

Open the frontend dev server, navigate to a competitor detail page (`/competitors/{slug}`), and confirm:
- The new row appears above the "Signals" table with two panels: activity-over-time (bar chart) on the left, by-category (horizontal bars) on the right.
- Toggling the page's 30 Days / 90 Days selector updates both new panels (daily buckets at 30d, weekly at 90d).
- A competitor with zero signals in the period shows the "No signals in this period." empty state in both panels instead of an empty chart.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/CompetitorWorkspacePage.tsx
git commit -m "feat: wire signal timeline and category panels into competitor workspace page"
```

---

## Task 5: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 2: Run full frontend test suite**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx vitest run`
Expected: all tests PASS.

- [ ] **Step 3: Run frontend lint**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npm run lint`
Expected: no errors.

- [ ] **Step 4: Confirm spec coverage**

Re-read `docs/superpowers/specs/2026-07-01-competitor-signal-stats-panels-design.md` and confirm every requirement maps to a completed task: new stats endpoint (Task 1), types/hook/dependency (Task 2), two panel components with empty/error states (Task 3), page wiring coupled to the existing period toggle (Task 4).
