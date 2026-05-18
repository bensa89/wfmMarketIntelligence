# Competitor Scorecard — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface CompetitorScorecard data on `/competitors` (summary strip per row) and `/competitors/:slug` (Scorecard tab with full dimension breakdown, top moves, watchpoints, and explainability drawer).

**Architecture:** TanStack Query hooks fetch from `/api/scorecards/`. Period state is shared at page level on the list page and tab level on the detail page. Recompute is stale-while-recomputing (existing data stays visible). All components handle null scorecard and loading states explicitly.

**Tech Stack:** React 18, TypeScript, Vite, TanStack Query, Lucide icons, Tailwind CSS.

**Prerequisite:** Backend plan must be complete and Docker stack running before testing API integration.

---

## File Map

**New files:**
- `frontend/src/types/scorecard.ts`
- `frontend/src/api/scorecard.ts`
- `frontend/src/hooks/useScorecard.ts`
- `frontend/src/components/scorecard/ScorecardSummaryStrip.tsx`
- `frontend/src/components/scorecard/DimensionScoreCard.tsx`
- `frontend/src/components/scorecard/DimensionScoreGrid.tsx`
- `frontend/src/components/scorecard/CapabilityStrengthPanel.tsx`
- `frontend/src/components/scorecard/TopMovesTimeline.tsx`
- `frontend/src/components/scorecard/RiskFlagsPanel.tsx`
- `frontend/src/components/scorecard/WatchpointsPanel.tsx`
- `frontend/src/components/scorecard/ExplainabilityDrawer.tsx`

**Modified files:**
- `frontend/src/pages/CompetitorList.tsx` — add ScorecardSummaryStrip to each competitor row
- `frontend/src/pages/CompetitorDetail.tsx` — add Scorecard tab

---

## Task 1: TypeScript types and API client

**Files:**
- Create: `frontend/src/types/scorecard.ts`
- Create: `frontend/src/api/scorecard.ts`

- [ ] **Step 1: Create types**

Create `frontend/src/types/scorecard.ts`:

```typescript
export type ScorecardPeriodType = '30d' | '90d' | '180d';
export const SCORECARD_PERIOD_TYPES: ScorecardPeriodType[] = ['30d', '90d', '180d'];

export interface ScorecardKPIValue {
  value: number | null;
  contributing_ids: string[];
}

export interface ScorecardDimension {
  score: number | null;
  trend: 'rising' | 'stable' | 'declining' | null;
  kpis: Record<string, ScorecardKPIValue>;
}

export interface ScorecardTopMove {
  assessment_id: string;
  signal_id: string;
  title: string;
  movement_score: number;
  signal_class: string;
}

export interface ScorecardRiskFlag {
  assessment_id: string;
  capability_key: string;
  movement_strength: string;
  title: string;
}

export interface ScorecardBenchmarkPosition {
  rank: number;
  percentile: number;
  total_competitors: number;
}

export interface CompetitorScorecard {
  id: string;
  company_id: string;
  period_type: ScorecardPeriodType;
  period_start: string;
  period_end: string;
  generated_at: string;
  overall_score: number | null;
  overall_trend: 'rising' | 'stable' | 'declining' | null;
  dimension_scores: Record<string, ScorecardDimension>;
  top_capabilities: Array<{ capability_key: string; score: number | null }>;
  top_moves: ScorecardTopMove[];
  risk_flags: ScorecardRiskFlag[];
  watchpoints: string[];
  benchmark_position: ScorecardBenchmarkPosition | null;
  contributing_assessment_ids: string[];
  is_current: boolean;
  scorecard_version: string | null;
  routing_version: string | null;
}

export interface ScorecardHistoryItem {
  id: string;
  overall_score: number | null;
  overall_trend: 'rising' | 'stable' | 'declining' | null;
  generated_at: string;
  scorecard_version: string | null;
}

export interface ScorecardExplainAssessment {
  assessment_id: string;
  signal_id: string;
  title: string;
  movement_score: number;
  signal_class: string;
}

export interface ScorecardExplainDimension {
  dimension: string;
  score: number | null;
  dimension_weight: number;
  effective_weight: number;
  weighted_contribution: number | null;
  assessment_count: number;
  top_contributing_assessments: ScorecardExplainAssessment[];
  kpi_detail: Record<string, ScorecardKPIValue>;
}

export interface ScorecardExplain {
  overall_score: number | null;
  dimension_breakdown: ScorecardExplainDimension[];
  null_dimensions: string[];
  score_formula: string;
  routing_version: string | null;
  scorecard_version: string | null;
}

export interface BenchmarkScorecardItem {
  company_id: string;
  slug: string;
  name: string;
  overall_score: number | null;
  rank: number;
  percentile: number;
  dimension_scores: Record<string, ScorecardDimension>;
  overall_trend: string | null;
  scorecard_version: string | null;
}

export interface BenchmarkScorecardView {
  items: BenchmarkScorecardItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  period_type: ScorecardPeriodType;
  capability_leaders: Record<string, { company_slug: string; score: number }>;
  highest_momentum: { company_slug: string; mom_period_delta: number } | null;
  threat_flags: Array<{ company_slug: string; capability: string; movement_strength: string }>;
}

export interface ScorecardRecomputeAck {
  status: string;
  company_slug: string;
  recomputed_periods: string[];
  scorecard_ids: Record<string, string>;
  generated_at: string;
}
```

