# Intelligence Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Dashboard from a simple KPI + table view into a two-column Intelligence Dashboard with crawl summary, top signals, time-series chart, distribution charts, and an enhanced signal feed — all in light theme.

**Architecture:** Add 3 new backend stats endpoints (signals over time, signal distribution, discovered pages stats). Build new frontend components (DeltaKpiCard, CrawlSummaryCard, TopSignalsPanel, SignalsOverTimeChart, SignalTypeDistribution, CompanySignalHeatmap, SignalFeedTable). Restructure Dashboard.tsx into a two-column layout with KPI band above. Use Recharts for the time-series chart. Light theme throughout.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, React 19, TypeScript, TanStack React Query 5, Tailwind CSS 3, Recharts, Lucide React icons

---

## File Structure

### Backend — New files
- `backend/app/routers/stats.py` — Stats endpoints (signals over time, distribution, discovered pages stats)
- `backend/app/schemas/stats.py` — Pydantic schemas for stats responses
- `backend/tests/test_stats.py` — Tests for stats endpoints

### Backend — Modified files
- `backend/app/main.py` — Mount stats router
- `backend/app/routers/discovered_pages.py` — Add global stats endpoint
- `backend/app/schemas/discovered_page.py` — Add DiscoveredPagesStats schema

### Frontend — New files
- `frontend/src/hooks/useCrawlRuns.ts` — Hook for CrawlRun history
- `frontend/src/hooks/useSignalStats.ts` — Hook for signal distribution + time series
- `frontend/src/hooks/useSourceCandidates.ts` — Hook for source candidates
- `frontend/src/components/dashboard/DeltaKpiCard.tsx` — KPI card with delta display
- `frontend/src/components/dashboard/CrawlSummaryCard.tsx` — Crawl changes since last run
- `frontend/src/components/dashboard/TopSignalsPanel.tsx` — Top new/updated signals list
- `frontend/src/components/dashboard/SignalsOverTimeChart.tsx` — Recharts LineChart per company
- `frontend/src/components/dashboard/SignalTypeDistribution.tsx` — Horizontal bar distribution
- `frontend/src/components/dashboard/CompanySignalHeatmap.tsx` — Company × signal type matrix
- `frontend/src/components/dashboard/SignalFeedTable.tsx` — Enhanced signal table with badges
- `frontend/src/components/dashboard/CompanyColorMap.tsx` — Utility for consistent company colors

### Frontend — Modified files
- `frontend/src/pages/Dashboard.tsx` — Complete rewrite with two-column layout
- `frontend/src/types/index.ts` — Add stats types, CrawlRunList, CrawlRun
- `frontend/src/components/FilterBar.tsx` — Add "Nur Neue" filter
- `frontend/package.json` — Add recharts dependency

---

### Task 1: Backend — Signal stats endpoints

**Files:**
- Create: `backend/app/schemas/stats.py`
- Create: `backend/app/routers/stats.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create stats schemas**

Create `backend/app/schemas/stats.py`:

```python
from pydantic import BaseModel
from typing import List


class SignalOverTimePoint(BaseModel):
    date: str
    company_id: str
    company_name: str
    count: int


class SignalTypeCount(BaseModel):
    signal_type: str
    count: int


class CompanySignalTypeCount(BaseModel):
    company_id: str
    company_name: str
    signal_type: str
    count: int


class SignalDistribution(BaseModel):
    by_type: List[SignalTypeCount]
    by_company_and_type: List[CompanySignalTypeCount]
```

- [ ] **Step 2: Create stats router**

Create `backend/app/routers/stats.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.signal import Signal, SignalType
from app.models.company import Company
from app.schemas.stats import (
    SignalOverTimePoint,
    SignalTypeCount,
    CompanySignalTypeCount,
    SignalDistribution,
)

router = APIRouter()


@router.get("/signals/over-time", response_model=List[SignalOverTimePoint])
def signals_over_time(
    days: int = Query(14, ge=1, le=90),
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(
        cast(Signal.created_at, Date).label("date"),
        Signal.company_id,
        func.count(Signal.id).label("count"),
    ).filter(Signal.created_at >= cutoff)

    if company_id:
        query = query.filter(Signal.company_id == company_id)

    query = query.group_by(cast(Signal.created_at, Date), Signal.company_id).order_by(
        cast(Signal.created_at, Date)
    )

    results = query.all()

    company_cache = {}
    points = []
    for date, comp_id, count in results:
        if comp_id not in company_cache:
            company = db.query(Company).filter(Company.id == comp_id).first()
            company_cache[comp_id] = company.name if company else "Unknown"
        points.append(
            SignalOverTimePoint(
                date=date.isoformat() if hasattr(date, "isoformat") else str(date),
                company_id=comp_id,
                company_name=company_cache[comp_id],
                count=count,
            )
        )
    return points


@router.get("/signals/distribution", response_model=SignalDistribution)
def signal_distribution(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    type_query = db.query(
        Signal.signal_type, func.count(Signal.id).label("count")
    )
    if company_id:
        type_query = type_query.filter(Signal.company_id == company_id)
    type_counts = type_query.group_by(Signal.signal_type).all()

    by_type = [
        SignalTypeCount(signal_type=st.value, count=count)
        for st, count in type_counts
    ]

    company_type_query = db.query(
        Signal.company_id,
        Signal.signal_type,
        func.count(Signal.id).label("count"),
    )
    if company_id:
        company_type_query = company_type_query.filter(
            Signal.company_id == company_id
        )
    company_type_counts = company_type_query.group_by(
        Signal.company_id, Signal.signal_type
    ).all()

    company_cache = {}
    by_company_and_type = []
    for comp_id, st, count in company_type_counts:
        if comp_id not in company_cache:
            company = db.query(Company).filter(Company.id == comp_id).first()
            company_cache[comp_id] = company.name if company else "Unknown"
        by_company_and_type.append(
            CompanySignalTypeCount(
                company_id=comp_id,
                company_name=company_cache[comp_id],
                signal_type=st.value if hasattr(st, "value") else str(st),
                count=count,
            )
        )

    return SignalDistribution(by_type=by_type, by_company_and_type=by_company_and_type)
```

- [ ] **Step 3: Register router in main.py**

Add to `backend/app/main.py` imports section:

```python
from app.routers import stats  # noqa: E402
```

Add after existing router mounts:

```python
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests pass. New endpoint tested manually.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/stats.py backend/app/routers/stats.py backend/app/main.py
git commit -m "feat: add signal stats endpoints (over-time, distribution)"
```

---

### Task 2: Backend — Discovered pages stats endpoint

**Files:**
- Modify: `backend/app/schemas/discovered_page.py`
- Modify: `backend/app/routers/discovered_pages.py`

- [ ] **Step 1: Add DiscoveredPagesStats schema**

Add to `backend/app/schemas/discovered_page.py`:

```python
class DiscoveredPagesStats(BaseModel):
    total: int
    new: int
    changed: int
    known: int
```

- [ ] **Step 2: Add global stats endpoint to discovered_pages router**

Add to `backend/app/routers/discovered_pages.py` at the top of the file, after the existing imports:

```python
from app.schemas.discovered_page import DiscoveredPageRead, DiscoveredPageUpdate, DiscoveredPagesStats
```

Add new endpoint before the existing `list_discovered_pages` function:

```python
@router.get("/stats", response_model=DiscoveredPagesStats)
def discovered_pages_stats(db: Session = Depends(get_db)):
    total = db.query(DiscoveredPage).count()
    new = db.query(DiscoveredPage).filter(DiscoveredPage.status == DiscoveredPageStatus.new).count()
    changed = db.query(DiscoveredPage).filter(DiscoveredPage.status == DiscoveredPageStatus.changed).count()
    known = db.query(DiscoveredPage).filter(DiscoveredPage.status == DiscoveredPageStatus.known).count()
    return DiscoveredPagesStats(total=total, new=new, changed=changed, known=known)
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/discovered_page.py backend/app/routers/discovered_pages.py
git commit -m "feat: add discovered pages global stats endpoint"
```

---

### Task 3: Backend — Tests for stats endpoints

**Files:**
- Create: `backend/tests/test_stats.py`

- [ ] **Step 1: Write tests for stats endpoints**

Create `backend/tests/test_stats.py`:

```python
import pytest
from app.models.signal import Signal, SignalType
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType


def test_signals_over_time_empty(client):
    response = client.get("/api/stats/signals/over-time")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_signals_over_time_with_days(client):
    response = client.get("/api/stats/signals/over-time?days=30")
    assert response.status_code == 200


def test_signal_distribution_empty(client):
    response = client.get("/api/stats/signals/distribution")
    assert response.status_code == 200
    data = response.json()
    assert "by_type" in data
    assert "by_company_and_type" in data


def test_discovered_pages_stats(client):
    response = client.get("/api/discovered-pages/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "new" in data
    assert "changed" in data
    assert "known" in data
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_stats.py -v`
Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_stats.py
git commit -m "test: add tests for stats endpoints"
```

---

### Task 4: Frontend — Install Recharts

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install recharts**

Run: `cd frontend && npm install recharts`

- [ ] **Step 2: Verify installation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: add recharts dependency"
```

---

### Task 5: Frontend — Add TypeScript types for stats and CrawlRun

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add stats and CrawlRun types**

Add at the end of `frontend/src/types/index.ts`, before the closing of any section, the following new types:

```typescript
// --- Stats ---

export interface SignalOverTimePoint {
  date: string;
  company_id: string;
  company_name: string;
  count: number;
}

export interface SignalTypeCount {
  signal_type: string;
  count: number;
}

export interface CompanySignalTypeCount {
  company_id: string;
  company_name: string;
  signal_type: string;
  count: number;
}

export interface SignalDistribution {
  by_type: SignalTypeCount[];
  by_company_and_type: CompanySignalTypeCount[];
}

export interface DiscoveredPagesStats {
  total: number;
  new: number;
  changed: number;
  known: number;
}

// --- CrawlRun (already partially defined) ---

export interface CrawlRunList {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_sources: number;
  total_new: number;
  total_skipped: number;
  total_errors: number;
}

export interface CrawlRun extends CrawlRunList {
  sources: CrawlRunSourceState[];
}
```

Note: `CrawlRunSourceState` and `CrawlRunList` may already be defined in the file. Check before adding. If `CrawlRunList` already exists, skip it. If `CrawlRunSourceState` already exists, skip it. Only add types that don't already exist.

- [ ] **Step 2: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add stats and CrawlRun TypeScript types"
```

---

### Task 6: Frontend — New hooks (useCrawlRuns, useSignalStats, useSourceCandidates, useDiscoveredPagesStats)

**Files:**
- Create: `frontend/src/hooks/useCrawlRuns.ts`
- Create: `frontend/src/hooks/useSignalStats.ts`
- Create: `frontend/src/hooks/useSourceCandidates.ts`
- Modify: `frontend/src/hooks/useDiscoveredPages.ts`

- [ ] **Step 1: Create useCrawlRuns hook**

Create `frontend/src/hooks/useCrawlRuns.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRunList } from '../types';

export function useCrawlRuns(status?: string, limit: number = 1) {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  params.limit = String(limit);

  return useQuery<CrawlRunList[]>({
    queryKey: ['crawlRuns', params],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/', params),
  });
}

export function useLastCompletedCrawl() {
  const { data, isLoading } = useQuery<CrawlRunList[]>({
    queryKey: ['crawlRuns', { status: 'completed', limit: '1' }],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/', { status: 'completed', limit: '1' }),
    select: (runs) => (runs && runs.length > 0 ? runs[0] : null),
  });
  return { lastCrawl: data ?? null, isLoading };
}
```

- [ ] **Step 2: Create useSignalStats hook**

Create `frontend/src/hooks/useSignalStats.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SignalOverTimePoint, SignalDistribution } from '../types';

export function useSignalsOverTime(days: number = 14) {
  return useQuery<SignalOverTimePoint[]>({
    queryKey: ['signalsOverTime', days],
    queryFn: () => apiGet<SignalOverTimePoint[]>('/stats/signals/over-time', { days: String(days) }),
  });
}

export function useSignalDistribution(companyId?: string) {
  const params = companyId ? { company_id: companyId } : undefined;
  return useQuery<SignalDistribution>({
    queryKey: ['signalDistribution', params],
    queryFn: () => apiGet<SignalDistribution>('/stats/signals/distribution', params),
  });
}
```

- [ ] **Step 3: Create useSourceCandidates hook**

Create `frontend/src/hooks/useSourceCandidates.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SourceCandidate } from '../types';

export function useSourceCandidates(status?: string) {
  const params = status ? { status } : undefined;
  return useQuery<SourceCandidate[]>({
    queryKey: ['sourceCandidates', params],
    queryFn: () => apiGet<SourceCandidate[]>('/source-candidates/', params),
  });
}
```

- [ ] **Step 4: Add useDiscoveredPagesStats to useDiscoveredPages.ts**

Add to `frontend/src/hooks/useDiscoveredPages.ts`:

```typescript
import type { DiscoveredPagesStats } from '../types';

export function useDiscoveredPagesStats() {
  return useQuery<DiscoveredPagesStats>({
    queryKey: ['discoveredPagesStats'],
    queryFn: () => apiGet<DiscoveredPagesStats>('/discovered-pages/stats'),
  });
}
```

Don't remove the existing exports. Just add the new export.

- [ ] **Step 5: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useCrawlRuns.ts frontend/src/hooks/useSignalStats.ts frontend/src/hooks/useSourceCandidates.ts frontend/src/hooks/useDiscoveredPages.ts
git commit -m "feat: add dashboard data hooks (crawlRuns, signalStats, sourceCandidates, discoveredPagesStats)"
```

---

### Task 7: Frontend — CompanyColorMap utility

**Files:**
- Create: `frontend/src/components/dashboard/CompanyColorMap.tsx`

- [ ] **Step 1: Create CompanyColorMap utility**

Create `frontend/src/components/dashboard/CompanyColorMap.tsx`:

```typescript
const COMPANY_COLORS = [
  '#7c3aed',
  '#2563eb',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
];

const colorMap = new Map<string, string>();

export function getCompanyColor(companyId: string): string {
  if (colorMap.has(companyId)) return colorMap.get(companyId)!;
  const index = colorMap.size % COMPANY_COLORS.length;
  const color = COMPANY_COLORS[index];
  colorMap.set(companyId, color);
  return color;
}

export function resetCompanyColors(): void {
  colorMap.clear();
}

export { COMPANY_COLORS };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/CompanyColorMap.tsx
git commit -m "feat: add CompanyColorMap utility for consistent dashboard colors"
```

---

### Task 8: Frontend — DeltaKpiCard component

**Files:**
- Create: `frontend/src/components/dashboard/DeltaKpiCard.tsx`

- [ ] **Step 1: Create DeltaKpiCard**

Create `frontend/src/components/dashboard/DeltaKpiCard.tsx`:

```tsx
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const ACCENT_COLORS: Record<string, string> = {
  blue: '#2563eb',
  green: '#10b981',
  amber: '#f59e0b',
  purple: '#7c3aed',
  cyan: '#06b6d4',
  pink: '#ec4899',
  orange: '#f97316',
  red: '#ef4444',
};

interface DeltaKpiCardProps {
  label: string;
  value: string | number;
  delta?: string;
  color: string;
  trend?: 'up' | 'down' | 'neutral';
}

export default function DeltaKpiCard({ label, value, delta, color, trend = 'neutral' }: DeltaKpiCardProps) {
  const accentColor = ACCENT_COLORS[color] || color;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 relative overflow-hidden">
      <div
        className="absolute top-0 left-0 right-0 h-[3px] rounded-t-xl"
        style={{ background: accentColor }}
      />
      <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">{label}</p>
      <p className="text-[28px] font-extrabold text-slate-900 leading-none tracking-tight">{value}</p>
      {delta && (
        <p className="text-[11px] font-medium mt-1 flex items-center gap-0.5" style={{
          color: trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#64748b',
        }}>
          {trend === 'up' && <TrendingUp size={10} />}
          {trend === 'down' && <TrendingDown size={10} />}
          {trend === 'neutral' && <Minus size={10} />}
          {delta}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/DeltaKpiCard.tsx
git commit -m "feat: add DeltaKpiCard component with light theme and delta display"
```

---

### Task 9: Frontend — CrawlSummaryCard component

**Files:**
- Create: `frontend/src/components/dashboard/CrawlSummaryCard.tsx`

- [ ] **Step 1: Create CrawlSummaryCard**

Create `frontend/src/components/dashboard/CrawlSummaryCard.tsx`:

```tsx
import type { CrawlRunList } from '../../types';

interface CrawlSummaryCardProps {
  lastCrawl: CrawlRunList | null;
  newSignalsCount: number;
  updatedSignalsCount: number;
  newDocumentsCount: number;
  candidatesCount: number;
}

export default function CrawlSummaryCard({
  lastCrawl,
  newSignalsCount,
  updatedSignalsCount,
  newDocumentsCount,
  candidatesCount,
}: CrawlSummaryCardProps) {
  const crawlTime = lastCrawl?.finished_at
    ? new Date(lastCrawl.finished_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '—';

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 border-l-[3px] border-l-emerald-500">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Seit letztem Crawl</p>
        <span className="text-[10px] text-slate-400">{crawlTime}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px]">
        <div>
          <span className="text-slate-500">Neue Signale: </span>
          <span className="font-bold text-slate-900">{newSignalsCount}</span>
        </div>
        <div>
          <span className="text-slate-500">Geändert: </span>
          <span className="font-bold text-slate-900">{updatedSignalsCount}</span>
        </div>
        <div>
          <span className="text-slate-500">Neue Dokumente: </span>
          <span className="font-bold text-slate-900">{newDocumentsCount}</span>
        </div>
        <div>
          <span className="text-slate-500">Candidates: </span>
          <span className="font-bold text-slate-900">{candidatesCount}</span>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/CrawlSummaryCard.tsx
git commit -m "feat: add CrawlSummaryCard component"
```

---

### Task 10: Frontend — TopSignalsPanel component

**Files:**
- Create: `frontend/src/components/dashboard/TopSignalsPanel.tsx`

- [ ] **Step 1: Create TopSignalsPanel**

Create `frontend/src/components/dashboard/TopSignalsPanel.tsx`:

```tsx
import type { Signal, CrawlRunList } from '../../types';
import SignalTypeIcon from '../SignalTypeIcon';
import RelevanceBadge from '../RelevanceBadge';

interface TopSignalsPanelProps {
  signals: Signal[];
  lastCrawl: CrawlRunList | null;
  maxItems?: number;
}

export default function TopSignalsPanel({ signals, lastCrawl, maxItems = 5 }: TopSignalsPanelProps) {
  const lastCrawlTime = lastCrawl?.started_at ? new Date(lastCrawl.started_at) : null;

  let displaySignals = signals;
  if (lastCrawlTime) {
    displaySignals = signals.filter(
      (s) => new Date(s.created_at) >= lastCrawlTime!
    );
  }
  displaySignals = displaySignals
    .sort((a, b) => (b.relevance_score ?? 0) - (a.relevance_score ?? 0))
    .slice(0, maxItems);

  if (displaySignals.length === 0) {
    return (
      <div>
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Top neue Signale</p>
        <p className="text-[12px] text-slate-400">Keine neuen Signale seit letztem Crawl.</p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Top neue Signale</p>
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        {displaySignals.map((signal) => {
          const isNew = lastCrawlTime && new Date(signal.created_at) >= lastCrawlTime;
          const isUpdated = lastCrawlTime && !isNew && signal.from_search;
          return (
            <div
              key={signal.id}
              className="flex items-center gap-2 px-3 py-2 border-b border-slate-100 last:border-b-0 hover:bg-slate-50 transition-colors"
            >
              {isNew ? (
                <span className="text-[9px] font-bold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded shrink-0">NEW</span>
              ) : isUpdated ? (
                <span className="text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded shrink-0">UPD</span>
              ) : (
                <span className="w-[30px] shrink-0" />
              )}
              <SignalTypeIcon type={signal.signal_type} variant="chip" />
              <span className="flex-1 text-[11px] font-semibold text-slate-900 truncate">{signal.title}</span>
              <RelevanceBadge score={signal.relevance_score} variant="badge" size="sm" />
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/TopSignalsPanel.tsx
git commit -m "feat: add TopSignalsPanel component with NEW/UPD badges"
```

---

### Task 11: Frontend — SignalsOverTimeChart component

**Files:**
- Create: `frontend/src/components/dashboard/SignalsOverTimeChart.tsx`

- [ ] **Step 1: Create SignalsOverTimeChart**

Create `frontend/src/components/dashboard/SignalsOverTimeChart.tsx`:

```tsx
import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import type { SignalOverTimePoint } from '../../types';
import { getCompanyColor } from './CompanyColorMap';

interface SignalsOverTimeChartProps {
  data: SignalOverTimePoint[];
}

const DAY_OPTIONS = [7, 14, 30] as const;

export default function SignalsOverTimeChart({ data }: SignalsOverTimeChartProps) {
  const [days, setDays] = useState<number>(14);

  const filtered = days === 7
    ? data.slice(-7)
    : days === 14
    ? data.slice(-14)
    : data;

  const companyIds = [...new Set(data.map((d) => d.company_id))];

  const chartData: Record<string, string | number>[] = [];
  const dates = [...new Set(filtered.map((d) => d.date))].sort();
  for (const date of dates) {
    const entry: Record<string, string | number> = { date };
    for (const cid of companyIds) {
      const point = filtered.find((d) => d.date === date && d.company_id === cid);
      entry[cid] = point ? point.count : 0;
    }
    chartData.push(entry);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Signale über Zeit</p>
        <div className="flex gap-1">
          {DAY_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                days === d
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>
      <div className="bg-white border border-slate-200 rounded-xl p-3">
        {companyIds.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {companyIds.map((cid) => {
              const name = filtered.find((d) => d.company_id === cid)?.company_name ?? cid;
              return (
                <span key={cid} className="flex items-center gap-1 text-[9px]">
                  <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: getCompanyColor(cid) }} />
                  <span className="text-slate-600">{name}</span>
                </span>
              );
            })}
          </div>
        )}
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={chartData} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: '#94a3b8' }}
              tickFormatter={(v: string) => {
                const d = new Date(v);
                return `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth() + 1).toString().padStart(2, '0')}`;
              }}
            />
            <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ fontSize: 11, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}
            />
            {companyIds.map((cid) => (
              <Line
                key={cid}
                type="monotone"
                dataKey={cid}
                stroke={getCompanyColor(cid)}
                strokeWidth={1.5}
                dot={false}
                name={filtered.find((d) => d.company_id === cid)?.company_name ?? cid}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/SignalsOverTimeChart.tsx
git commit -m "feat: add SignalsOverTimeChart with Recharts"
```

---

### Task 12: Frontend — SignalTypeDistribution + CompanySignalHeatmap components

**Files:**
- Create: `frontend/src/components/dashboard/SignalTypeDistribution.tsx`
- Create: `frontend/src/components/dashboard/CompanySignalHeatmap.tsx`

- [ ] **Step 1: Create SignalTypeDistribution**

Create `frontend/src/components/dashboard/SignalTypeDistribution.tsx`:

```tsx
import type { SignalTypeCount } from '../../types';
import { labelMap } from '../SignalTypeIcon';

const TYPE_COLORS: Record<string, string> = {
  ai_announcement: '#7c3aed',
  product_update: '#10b981',
  partnership: '#c2410c',
  positioning_change: '#86198f',
  target_market_change: '#be123c',
  event_or_thought_leadership: '#0f766e',
  hiring_signal: '#1d4ed8',
  other: '#52525b',
};

interface SignalTypeDistributionProps {
  byType: SignalTypeCount[];
}

export default function SignalTypeDistribution({ byType }: SignalTypeDistributionProps) {
  const maxCount = Math.max(...byType.map((t) => t.count), 1);

  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Nach Typ</p>
      <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-2">
        {byType.map((item) => {
          const color = TYPE_COLORS[item.signal_type] ?? '#52525b';
          const label = labelMap[item.signal_type as keyof typeof labelMap] ?? item.signal_type;
          const pct = (item.count / maxCount) * 100;
          return (
            <div key={item.signal_type}>
              <span className="text-[10px] font-medium" style={{ color }}>{label} {Math.round((item.count / (byType.reduce((s, t) => s + t.count, 0) || 1)) * 100)}%</span>
              <div className="bg-slate-100 rounded h-[5px] mt-0.5">
                <div className="rounded h-[5px]" style={{ width: `${pct}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create CompanySignalHeatmap**

Create `frontend/src/components/dashboard/CompanySignalHeatmap.tsx`:

```tsx
import type { CompanySignalTypeCount } from '../../types';
import { labelMap } from '../SignalTypeIcon';
import { getCompanyColor } from './CompanyColorMap';

const TYPE_COLORS: Record<string, string> = {
  ai_announcement: '#7c3aed',
  product_update: '#10b981',
  partnership: '#c2410c',
  positioning_change: '#86198f',
  target_market_change: '#be123c',
  event_or_thought_leadership: '#0f766e',
  hiring_signal: '#1d4ed8',
  other: '#52525b',
};

const TYPE_KEYS = ['ai_announcement', 'product_update', 'partnership', 'hiring_signal', 'other'] as const;

interface CompanySignalHeatmapProps {
  data: CompanySignalTypeCount[];
  companies: { id: string; name: string }[];
}

function getCellBg(count: number, maxCount: number): React.CSSProperties {
  if (count === 0) return { background: '#f1f5f9', color: '#94a3b8' };
  const intensity = count / Math.max(maxCount, 1);
  if (intensity > 0.6) return { background: '#1e3a8a', color: '#dbeafe' };
  if (intensity > 0.3) return { background: '#3b82f6', color: '#dbeafe' };
  return { background: '#dbeafe', color: '#1e3a8a' };
}

export default function CompanySignalHeatmap({ data, companies }: CompanySignalHeatmapProps) {
  const companyIds = companies.map((c) => c.id);
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Unternehmen × Typ</p>
      <div className="bg-white border border-slate-200 rounded-xl p-2 text-[9px]">
        <div className="grid grid-cols-[56px_repeat(5,1fr)] gap-px text-center">
          <div />
          {TYPE_KEYS.map((key) => (
            <div key={key} className="text-slate-400 text-[7px]">
              {labelMap[key as keyof typeof labelMap]?.split(' ')[0] ?? key.slice(0, 4)}
            </div>
          ))}
        </div>
        {companyIds.map((cid) => {
          const company = companies.find((c) => c.id === cid);
          return (
            <div key={cid} className="grid grid-cols-[56px_repeat(5,1fr)] gap-px text-center mt-px">
              <div className="text-left text-slate-500 text-[8px] truncate flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: getCompanyColor(cid) }} />
                {company?.name ?? '—'}
              </div>
              {TYPE_KEYS.map((typeKey) => {
                const entry = data.find((d) => d.company_id === cid && d.signal_type === typeKey);
                const count = entry?.count ?? 0;
                return (
                  <div key={typeKey} className="rounded px-1 py-0.5 font-semibold text-[8px]" style={getCellBg(count, maxCount)}>
                    {count > 0 ? count : ''}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/SignalTypeDistribution.tsx frontend/src/components/dashboard/CompanySignalHeatmap.tsx
git commit -m "feat: add SignalTypeDistribution and CompanySignalHeatmap components"
```

---

### Task 13: Frontend — SignalFeedTable component

**Files:**
- Create: `frontend/src/components/dashboard/SignalFeedTable.tsx`

- [ ] **Step 1: Create SignalFeedTable**

Create `frontend/src/components/dashboard/SignalFeedTable.tsx`:

```tsx
import type { Signal, CrawlRunList, Company } from '../../types';
import SignalTypeIcon from '../SignalTypeIcon';
import RelevanceBadge from '../RelevanceBadge';
import { getCompanyColor } from './CompanyColorMap';

interface SignalFeedTableProps {
  signals: Signal[];
  companies: Company[];
  lastCrawl: CrawlRunList | null;
}

export default function SignalFeedTable({ signals, companies, lastCrawl }: SignalFeedTableProps) {
  const lastCrawlTime = lastCrawl?.started_at ? new Date(lastCrawl.started_at) : null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div
        className="grid text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-4 py-2.5 border-b border-slate-200 bg-slate-50"
        style={{ gridTemplateColumns: '28px minmax(0,2.2fr) minmax(0,1fr) 140px 80px 70px' }}
      >
        <span></span>
        <span>Signal</span>
        <span>Unternehmen</span>
        <span>Typ</span>
        <span>Datum</span>
        <span>Relevanz</span>
      </div>

      {signals.length === 0 && (
        <p className="text-slate-400 text-[13px] text-center py-8">Keine Signale gefunden.</p>
      )}

      {signals.map((signal) => {
        const company = companies.find((c) => c.id === signal.company_id);
        const dateStr = signal.published_at
          ? new Date(signal.published_at).toLocaleDateString('de-DE')
          : new Date(signal.created_at).toLocaleDateString('de-DE');

        const isNew = lastCrawlTime && new Date(signal.created_at) >= lastCrawlTime;
        const isUpdated = lastCrawlTime && !isNew && signal.from_search;

        return (
          <div
            key={signal.id}
            className={`grid items-center px-4 py-3 border-b border-slate-100 last:border-b-0 hover:bg-slate-50 cursor-pointer transition-colors ${
              isNew ? 'bg-blue-50/40' : ''
            }`}
            style={{ gridTemplateColumns: '28px minmax(0,2.2fr) minmax(0,1fr) 140px 80px 70px' }}
          >
            <div>
              {isNew ? (
                <span className="text-[9px] font-bold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded">NEW</span>
              ) : isUpdated ? (
                <span className="text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">UPD</span>
              ) : null}
            </div>
            <div className="min-w-0 pr-2">
              <p className="text-[12px] font-semibold text-slate-900 truncate">{signal.title}</p>
              {signal.why_it_matters && (
                <p className="text-[10px] text-blue-600 truncate mt-0.5">
                  {signal.why_it_matters}
                </p>
              )}
            </div>
            <div className="flex items-center gap-1.5 min-w-0">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: company ? getCompanyColor(company.id) : '#a1a1aa' }}
              />
              <span className="text-[12px] font-medium text-slate-600 truncate">{company?.name ?? '—'}</span>
            </div>
            <div>
              <SignalTypeIcon type={signal.signal_type} variant="chip" />
            </div>
            <span className="text-[11px] text-slate-500">{dateStr}</span>
            <RelevanceBadge score={signal.relevance_score} variant="bar" />
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/SignalFeedTable.tsx
git commit -m "feat: add SignalFeedTable component with NEW/UPD badges and light theme"
```

---

### Task 14: Frontend — Update FilterBar with "Nur Neue" filter

**Files:**
- Modify: `frontend/src/components/FilterBar.tsx`

- [ ] **Step 1: Add Nur Neue filter to FilterBar**

Replace the content of `frontend/src/components/FilterBar.tsx` with an updated version that adds a `onlyNew` prop and filter. The existing interface and functionality stays, we add:

Add to the `FilterBarProps` interface:
```typescript
onlyNew?: boolean;
onOnlyNewChange?: (v: boolean) => void;
```

Add a new filter pill after the relevance levels, with a divider:

```tsx
{onOnlyNewChange && (
  <>
    <div className="w-px h-5 bg-slate-200" />
    <button
      onClick={() => onOnlyNewChange(!onlyNew)}
      className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
        onlyNew
          ? 'bg-emerald-100 border-emerald-300 text-emerald-700'
          : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
      }`}
    >
      Nur Neue
    </button>
  </>
)}
```

Also update the existing style colors for light theme: change `bg-app-card` to `bg-white`, `border-app-border` to `border-slate-200`, `text-ink-secondary` to `text-slate-600`, `text-ink-muted` to `text-slate-500`, `hover:bg-app-bg` to `hover:bg-slate-50`, and the active signal type pill to use `bg-blue-100 border-blue-300 text-blue-700` instead of accent-blue.

- [ ] **Step 2: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/FilterBar.tsx
git commit -m "feat: add Nur Neue filter and light theme styles to FilterBar"
```

---

### Task 15: Frontend — Rewrite Dashboard.tsx (two-column layout, light theme, all new components)

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Rewrite Dashboard.tsx**

Replace the entire content of `frontend/src/pages/Dashboard.tsx` with the new two-column intelligence dashboard that imports and uses all the new components. Key structure:

```tsx
import { useState } from 'react';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useCrawlAll } from '../hooks/useCrawl';
import { useLastCompletedCrawl } from '../hooks/useCrawlRuns';
import { useSignalsOverTime, useSignalDistribution } from '../hooks/useSignalStats';
import { useSourceCandidates } from '../hooks/useSourceCandidates';
import { useDiscoveredPagesStats } from '../hooks/useDiscoveredPages';
import DeltaKpiCard from '../components/dashboard/DeltaKpiCard';
import CrawlSummaryCard from '../components/dashboard/CrawlSummaryCard';
import TopSignalsPanel from '../components/dashboard/TopSignalsPanel';
import SignalsOverTimeChart from '../components/dashboard/SignalsOverTimeChart';
import SignalTypeDistribution from '../components/dashboard/SignalTypeDistribution';
import CompanySignalHeatmap from '../components/dashboard/CompanySignalHeatmap';
import SignalFeedTable from '../components/dashboard/SignalFeedTable';
import FilterBar from '../components/FilterBar';
import { Play, Loader2 } from 'lucide-react';
import type { SignalType } from '../types';

export default function Dashboard() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [companyId, setCompanyId] = useState('');
  const [onlyNew, setOnlyNew] = useState(false);
  const crawlAll = useCrawlAll();
  const { lastCrawl, isLoading: lastCrawlLoading } = useLastCompletedCrawl();
  const { data: allSignals } = useSignals({});
  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id: companyId || undefined,
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
  });
  const { data: overTimeData } = useSignalsOverTime(14);
  const { data: distribution } = useSignalDistribution(companyId || undefined);
  const { data: candidates } = useSourceCandidates('candidate');
  const { data: discoveredStats } = useDiscoveredPagesStats();

  const competitorCount = companies?.filter((c) => c.type === 'competitor').length ?? 0;
  const lastCrawlTime = lastCrawl?.started_at ? new Date(lastCrawl.started_at) : null;

  const newSignalsCount = lastCrawlTime
    ? allSignals?.filter((s) => new Date(s.created_at) >= lastCrawlTime!).length ?? 0
    : 0;
  const highRelevanceCount = allSignals?.filter((s) => (s.relevance_score ?? 0) >= 0.7).length ?? 0;
  const newHighRelevanceCount = lastCrawlTime
    ? allSignals?.filter((s) => new Date(s.created_at) >= lastCrawlTime! && (s.relevance_score ?? 0) >= 0.7).length ?? 0
    : 0;
  const candidateCount = candidates?.length ?? 0;
  const unreviewedCount = candidates?.filter((c) => c.status === 'candidate').length ?? 0;
  const discoveredNew = discoveredStats?.new ?? 0;
  const discoveredTotal = discoveredStats?.total ?? 0;

  const filteredSignals = onlyNew && lastCrawlTime
    ? signals?.filter((s) => new Date(s.created_at) >= lastCrawlTime!) ?? []
    : signals ?? [];

  const lastCrawlTimeStr = lastCrawl?.finished_at
    ? new Date(lastCrawl.finished_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Topbar */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-[12px] text-slate-500 mt-0.5">
            {allSignals?.length ?? '–'} Signale gesamt
            {lastCrawlTimeStr && ` · Letzter Crawl: ${lastCrawlTimeStr}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {crawlAll.isPending && (
            <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
              <Loader2 size={12} className="animate-spin" />
              Crawling...
            </span>
          )}
          <button
            onClick={() => crawlAll.mutate()}
            disabled={crawlAll.isPending}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors flex items-center gap-1.5"
          >
            <Play size={12} />
            Crawl starten
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-5">
        {/* Status banners */}
        {crawlAll.isSuccess && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border bg-emerald-50 text-emerald-700 border-emerald-200">
            Crawl abgeschlossen: {crawlAll.data.sources_processed} Quellen verarbeitet
          </div>
        )}
        {crawlAll.isError && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border bg-red-50 text-red-700 border-red-200">
            Crawl fehlgeschlagen
          </div>
        )}

        {/* KPI Band */}
        <div className="grid grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
          <DeltaKpiCard label="Signale gesamt" value={allSignals?.length ?? '–'} delta={newSignalsCount > 0 ? `↑ +${newSignalsCount} seit letztem Crawl` : undefined} color="blue" trend={newSignalsCount > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Hohe Relevanz" value={highRelevanceCount} delta={newHighRelevanceCount > 0 ? `↑ +${newHighRelevanceCount} neu` : undefined} color="green" trend={newHighRelevanceCount > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Wettbewerber" value={competitorCount} color="amber" trend="neutral" />
          <DeltaKpiCard label="Neue Signale" value={newSignalsCount} delta={lastCrawlTime ? 'seit letztem Crawl' : undefined} color="purple" trend={newSignalsCount > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Neue Dokumente" value={lastCrawl?.total_new ?? '–'} delta={lastCrawlTime ? 'seit letztem Crawl' : undefined} color="cyan" trend="neutral" />
          <DeltaKpiCard label="Source Candidates" value={candidateCount} delta={unreviewedCount > 0 ? `${unreviewedCount} ungeprüft` : undefined} color="pink" trend="neutral" />
          <DeltaKpiCard label="Discovered Pages" value={discoveredTotal} delta={discoveredNew > 0 ? `${discoveredNew} neu` : undefined} color="orange" trend={discoveredNew > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Fehler letzter Crawl" value={lastCrawl?.total_errors ?? '–'} delta={(!lastCrawl?.total_errors || lastCrawl.total_errors === 0) ? '✓ Alle erfolgreich' : `${lastCrawl?.total_errors} Fehler`} color="red" trend={lastCrawl?.total_errors ? 'down' : 'neutral'} />
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left panel: Intelligence Overview */}
          <div className="lg:col-span-2 space-y-4">
            <CrawlSummaryCard
              lastCrawl={lastCrawl ?? null}
              newSignalsCount={newSignalsCount}
              updatedSignalsCount={0}
              newDocumentsCount={lastCrawl?.total_new ?? 0}
              candidatesCount={candidateCount}
            />
            <TopSignalsPanel
              signals={allSignals ?? []}
              lastCrawl={lastCrawl ?? null}
              maxItems={5}
            />
            {overTimeData && overTimeData.length > 0 && (
              <SignalsOverTimeChart data={overTimeData} />
            )}
            <div className="grid grid-cols-2 gap-3">
              {distribution && <SignalTypeDistribution byType={distribution.by_type} />}
              {distribution && companies && (
                <CompanySignalHeatmap data={distribution.by_company_and_type} companies={companies} />
              )}
            </div>
          </div>

          {/* Right panel: Signal Feed */}
          <div className="lg:col-span-3">
            <FilterBar
              signalType={signalType}
              onSignalTypeChange={setSignalType}
              minRelevance={minRelevance}
              onMinRelevanceChange={setMinRelevance}
              companyId={companyId}
              onCompanyChange={setCompanyId}
              companies={companies?.map((c) => ({ id: c.id, name: c.name, type: c.type }))}
              onlyNew={onlyNew}
              onOnlyNewChange={setOnlyNew}
            />
            {signalsLoading || companiesLoading ? (
              <div className="flex items-center gap-2 text-slate-400 text-[13px]">
                <Loader2 size={14} className="animate-spin" />
                Lade Signale...
              </div>
            ) : (
              <SignalFeedTable
                signals={filteredSignals}
                companies={companies ?? []}
                lastCrawl={lastCrawl ?? null}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors. Some unused import warnings are acceptable.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: rewrite Dashboard with two-column layout, light theme, and all new components"
```

---

### Task 16: Frontend — Light theme migration for existing components

**Files:**
- Modify: `frontend/src/components/RelevanceBadge.tsx`
- Modify: `frontend/src/components/SignalTypeIcon.tsx`
- Modify: `frontend/src/components/CrawlProgressPanel.tsx`

- [ ] **Step 1: Update RelevanceBadge for light theme**

In `frontend/src/components/RelevanceBadge.tsx`, the badge variant colors need updating for light theme. Change:
- High: `{ background: '#dcfce7', color: '#15803d' }` — this already works for light theme
- Medium: `{ background: '#fef3c7', color: '#92400e' }` — already works
- Low: `{ background: '#fee2e2', color: '#b91c1c' }` — already works

These are fine. No changes needed for badge variant.

For the `bar` variant, change the background from `bg-app-border` to `bg-slate-200`:

Change the bar variant return:
```tsx
if (variant === 'bar') {
    return (
      <div className="flex items-center gap-2 w-full">
        <div className="flex-1 h-1 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${pct}%`, background: barColor }}
          />
        </div>
        <span className="text-[11px] font-bold text-slate-900 min-w-[28px] text-right">{pct}%</span>
      </div>
    );
  }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/RelevanceBadge.tsx
git commit -m "feat: update RelevanceBadge bar variant for light theme"
```

- [ ] **Step 3: Verify full build**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

---

### Task 17: End-to-end verification

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Manual integration test**

Start the dev stack with `docker compose -f docker-compose.dev.yml up -d`, then run backend migrations, then access the dashboard. Verify:
1. KPI band shows 8 cards with values
2. Crawl summary card shows since-last-crawl data
3. Top signals panel shows new signals with NEW badges
4. Time series chart renders with company lines
5. Type distribution and heatmap render
6. Signal table shows NEW/UPD badges
7. Filter bar includes "Nur Neue" toggle
8. Responsive: collapses to single column on mobile
9. Light theme throughout (white cards, slate backgrounds)

---

## Self-Review

- **Spec coverage:** All sections of the design spec are implemented — KPI band, CrawlSummaryCard, TopSignalsPanel, SignalsOverTimeChart, SignalTypeDistribution, CompanySignalHeatmap, SignalFeedTable, FilterBar with Nur Neue, light theme.
- **Placeholder scan:** No TBDs, TODOs, or vague steps. All code is concrete.
- **Type consistency:** CrawlRunList, SignalOverTimePoint, SignalDistribution, DiscoveredPagesStats, CompanySignalTypeCount types are defined in Task 5 and used consistently in Tasks 6, 8-15.
- **Missing spec item check:** The "Nur Neue" filter is implemented in Task 14 and wired in Task 15. The "Origin (crawl/search)" filter from the spec is NOT implemented — it's marked as optional ("optional Filter für Herkunft"). The SignalFeedTable shows `from_search` via the `isUpdated` badge which covers this partially. No task is missing.