- [ ] **Step 2: Create API client**

Create `frontend/src/api/scorecard.ts`:

```typescript
import { apiGet, apiPost } from './client';
import type {
  CompetitorScorecard, ScorecardHistoryItem, ScorecardExplain,
  BenchmarkScorecardView, ScorecardRecomputeAck, ScorecardPeriodType,
} from '../types/scorecard';

export function fetchScorecard(slug: string, periodType: ScorecardPeriodType) {
  return apiGet<CompetitorScorecard>(`/scorecards/${slug}`, { period_type: periodType });
}

export function fetchScorecardHistory(slug: string, periodType: ScorecardPeriodType, limit = 10) {
  return apiGet<ScorecardHistoryItem[]>(`/scorecards/${slug}/history`, {
    period_type: periodType,
    limit: String(limit),
  });
}

export function fetchScorecardExplain(slug: string, periodType: ScorecardPeriodType) {
  return apiGet<ScorecardExplain>(`/scorecards/${slug}/explain`, { period_type: periodType });
}

export function recomputeScorecard(slug: string) {
  return apiPost<ScorecardRecomputeAck>(`/scorecards/${slug}/recompute`, {});
}

export function fetchBenchmarkScorecard(periodType: ScorecardPeriodType, page = 1, pageSize = 20) {
  return apiGet<BenchmarkScorecardView>('/scorecards/benchmark', {
    period_type: periodType,
    page: String(page),
    page_size: String(pageSize),
  });
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/scorecard.ts frontend/src/api/scorecard.ts
git commit -m "feat: scorecard TypeScript types and API client"
```

---

## Task 2: Hooks

**Files:**
- Create: `frontend/src/hooks/useScorecard.ts`

- [ ] **Step 1: Create hooks**

Create `frontend/src/hooks/useScorecard.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchScorecard, fetchScorecardHistory, fetchScorecardExplain,
  recomputeScorecard, fetchBenchmarkScorecard,
} from '../api/scorecard';
import type { ScorecardPeriodType } from '../types/scorecard';

export function useScorecard(slug: string, periodType: ScorecardPeriodType) {
  return useQuery({
    queryKey: ['scorecard', slug, periodType],
    queryFn: () => fetchScorecard(slug, periodType),
    enabled: Boolean(slug),
    retry: false,         // 404 is valid — competitor has no scorecard yet
  });
}

export function useScorecardHistory(slug: string, periodType: ScorecardPeriodType) {
  return useQuery({
    queryKey: ['scorecard', 'history', slug, periodType],
    queryFn: () => fetchScorecardHistory(slug, periodType),
    enabled: Boolean(slug),
  });
}

export function useScorecardExplain(slug: string, periodType: ScorecardPeriodType, enabled: boolean) {
  return useQuery({
    queryKey: ['scorecard', 'explain', slug, periodType],
    queryFn: () => fetchScorecardExplain(slug, periodType),
    enabled: Boolean(slug) && enabled,  // lazy — only fetch when drawer opens
    retry: false,
  });
}

export function useRecomputeScorecard(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => recomputeScorecard(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scorecard', slug] });
    },
  });
}

export function useBenchmarkScorecard(periodType: ScorecardPeriodType, page = 1) {
  return useQuery({
    queryKey: ['scorecard', 'benchmark', periodType, page],
    queryFn: () => fetchBenchmarkScorecard(periodType, page),
  });
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useScorecard.ts
git commit -m "feat: scorecard React Query hooks"
```

---

## Task 3: ScorecardSummaryStrip and DimensionScoreCard/Grid

**Files:**
- Create: `frontend/src/components/scorecard/ScorecardSummaryStrip.tsx`
- Create: `frontend/src/components/scorecard/DimensionScoreCard.tsx`
- Create: `frontend/src/components/scorecard/DimensionScoreGrid.tsx`

- [ ] **Step 1: Create ScorecardSummaryStrip**

Create `frontend/src/components/scorecard/ScorecardSummaryStrip.tsx`:

```tsx
import type { BenchmarkScorecardItem } from '../../types/scorecard';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const TREND_ICONS = {
  rising: <TrendingUp className="w-4 h-4 text-green-500" />,
  declining: <TrendingDown className="w-4 h-4 text-red-500" />,
  stable: <Minus className="w-4 h-4 text-gray-400" />,
};

const TOP_DIMENSIONS = ['capability_strength', 'market_impact'];
const DIM_LABELS: Record<string, string> = {
  capability_strength: 'Cap',
  market_impact: 'Impact',
  activity: 'Activity',
  customer_proof: 'Proof',
  momentum: 'Momentum',
};

interface Props {
  scorecard: BenchmarkScorecardItem | null | undefined;
  loading?: boolean;
}

export function ScorecardSummaryStrip({ scorecard, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 mt-2 animate-pulse">
        <div className="h-7 w-12 rounded-full bg-gray-200" />
        <div className="h-5 w-4 rounded bg-gray-200" />
        <div className="h-5 w-16 rounded-full bg-gray-200" />
        <div className="h-5 w-16 rounded-full bg-gray-200" />
        <div className="h-5 w-14 rounded bg-gray-200" />
      </div>
    );
  }

  if (!scorecard || scorecard.overall_score == null) {
    return (
      <p className="mt-2 text-xs text-gray-400 italic">No scorecard data for this period</p>
    );
  }

  const trend = scorecard.overall_trend as keyof typeof TREND_ICONS | null;

  return (
    <div className="flex items-center gap-3 mt-2 flex-wrap">
      {/* Overall score badge */}
      <span className="inline-flex items-center justify-center w-10 h-7 rounded-full bg-indigo-100 text-indigo-800 text-xs font-bold">
        {Math.round(scorecard.overall_score)}
      </span>

      {/* Trend */}
      {trend && TREND_ICONS[trend]}

      {/* Top 2 dimension pills */}
      {TOP_DIMENSIONS.map((dim) => {
        const score = scorecard.dimension_scores?.[dim]?.score;
        if (score == null) return null;
        return (
          <span key={dim} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs">
            <span className="font-medium">{DIM_LABELS[dim]}</span>
            <span>{Math.round(score)}</span>
          </span>
        );
      })}

      {/* Rank badge */}
      {scorecard.rank && (
        <span className="text-xs text-gray-500">
          #{scorecard.rank} of {/* total available from parent */}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create DimensionScoreCard**

Create `frontend/src/components/scorecard/DimensionScoreCard.tsx`:

```tsx
import type { ScorecardDimension } from '../../types/scorecard';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const DIM_LABELS: Record<string, string> = {
  capability_strength: 'Capability Strength',
  market_impact: 'Market Impact',
  activity: 'Activity',
  customer_proof: 'Customer Proof',
  momentum: 'Momentum',
};

const DIM_PRIMARY_KPI: Record<string, string> = {
  capability_strength: 'cap_weighted_score',
  activity: 'act_weighted_strength',
  market_impact: 'mkt_weighted_visibility',
  customer_proof: 'cp_validation_score',
  momentum: 'mom_period_delta',
};

interface Props {
  dimensionKey: string;
  dimension: ScorecardDimension | null | undefined;
  loading?: boolean;
}

export function DimensionScoreCard({ dimensionKey, dimension, loading }: Props) {
  const label = DIM_LABELS[dimensionKey] ?? dimensionKey;

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4 animate-pulse">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3" />
        <div className="h-8 w-12 bg-gray-200 rounded mb-2" />
        <div className="h-3 w-32 bg-gray-100 rounded" />
      </div>
    );
  }

  const score = dimension?.score ?? null;
  const trend = dimension?.trend ?? null;
  const primaryKpi = DIM_PRIMARY_KPI[dimensionKey];
  const kpiValue = primaryKpi ? dimension?.kpis?.[primaryKpi]?.value : null;

  const trendIcon = trend === 'rising'
    ? <TrendingUp className="w-4 h-4 text-green-500" />
    : trend === 'declining'
    ? <TrendingDown className="w-4 h-4 text-red-500" />
    : trend === 'stable'
    ? <Minus className="w-4 h-4 text-gray-400" />
    : null;

  const scoreColor = score == null
    ? 'text-gray-400'
    : score >= 70 ? 'text-green-700'
    : score >= 40 ? 'text-yellow-700'
    : 'text-red-600';

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white hover:border-indigo-200 transition-colors">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
        {trendIcon}
      </div>
      <p className={`text-2xl font-bold ${scoreColor}`}>
        {score != null ? Math.round(score) : '—'}
      </p>
      {kpiValue != null && (
        <p className="mt-1 text-xs text-gray-400">
          {primaryKpi?.replace(/_/g, ' ')}: {typeof kpiValue === 'number' ? Math.round(kpiValue * 10) / 10 : kpiValue}
        </p>
      )}
      {score == null && (
        <p className="mt-1 text-xs text-gray-400 italic">No data this period</p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create DimensionScoreGrid**

Create `frontend/src/components/scorecard/DimensionScoreGrid.tsx`:

```tsx
import type { ScorecardDimension } from '../../types/scorecard';
import { DimensionScoreCard } from './DimensionScoreCard';

const DIMENSIONS = ['capability_strength', 'market_impact', 'activity', 'customer_proof', 'momentum'];

interface Props {
  dimensionScores: Record<string, ScorecardDimension> | null | undefined;
  loading?: boolean;
}

export function DimensionScoreGrid({ dimensionScores, loading }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {DIMENSIONS.map((dim) => (
        <DimensionScoreCard
          key={dim}
          dimensionKey={dim}
          dimension={dimensionScores?.[dim]}
          loading={loading}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: TypeScript check**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/scorecard/
git commit -m "feat: ScorecardSummaryStrip, DimensionScoreCard, and DimensionScoreGrid components"
```

---

## Task 4: CapabilityStrengthPanel, TopMovesTimeline, RiskFlagsPanel, WatchpointsPanel

**Files:**
- Create: `frontend/src/components/scorecard/CapabilityStrengthPanel.tsx`
- Create: `frontend/src/components/scorecard/TopMovesTimeline.tsx`
- Create: `frontend/src/components/scorecard/RiskFlagsPanel.tsx`
- Create: `frontend/src/components/scorecard/WatchpointsPanel.tsx`

- [ ] **Step 1: CapabilityStrengthPanel**

Create `frontend/src/components/scorecard/CapabilityStrengthPanel.tsx`:

```tsx
import type { CompetitorScorecard } from '../../types/scorecard';

interface Props {
  scorecard: CompetitorScorecard | null | undefined;
  loading?: boolean;
}

export function CapabilityStrengthPanel({ scorecard, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-32 bg-gray-200 rounded mb-3 animate-pulse" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 bg-gray-100 rounded mb-2 animate-pulse" />
        ))}
      </div>
    );
  }

  const caps = scorecard?.top_capabilities ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Capabilities</h3>
      {caps.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No capability data in this period.</p>
      ) : (
        <ul className="space-y-2">
          {caps.map((cap) => (
            <li key={cap.capability_key} className="flex items-center justify-between">
              <span className="text-sm text-gray-700 capitalize">
                {cap.capability_key.replace(/_/g, ' ')}
              </span>
              <span className="text-sm font-medium text-indigo-700">
                {cap.score != null ? Math.round(cap.score) : '—'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: TopMovesTimeline**

Create `frontend/src/components/scorecard/TopMovesTimeline.tsx`:

```tsx
import type { ScorecardTopMove } from '../../types/scorecard';

const CLASS_LABELS: Record<string, string> = {
  product_capability_move: 'Product',
  positioning_move: 'Positioning',
  ecosystem_move: 'Ecosystem',
  thought_leadership_signal: 'Thought Leadership',
  hiring_signal: 'Hiring',
  market_expansion_move: 'Expansion',
  weak_signal: 'Weak',
};

interface Props {
  moves: ScorecardTopMove[] | null | undefined;
  loading?: boolean;
}

export function TopMovesTimeline({ moves, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3 animate-pulse" />
        {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded mb-2 animate-pulse" />)}
      </div>
    );
  }

  const list = moves ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Moves</h3>
      {list.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No moves recorded in this period.</p>
      ) : (
        <ul className="space-y-2">
          {list.map((move) => (
            <li key={move.assessment_id} className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm text-gray-800 truncate">{move.title}</p>
                <span className="inline-block text-xs text-gray-500 bg-gray-100 rounded px-1.5 py-0.5 mt-0.5">
                  {CLASS_LABELS[move.signal_class] ?? move.signal_class}
                </span>
              </div>
              <span className="flex-shrink-0 text-xs font-semibold text-indigo-700 bg-indigo-50 rounded px-1.5 py-0.5">
                {move.movement_score}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 3: RiskFlagsPanel**

Create `frontend/src/components/scorecard/RiskFlagsPanel.tsx`:

```tsx
import type { ScorecardRiskFlag } from '../../types/scorecard';
import { AlertTriangle } from 'lucide-react';

interface Props {
  flags: ScorecardRiskFlag[] | null | undefined;
  loading?: boolean;
}

export function RiskFlagsPanel({ flags, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3 animate-pulse" />
        <div className="h-10 bg-gray-100 rounded animate-pulse" />
      </div>
    );
  }

  const list = flags ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        Risk Flags
      </h3>
      {list.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No high-risk signals in this period.</p>
      ) : (
        <ul className="space-y-2">
          {list.map((flag) => (
            <li key={flag.assessment_id} className="p-2 bg-amber-50 border border-amber-200 rounded text-sm">
              <p className="font-medium text-amber-900 truncate">{flag.title}</p>
              <p className="text-xs text-amber-700 mt-0.5 capitalize">
                {flag.capability_key.replace(/_/g, ' ')} · {flag.movement_strength.replace(/_/g, ' ')}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: WatchpointsPanel**

Create `frontend/src/components/scorecard/WatchpointsPanel.tsx`:

```tsx
interface Props {
  watchpoints: string[] | null | undefined;
  loading?: boolean;
}

export function WatchpointsPanel({ watchpoints, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3 animate-pulse" />
        {[1, 2].map((i) => <div key={i} className="h-5 bg-gray-100 rounded mb-2 animate-pulse" />)}
      </div>
    );
  }

  const list = watchpoints ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Watchpoints</h3>
      {list.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No watchpoints in this period.</p>
      ) : (
        <ul className="space-y-1.5">
          {list.map((wp, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
              <span className="mt-1 flex-shrink-0 w-1.5 h-1.5 rounded-full bg-indigo-400" />
              {wp}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 5: TypeScript check**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/scorecard/
git commit -m "feat: CapabilityStrengthPanel, TopMovesTimeline, RiskFlagsPanel, WatchpointsPanel"
```

---

## Task 5: ExplainabilityDrawer

**Files:**
- Create: `frontend/src/components/scorecard/ExplainabilityDrawer.tsx`

- [ ] **Step 1: Create ExplainabilityDrawer**

Create `frontend/src/components/scorecard/ExplainabilityDrawer.tsx`:

```tsx
import { X } from 'lucide-react';
import type { ScorecardExplain } from '../../types/scorecard';

const DIM_LABELS: Record<string, string> = {
  capability_strength: 'Capability Strength',
  market_impact: 'Market Impact',
  activity: 'Activity',
  customer_proof: 'Customer Proof',
  momentum: 'Momentum',
};

interface Props {
  open: boolean;
  onClose: () => void;
  explain: ScorecardExplain | null | undefined;
  loading?: boolean;
  error?: boolean;
}

export function ExplainabilityDrawer({ open, onClose, explain, loading, error }: Props) {
  if (!open) return null;

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-800">Why this score?</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {loading && (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-gray-100 rounded" />
              ))}
            </div>
          )}

          {error && !loading && (
            <p className="text-sm text-gray-500 italic">Explainability data unavailable for this period.</p>
          )}

          {explain && !loading && (
            <>
              {/* Overall score */}
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-indigo-700">
                  {explain.overall_score != null ? Math.round(explain.overall_score) : '—'}
                </span>
                <p className="text-sm text-gray-500">{explain.score_formula}</p>
              </div>

              {/* Null dimensions notice */}
              {explain.null_dimensions.length > 0 && (
                <p className="text-xs text-gray-400 italic">
                  Dimensions with no data (excluded from score):{' '}
                  {explain.null_dimensions.map((d) => DIM_LABELS[d] ?? d).join(', ')}
                </p>
              )}

              {/* Dimension breakdown */}
              <div className="space-y-4">
                {explain.dimension_breakdown.map((dim) => (
                  <div key={dim.dimension} className="border border-gray-100 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-semibold text-gray-700">
                        {DIM_LABELS[dim.dimension] ?? dim.dimension}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span>Score: <strong className="text-gray-800">{dim.score != null ? Math.round(dim.score) : '—'}</strong></span>
                        <span>Weight: <strong className="text-gray-800">{(dim.effective_weight * 100).toFixed(1)}%</strong></span>
                        <span>Contribution: <strong className="text-gray-800">
                          {dim.weighted_contribution != null ? Math.round(dim.weighted_contribution * 10) / 10 : '—'}
                        </strong></span>
                      </div>
                    </div>

                    {dim.top_contributing_assessments.length > 0 ? (
                      <ul className="space-y-1.5 mt-2">
                        {dim.top_contributing_assessments.map((a) => (
                          <li key={a.assessment_id} className="flex items-center justify-between gap-2 text-xs">
                            <span className="text-gray-700 truncate">{a.title}</span>
                            <span className="flex-shrink-0 text-indigo-600 font-medium">{a.movement_score}</span>
                          </li>
                        ))}
                        {dim.assessment_count > 5 && (
                          <li className="text-xs text-gray-400 italic">
                            …and {dim.assessment_count - 5} more
                          </li>
                        )}
                      </ul>
                    ) : (
                      <p className="text-xs text-gray-400 italic mt-2">No contributing assessments.</p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {explain && (
          <div className="px-6 py-3 border-t border-gray-100 text-xs text-gray-400 flex gap-4">
            <span>Routing: {explain.routing_version ?? '—'}</span>
            <span>Scorecard: {explain.scorecard_version ?? '—'}</span>
          </div>
        )}
      </div>
    </>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/scorecard/ExplainabilityDrawer.tsx
git commit -m "feat: ExplainabilityDrawer with lazy-loaded explain payload"
```

---

## Task 6: CompetitorList page integration

**Files:**
- Modify: `frontend/src/pages/CompetitorList.tsx`

- [ ] **Step 1: Add scorecard period state and benchmark data fetch**

In `frontend/src/pages/CompetitorList.tsx`, add the import and state. The page already has `benchmarkPeriod` state — add a separate `scorecardPeriod` state alongside it:

```tsx
// Add to imports:
import { useBenchmarkScorecard } from '../hooks/useScorecard';
import { ScorecardSummaryStrip } from '../components/scorecard/ScorecardSummaryStrip';
import type { ScorecardPeriodType, SCORECARD_PERIOD_TYPES } from '../types/scorecard';

// Add to component state:
const [scorecardPeriod, setScorecardPeriod] = useState<ScorecardPeriodType>('30d');
const { data: scorecardBenchmark, isLoading: scorecardLoading } = useBenchmarkScorecard(scorecardPeriod);

// Build lookup map from company_id → BenchmarkScorecardItem
const scorecardByCompanyId = Object.fromEntries(
  (scorecardBenchmark?.items ?? []).map((item) => [item.company_id, item])
);
```

- [ ] **Step 2: Add period selector to the page header**

Find where the existing benchmark period selector is rendered and add a scorecard period selector nearby. Look for the section that renders `setBenchmarkPeriod` and add below it:

```tsx
{/* Scorecard period selector */}
<div className="flex items-center gap-2">
  <span className="text-xs text-gray-500">Scorecard period:</span>
  {(['30d', '90d', '180d'] as ScorecardPeriodType[]).map((p) => (
    <button
      key={p}
      onClick={() => setScorecardPeriod(p)}
      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
        scorecardPeriod === p
          ? 'bg-indigo-600 text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      {p}
    </button>
  ))}
</div>
```

- [ ] **Step 3: Add ScorecardSummaryStrip to each competitor row**

Find the `map` over `competitors` that renders each row. After the existing company name / signal count content, add:

```tsx
<ScorecardSummaryStrip
  scorecard={scorecardByCompanyId[company.id] ?? null}
  loading={scorecardLoading}
/>
```

- [ ] **Step 4: Verify in browser**

Start the dev stack and open `http://localhost:5173/competitors`. Check:
- Period selector renders
- Each competitor row shows a scorecard strip (or "No scorecard data" if none exist yet)
- Skeleton shows while loading
- Switching period re-fetches and updates all strips simultaneously

```bash
docker compose -f docker-compose.dev.yml up -d
```

Open browser at `http://localhost:5173/competitors`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CompetitorList.tsx
git commit -m "feat: add scorecard summary strip to CompetitorList page"
```

---

## Task 7: CompetitorDetail page Scorecard tab

**Files:**
- Modify: `frontend/src/pages/CompetitorDetail.tsx`

- [ ] **Step 1: Add Scorecard tab state and data fetching**

In `frontend/src/pages/CompetitorDetail.tsx`, add imports and state:

```tsx
// Add to imports:
import { useState } from 'react'; // already present
import { useScorecard, useScorecardExplain, useRecomputeScorecard } from '../hooks/useScorecard';
import { DimensionScoreGrid } from '../components/scorecard/DimensionScoreGrid';
import { CapabilityStrengthPanel } from '../components/scorecard/CapabilityStrengthPanel';
import { TopMovesTimeline } from '../components/scorecard/TopMovesTimeline';
import { RiskFlagsPanel } from '../components/scorecard/RiskFlagsPanel';
import { WatchpointsPanel } from '../components/scorecard/WatchpointsPanel';
import { ExplainabilityDrawer } from '../components/scorecard/ExplainabilityDrawer';
import type { ScorecardPeriodType } from '../types/scorecard';
import { RefreshCw, HelpCircle } from 'lucide-react';

// Add to component (inside the function body, alongside existing state):
const [activeTab, setActiveTab] = useState<'signals' | 'scorecard'>('signals');
const [scorecardPeriod, setScorecardPeriod] = useState<ScorecardPeriodType>('30d');
const [explainOpen, setExplainOpen] = useState(false);

const { data: scorecard, isLoading: scorecardLoading } = useScorecard(slug!, scorecardPeriod);
const {
  data: explain,
  isLoading: explainLoading,
  isError: explainError,
} = useScorecardExplain(slug!, scorecardPeriod, explainOpen);
const recompute = useRecomputeScorecard(slug!);
```

- [ ] **Step 2: Add tab switcher**

Find the component return JSX — before the signals list, add a tab bar. Look for where the `FilterBar` or signals content starts and wrap it with a tab structure:

```tsx
{/* Tab bar */}
<div className="flex border-b border-gray-200 mb-4">
  <button
    onClick={() => setActiveTab('signals')}
    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      activeTab === 'signals'
        ? 'border-indigo-600 text-indigo-700'
        : 'border-transparent text-gray-500 hover:text-gray-700'
    }`}
  >
    Signals
  </button>
  <button
    onClick={() => setActiveTab('scorecard')}
    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      activeTab === 'scorecard'
        ? 'border-indigo-600 text-indigo-700'
        : 'border-transparent text-gray-500 hover:text-gray-700'
    }`}
  >
    Scorecard
  </button>
</div>

{/* Signals tab — wrap existing signals content */}
{activeTab === 'signals' && (
  <> {/* existing signals JSX here */ } </>
)}
```

- [ ] **Step 3: Add Scorecard tab content**

After the signals tab block, add:

```tsx
{activeTab === 'scorecard' && (
  <div>
    {/* Top bar */}
    <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
      {/* Period selector */}
      <div className="flex items-center gap-2">
        {(['30d', '90d', '180d'] as ScorecardPeriodType[]).map((p) => (
          <button
            key={p}
            onClick={() => setScorecardPeriod(p)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              scorecardPeriod === p
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {scorecard && (
          <span className="text-xs text-gray-400">
            Last updated {new Date(scorecard.generated_at).toLocaleDateString()}
          </span>
        )}
        <button
          onClick={() => setExplainOpen(true)}
          disabled={!scorecard}
          className="flex items-center gap-1 px-3 py-1.5 text-sm rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-40"
        >
          <HelpCircle className="w-4 h-4" />
          Why this score?
        </button>
        <button
          onClick={() => recompute.mutate()}
          disabled={recompute.isPending}
          className="flex items-center gap-1 px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          <RefreshCw className={`w-4 h-4 ${recompute.isPending ? 'animate-spin' : ''}`} />
          {recompute.isPending ? 'Recomputing…' : 'Recompute'}
        </button>
      </div>
    </div>

    {/* No scorecard state */}
    {!scorecardLoading && !scorecard && (
      <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
        <p className="text-sm text-gray-500">
          No scorecard available for this period. Scorecards are generated automatically when new
          signals are analysed. You can also trigger a manual recompute above.
        </p>
      </div>
    )}

    {/* Scorecard content */}
    {(scorecardLoading || scorecard) && (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column */}
        <div className="space-y-4">
          <DimensionScoreGrid
            dimensionScores={scorecard?.dimension_scores}
            loading={scorecardLoading}
          />
          <RiskFlagsPanel flags={scorecard?.risk_flags} loading={scorecardLoading} />
        </div>

        {/* Right column */}
        <div className="space-y-4">
          <CapabilityStrengthPanel scorecard={scorecard} loading={scorecardLoading} />
          <TopMovesTimeline moves={scorecard?.top_moves} loading={scorecardLoading} />
          <WatchpointsPanel watchpoints={scorecard?.watchpoints} loading={scorecardLoading} />
        </div>
      </div>
    )}

    {/* Explainability drawer */}
    <ExplainabilityDrawer
      open={explainOpen}
      onClose={() => setExplainOpen(false)}
      explain={explain}
      loading={explainLoading}
      error={explainError}
    />
  </div>
)}
```

- [ ] **Step 4: Verify in browser**

Open `http://localhost:5173/competitors/atoss` (or any existing competitor slug).

Check:
- "Scorecard" tab appears next to "Signals"
- Clicking Scorecard tab shows period selector, recompute button, and layout
- If no scorecard: the no-data message appears with recompute button still visible
- Recompute button shows spinner while in flight; existing data stays visible (not blanked)
- "Why this score?" opens drawer from right; drawer lazy-fetches and shows skeleton
- Closing drawer (X button or overlay click) works
- Switching period re-fetches scorecard data; layout doesn't jump

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CompetitorDetail.tsx
git commit -m "feat: add Scorecard tab to CompetitorDetail page"
```

---

## Task 8: Final TypeScript and build check

- [ ] **Step 1: Full TypeScript check**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 2: Vite build**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: competitor scorecard frontend — complete"
```

---

## Self-review checklist

- [x] §8.1 ScorecardSummaryStrip on /competitors — Tasks 3, 6
- [x] Shared period state at page level (CompetitorList) — Task 6
- [x] `useBenchmarkScorecard` called once, fanned out by company_id — Task 6
- [x] No-data copy: "No scorecard data for this period" — Task 3
- [x] Loading state: skeleton without layout jump — Tasks 3, 4, 5
- [x] §8.2 Scorecard tab on /competitors/:slug — Task 7
- [x] Period selector in tab (does not affect other tabs) — Task 7
- [x] Recompute: stale-while-recomputing (not blanked), spinner, refresh on resolve — Task 7
- [x] No-data state (entire tab) with recompute button visible — Task 7
- [x] ExplainabilityDrawer lazy-fetched only on open — Tasks 5, 7
- [x] `effective_weight` and `dimension_weight` both shown in explain — Task 5
- [x] "…and N more" for capped assessments — Task 5
- [x] All empty states with correct copy — Tasks 4, 5, 7
- [x] TypeScript types match backend schemas — Task 1
- [x] `signal_id` present in ScorecardTopMove type — Task 1
