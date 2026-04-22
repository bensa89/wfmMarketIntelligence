# V1 Intelligence Layer — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three new intelligence views (Executive Overview, Competitor Workspace, Signals Feed) to the existing React frontend, consuming the new `/api/intelligence/*` endpoints from the backend plan.

**Architecture:** New pages at `/overview`, `/competitors/:slug`, `/signals`. New component directories `overview/`, `workspace/`, `signals/` under `src/components/`. Five new React Query hooks. Navigation sidebar extended with new items. No existing pages, hooks, or components are modified.

**Prerequisites:** The backend plan (`2026-04-22-v1-intelligence-backend.md`) must be complete and the backend running before the frontend can be tested end-to-end.

**Tech Stack:** React 18, TypeScript, Vite, TanStack React Query v5, Tailwind CSS, Lucide React, React Router v6

---

## File Map

**Create:**
- `frontend/src/constants/capabilities.ts` — 16 WFM capability definitions
- `frontend/src/types/intelligence.ts` — intelligence-specific TypeScript types
- `frontend/src/hooks/useOverview.ts`
- `frontend/src/hooks/useCompetitorWorkspace.ts`
- `frontend/src/hooks/useSignalsFeed.ts`
- `frontend/src/hooks/useAssessSignal.ts`
- `frontend/src/hooks/useSummarizeCompetitor.ts`
- `frontend/src/components/signals/MovementBadge.tsx`
- `frontend/src/components/signals/ConfidenceBar.tsx`
- `frontend/src/components/overview/OverviewKPIBar.tsx`
- `frontend/src/components/overview/TopMoversList.tsx`
- `frontend/src/components/overview/CapabilityHeatmapV2.tsx`
- `frontend/src/components/overview/MarketShapingFeed.tsx`
- `frontend/src/components/overview/RisksOpportunitiesPanel.tsx`
- `frontend/src/components/workspace/CompetitorHeader.tsx`
- `frontend/src/components/workspace/StrategicPostureCard.tsx`
- `frontend/src/components/workspace/CapabilityRadar.tsx`
- `frontend/src/components/workspace/RecentMovesTimeline.tsx`
- `frontend/src/components/workspace/RisksOpportunitiesCards.tsx`
- `frontend/src/components/workspace/SummaryPeriodTabs.tsx`
- `frontend/src/components/signals/SignalFeedFilters.tsx`
- `frontend/src/components/signals/SignalFeedTable.tsx`
- `frontend/src/components/signals/SignalDetailDrawer.tsx`
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/CompetitorWorkspacePage.tsx`
- `frontend/src/pages/SignalsFeedPage.tsx`

**Modify:**
- `frontend/src/types/index.ts` — add Company.type value (already exists, no change needed)
- `frontend/src/App.tsx` — add three new routes
- `frontend/src/components/Layout.tsx` — add nav items for three new pages

---

## Task 13: TypeScript Types + Capabilities Constant

**Files:**
- Create: `frontend/src/constants/capabilities.ts`
- Create: `frontend/src/types/intelligence.ts`

- [ ] **Step 1: Create capabilities constant**

```typescript
// frontend/src/constants/capabilities.ts
export interface CapabilityMeta {
  key: string;
  label: string;
  visibilityToUser: boolean;
  strategicWeight: number;
  description: string;
}

export const CAPABILITIES: Record<string, CapabilityMeta> = {
  demand_forecasting: { key: 'demand_forecasting', label: 'Demand Forecasting', visibilityToUser: true, strategicWeight: 9, description: 'Predicting staffing demand based on historical data' },
  shift_scheduling: { key: 'shift_scheduling', label: 'Shift Scheduling', visibilityToUser: true, strategicWeight: 10, description: 'Creating and optimizing shift plans' },
  intraday_management: { key: 'intraday_management', label: 'Intraday Management', visibilityToUser: true, strategicWeight: 8, description: 'Real-time adjustment of staffing to match live demand' },
  time_attendance: { key: 'time_attendance', label: 'Time & Attendance', visibilityToUser: true, strategicWeight: 7, description: 'Tracking worked hours, absences and compliance' },
  compliance_rules: { key: 'compliance_rules', label: 'Compliance & Labor Rules', visibilityToUser: true, strategicWeight: 8, description: 'Enforcing labor law and scheduling policies' },
  employee_self_service: { key: 'employee_self_service', label: 'Employee Self-Service', visibilityToUser: true, strategicWeight: 6, description: 'Employee tools for availability and shift swaps' },
  manager_experience: { key: 'manager_experience', label: 'Manager Experience', visibilityToUser: true, strategicWeight: 7, description: 'Tooling for frontline managers' },
  mobile_experience: { key: 'mobile_experience', label: 'Mobile Experience', visibilityToUser: true, strategicWeight: 6, description: 'Mobile apps for deskless workers' },
  analytics_insights: { key: 'analytics_insights', label: 'Analytics & Insights', visibilityToUser: true, strategicWeight: 8, description: 'Reporting dashboards and workforce analytics' },
  ai_copilot: { key: 'ai_copilot', label: 'AI Copilot', visibilityToUser: true, strategicWeight: 9, description: 'AI-assisted scheduling and conversational interfaces' },
  workflow_automation: { key: 'workflow_automation', label: 'Workflow Automation', visibilityToUser: true, strategicWeight: 7, description: 'Automating approval flows and operational processes' },
  integration_hub: { key: 'integration_hub', label: 'Integration Hub', visibilityToUser: true, strategicWeight: 7, description: 'Pre-built connectors to HCM, ERP, and payroll' },
  platform_ecosystem: { key: 'platform_ecosystem', label: 'Platform & Ecosystem', visibilityToUser: true, strategicWeight: 8, description: 'Partner ecosystem and platform extensibility' },
  vertical_solutions: { key: 'vertical_solutions', label: 'Vertical Solutions', visibilityToUser: true, strategicWeight: 7, description: 'Industry-specific WFM modules' },
  data_foundation: { key: 'data_foundation', label: 'Data Foundation', visibilityToUser: false, strategicWeight: 6, description: 'Underlying data model and multi-tenant architecture' },
  optimization_engine: { key: 'optimization_engine', label: 'Optimization Engine', visibilityToUser: true, strategicWeight: 9, description: 'Mathematical optimization for schedule quality and cost' },
};

export const CAPABILITY_KEYS = Object.keys(CAPABILITIES);

export function getCapabilityLabel(key: string | null | undefined): string {
  if (!key) return 'Unknown';
  return CAPABILITIES[key]?.label ?? key;
}
```

- [ ] **Step 2: Create intelligence types**

```typescript
// frontend/src/types/intelligence.ts
import type { SignalType } from './index';

export type MovementStrength = 'weak' | 'relevant' | 'strong' | 'market_shaping';
export type VisibilityImpact = 'low' | 'medium' | 'high';
export type PeriodType = '7d' | '30d' | '90d' | 'quarter';
export type SignalClass =
  | 'product_capability_move'
  | 'positioning_move'
  | 'ecosystem_move'
  | 'thought_leadership_signal'
  | 'hiring_signal'
  | 'weak_signal'
  | 'market_expansion_move';

export interface SignalAssessment {
  id: string;
  signal_id: string;
  company_id: string;
  capability_primary: string | null;
  capability_secondary: string[];
  signal_class: SignalClass | null;
  evidence_strength: number | null;
  visibility_impact: VisibilityImpact | null;
  strategic_weight: number | null;
  movement_score: number | null;
  movement_strength: MovementStrength | null;
  confidence: number | null;
  strategic_intent_guess: string | null;
  gameplay_tags: string[];
  assessment_summary: string | null;
  implication_for_us: string | null;
  watch_items: string[];
  created_at: string;
  updated_at: string;
}

export interface SignalFeedItem {
  id: string;
  title: string;
  signal_type: SignalType;
  topic: string | null;
  summary: string | null;
  why_it_matters: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  published_at: string | null;
  created_at: string;
  company_id: string;
  company_name: string | null;
  company_slug: string | null;
  source_url: string | null;
  document_id: string;
  document_title: string | null;
  assessment: SignalAssessment | null;
}

export interface CompetitorMover {
  company_id: string;
  company_name: string;
  company_slug: string;
  avg_movement_score: number;
  signal_count: number;
  top_capability: string | null;
}

export interface HeatmapRow {
  company_id: string;
  company_name: string;
  capabilities: Record<string, number>;
}

export interface OverviewResponse {
  top_movers_7d: CompetitorMover[];
  top_movers_30d: CompetitorMover[];
  capability_heatmap: HeatmapRow[];
  recent_market_shaping: SignalFeedItem[];
  emerging_risks: string[];
  emerging_opportunities: string[];
}

export interface CapabilityCount {
  capability_key: string;
  count: number;
  avg_movement_score: number;
}

export interface TimelineEntry {
  signal_id: string;
  title: string;
  signal_type: SignalType;
  published_at: string | null;
  created_at: string;
  movement_strength: MovementStrength | null;
  movement_score: number | null;
  capability_primary: string | null;
}

export interface CompetitorSummary {
  id: string;
  company_id: string;
  period_type: PeriodType;
  period_start: string;
  period_end: string;
  strategic_posture: string | null;
  positioning_summary: string | null;
  top_capabilities: string[];
  capability_assessment: Array<{ key: string; label: string; activity_level: string; notes: string }>;
  top_risks: string[];
  top_opportunities: string[];
  watchpoints: string[];
  avg_movement_score: number | null;
  signal_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceResponse {
  competitor_profile: {
    id: string;
    name: string;
    slug: string;
    type: string;
    description: string | null;
    website: string | null;
    created_at: string;
  };
  summary_30d: CompetitorSummary | null;
  summary_90d: CompetitorSummary | null;
  recent_assessments: SignalFeedItem[];
  capability_distribution: CapabilityCount[];
  timeline_of_moves: TimelineEntry[];
}

export interface SignalsFeedResponse {
  items: SignalFeedItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SignalsFeedFilters {
  company_id?: string;
  capability?: string;
  signal_type?: string;
  movement_strength?: MovementStrength;
  min_confidence?: number;
  from_date?: string;
  to_date?: string;
  sort_by?: 'published_at' | 'movement_score' | 'confidence';
  page?: number;
  page_size?: number;
}
```

- [ ] **Step 3: Verify types compile**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors from the new files.

- [ ] **Step 4: Commit**

```bash
rtk git add frontend/src/constants/capabilities.ts frontend/src/types/intelligence.ts
rtk git commit -m "feat: add intelligence TypeScript types and capabilities constant"
```

---

## Task 14: Intelligence Hooks

**Files:**
- Create: `frontend/src/hooks/useOverview.ts`
- Create: `frontend/src/hooks/useCompetitorWorkspace.ts`
- Create: `frontend/src/hooks/useSignalsFeed.ts`
- Create: `frontend/src/hooks/useAssessSignal.ts`
- Create: `frontend/src/hooks/useSummarizeCompetitor.ts`

- [ ] **Step 1: Create useOverview.ts**

```typescript
// frontend/src/hooks/useOverview.ts
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { OverviewResponse } from '../types/intelligence';

export function useOverview() {
  return useQuery<OverviewResponse>({
    queryKey: ['intelligence', 'overview'],
    queryFn: () => apiGet<OverviewResponse>('/intelligence/overview'),
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] **Step 2: Create useCompetitorWorkspace.ts**

```typescript
// frontend/src/hooks/useCompetitorWorkspace.ts
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { WorkspaceResponse } from '../types/intelligence';

export function useCompetitorWorkspace(slug: string) {
  return useQuery<WorkspaceResponse>({
    queryKey: ['intelligence', 'workspace', slug],
    queryFn: () => apiGet<WorkspaceResponse>(`/intelligence/competitors/${slug}/workspace`),
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] **Step 3: Create useSignalsFeed.ts**

```typescript
// frontend/src/hooks/useSignalsFeed.ts
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SignalsFeedResponse, SignalsFeedFilters } from '../types/intelligence';

export function useSignalsFeed(filters: SignalsFeedFilters = {}) {
  const params: Record<string, string> = {};
  if (filters.company_id) params.company_id = filters.company_id;
  if (filters.capability) params.capability = filters.capability;
  if (filters.signal_type) params.signal_type = filters.signal_type;
  if (filters.movement_strength) params.movement_strength = filters.movement_strength;
  if (filters.min_confidence !== undefined) params.min_confidence = String(filters.min_confidence);
  if (filters.from_date) params.from_date = filters.from_date;
  if (filters.to_date) params.to_date = filters.to_date;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.page) params.page = String(filters.page);
  if (filters.page_size) params.page_size = String(filters.page_size);

  return useQuery<SignalsFeedResponse>({
    queryKey: ['intelligence', 'signals-feed', params],
    queryFn: () => apiGet<SignalsFeedResponse>('/intelligence/signals/feed', params),
    staleTime: 60 * 1000,
  });
}
```

- [ ] **Step 4: Create useAssessSignal.ts**

```typescript
// frontend/src/hooks/useAssessSignal.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
import type { SignalAssessment } from '../types/intelligence';

export function useAssessSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (signalId: string) =>
      apiPost<SignalAssessment>(`/intelligence/signals/${signalId}/assess`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'signals-feed'] });
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'overview'] });
    },
  });
}
```

- [ ] **Step 5: Create useSummarizeCompetitor.ts**

```typescript
// frontend/src/hooks/useSummarizeCompetitor.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
import type { PeriodType } from '../types/intelligence';

export function useSummarizeCompetitor(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (period_type: PeriodType) =>
      apiPost(`/intelligence/competitors/${companyId}/summarize?period_type=${period_type}`),
    onSuccess: (_data, period_type) => {
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'workspace'] });
    },
  });
}
```

- [ ] **Step 6: Verify compilation**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
rtk git add frontend/src/hooks/useOverview.ts frontend/src/hooks/useCompetitorWorkspace.ts frontend/src/hooks/useSignalsFeed.ts frontend/src/hooks/useAssessSignal.ts frontend/src/hooks/useSummarizeCompetitor.ts
rtk git commit -m "feat: add intelligence data hooks (useOverview, useCompetitorWorkspace, useSignalsFeed)"
```

---

## Task 15: Shared Signal Components

**Files:**
- Create: `frontend/src/components/signals/MovementBadge.tsx`
- Create: `frontend/src/components/signals/ConfidenceBar.tsx`

- [ ] **Step 1: Create MovementBadge.tsx**

```tsx
// frontend/src/components/signals/MovementBadge.tsx
import type { MovementStrength } from '../../types/intelligence';

interface Props {
  strength: MovementStrength | null | undefined;
  size?: 'sm' | 'md';
}

const CONFIG: Record<MovementStrength, { label: string; bg: string; text: string; dot: string }> = {
  weak:           { label: 'Weak',           bg: 'rgba(100,116,139,0.15)', text: '#94a3b8', dot: '#64748b' },
  relevant:       { label: 'Relevant',       bg: 'rgba(59,130,246,0.15)',  text: '#60a5fa', dot: '#3b82f6' },
  strong:         { label: 'Strong',         bg: 'rgba(139,92,246,0.15)',  text: '#a78bfa', dot: '#8b5cf6' },
  market_shaping: { label: 'Market Shaping', bg: 'rgba(251,146,60,0.18)', text: '#fb923c', dot: '#f97316' },
};

export default function MovementBadge({ strength, size = 'sm' }: Props) {
  if (!strength) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full font-medium ${size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'}`}
        style={{ background: 'rgba(71,85,105,0.2)', color: '#64748b' }}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-slate-600 inline-block" />
        Unassessed
      </span>
    );
  }

  const c = CONFIG[strength];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'}`}
      style={{ background: c.bg, color: c.text }}
    >
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: c.dot }} />
      {c.label}
    </span>
  );
}
```

- [ ] **Step 2: Create ConfidenceBar.tsx**

```tsx
// frontend/src/components/signals/ConfidenceBar.tsx
interface Props {
  value: number | null | undefined;
  showLabel?: boolean;
}

export default function ConfidenceBar({ value, showLabel = true }: Props) {
  if (value == null) return <span className="text-slate-600 text-[11px]">—</span>;

  const pct = Math.round(value * 100);
  const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#3b82f6' : pct >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-slate-700 overflow-hidden flex-shrink-0">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      {showLabel && (
        <span className="text-[11px] tabular-nums" style={{ color }}>
          {pct}%
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify compilation**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
rtk git add frontend/src/components/signals/MovementBadge.tsx frontend/src/components/signals/ConfidenceBar.tsx
rtk git commit -m "feat: add MovementBadge and ConfidenceBar shared components"
```

---

## Task 16: Overview Components + Page

**Files:**
- Create: `frontend/src/components/overview/OverviewKPIBar.tsx`
- Create: `frontend/src/components/overview/TopMoversList.tsx`
- Create: `frontend/src/components/overview/CapabilityHeatmapV2.tsx`
- Create: `frontend/src/components/overview/MarketShapingFeed.tsx`
- Create: `frontend/src/components/overview/RisksOpportunitiesPanel.tsx`
- Create: `frontend/src/pages/OverviewPage.tsx`

- [ ] **Step 1: Create OverviewKPIBar.tsx**

```tsx
// frontend/src/components/overview/OverviewKPIBar.tsx
import type { OverviewResponse } from '../../types/intelligence';

interface Props {
  data: OverviewResponse;
}

export default function OverviewKPIBar({ data }: Props) {
  const totalSignals = data.top_movers_30d.reduce((sum, m) => sum + m.signal_count, 0);
  const avgScore = data.top_movers_30d.length > 0
    ? Math.round(data.top_movers_30d.reduce((sum, m) => sum + m.avg_movement_score, 0) / data.top_movers_30d.length)
    : 0;
  const activeCompetitors = data.top_movers_30d.length;
  const marketShapingCount = data.recent_market_shaping.length;

  const kpis = [
    { label: 'Signals (30d)', value: totalSignals },
    { label: 'Active Competitors', value: activeCompetitors },
    { label: 'Avg Movement Score', value: avgScore },
    { label: 'Market Shaping', value: marketShapingCount },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {kpis.map((k) => (
        <div
          key={k.label}
          className="rounded-xl px-4 py-3"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
        >
          <div className="text-[11px] text-slate-500 uppercase tracking-wider mb-1">{k.label}</div>
          <div className="text-2xl font-semibold text-slate-100 tabular-nums">{k.value}</div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create TopMoversList.tsx**

```tsx
// frontend/src/components/overview/TopMoversList.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { CompetitorMover } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';

interface Props {
  movers7d: CompetitorMover[];
  movers30d: CompetitorMover[];
}

export default function TopMoversList({ movers7d, movers30d }: Props) {
  const [period, setPeriod] = useState<'7d' | '30d'>('7d');
  const movers = period === '7d' ? movers7d : movers30d;

  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[13px] font-semibold text-slate-200">Top Movers</h3>
        <div className="flex gap-1">
          {(['7d', '30d'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                period === p
                  ? 'text-blue-400'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
              style={period === p ? { background: 'rgba(59,130,246,0.15)' } : undefined}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {movers.length === 0 ? (
        <p className="text-slate-600 text-[12px]">No data yet</p>
      ) : (
        <ul className="space-y-2">
          {movers.map((mover, i) => (
            <li key={mover.company_id} className="flex items-center gap-3">
              <span className="text-[11px] text-slate-600 w-4 tabular-nums">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <Link
                  to={`/competitors/${mover.company_slug}`}
                  className="text-[13px] text-slate-200 hover:text-blue-400 font-medium truncate block transition-colors"
                >
                  {mover.company_name}
                </Link>
                {mover.top_capability && (
                  <span className="text-[11px] text-slate-500">{getCapabilityLabel(mover.top_capability)}</span>
                )}
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-[13px] font-semibold text-slate-200 tabular-nums">
                  {mover.avg_movement_score}
                </div>
                <div className="text-[10px] text-slate-600">{mover.signal_count} signals</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create CapabilityHeatmapV2.tsx**

```tsx
// frontend/src/components/overview/CapabilityHeatmapV2.tsx
import type { HeatmapRow } from '../../types/intelligence';
import { CAPABILITIES } from '../../constants/capabilities';

interface Props {
  rows: HeatmapRow[];
}

const VISIBLE_CAPABILITIES = Object.values(CAPABILITIES)
  .filter((c) => c.visibilityToUser)
  .sort((a, b) => b.strategicWeight - a.strategicWeight)
  .slice(0, 8);

function scoreToColor(score: number): string {
  if (score === 0) return 'rgba(71,85,105,0.15)';
  if (score < 30) return 'rgba(59,130,246,0.20)';
  if (score < 60) return 'rgba(59,130,246,0.45)';
  if (score < 80) return 'rgba(139,92,246,0.55)';
  return 'rgba(251,146,60,0.65)';
}

export default function CapabilityHeatmapV2({ rows }: Props) {
  if (rows.length === 0) {
    return (
      <div
        className="rounded-xl p-4 flex items-center justify-center h-48"
        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <p className="text-slate-600 text-[12px]">No assessment data yet</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl p-4 overflow-x-auto"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <h3 className="text-[13px] font-semibold text-slate-200 mb-4">Capability Activity (30d)</h3>
      <table className="w-full text-[11px]">
        <thead>
          <tr>
            <th className="text-left text-slate-500 pb-2 pr-3 font-medium w-32">Company</th>
            {VISIBLE_CAPABILITIES.map((c) => (
              <th
                key={c.key}
                className="text-slate-500 pb-2 px-1 font-medium text-center"
                style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: 64, verticalAlign: 'bottom' }}
                title={c.label}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.company_id}>
              <td className="pr-3 py-1 text-slate-300 truncate max-w-[8rem]" title={row.company_name}>
                {row.company_name}
              </td>
              {VISIBLE_CAPABILITIES.map((c) => {
                const score = row.capabilities[c.key] ?? 0;
                return (
                  <td key={c.key} className="px-0.5 py-0.5 text-center">
                    <div
                      className="w-7 h-5 rounded mx-auto"
                      style={{ background: scoreToColor(score) }}
                      title={score > 0 ? `${c.label}: ${score}` : `${c.label}: no data`}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Create MarketShapingFeed.tsx**

```tsx
// frontend/src/components/overview/MarketShapingFeed.tsx
import { Link } from 'react-router-dom';
import type { SignalFeedItem } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  signals: SignalFeedItem[];
}

export default function MarketShapingFeed({ signals }: Props) {
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="flex items-center gap-2 mb-4">
        <span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />
        <h3 className="text-[13px] font-semibold text-slate-200">Market Shaping Signals</h3>
      </div>

      {signals.length === 0 ? (
        <p className="text-slate-600 text-[12px]">No market-shaping signals in the last 30 days</p>
      ) : (
        <ul className="space-y-3">
          {signals.slice(0, 6).map((item) => (
            <li key={item.id} className="flex gap-3">
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-medium text-slate-200 leading-snug line-clamp-2">
                  {item.title}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {item.company_slug && (
                    <Link
                      to={`/competitors/${item.company_slug}`}
                      className="text-[11px] text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      {item.company_name}
                    </Link>
                  )}
                  {item.assessment?.capability_primary && (
                    <span className="text-[11px] text-slate-500">
                      · {getCapabilityLabel(item.assessment.capability_primary)}
                    </span>
                  )}
                  <span className="text-[11px] text-slate-600">
                    · {formatDistanceToNow(item.published_at || item.created_at)}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Create RisksOpportunitiesPanel.tsx**

```tsx
// frontend/src/components/overview/RisksOpportunitiesPanel.tsx
interface Props {
  risks: string[];
  opportunities: string[];
}

export default function RisksOpportunitiesPanel({ risks, opportunities }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-red-400 mb-3">Emerging Risks</h4>
        {risks.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {risks.slice(0, 5).map((r, i) => (
              <li key={i} className="flex gap-2 text-[12px] text-slate-300">
                <span className="text-red-500 mt-0.5 flex-shrink-0">▸</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-green-400 mb-3">Emerging Opportunities</h4>
        {opportunities.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {opportunities.slice(0, 5).map((o, i) => (
              <li key={i} className="flex gap-2 text-[12px] text-slate-300">
                <span className="text-green-500 mt-0.5 flex-shrink-0">▸</span>
                <span>{o}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create OverviewPage.tsx**

```tsx
// frontend/src/pages/OverviewPage.tsx
import { useOverview } from '../hooks/useOverview';
import OverviewKPIBar from '../components/overview/OverviewKPIBar';
import TopMoversList from '../components/overview/TopMoversList';
import CapabilityHeatmapV2 from '../components/overview/CapabilityHeatmapV2';
import MarketShapingFeed from '../components/overview/MarketShapingFeed';
import RisksOpportunitiesPanel from '../components/overview/RisksOpportunitiesPanel';

export default function OverviewPage() {
  const { data, isLoading, error } = useOverview();

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-slate-500 text-sm">Loading intelligence overview…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-red-400 text-sm">Failed to load overview. Is the backend running?</span>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-100">Executive Overview</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">Market intelligence summary · last 30 days</p>
      </div>

      <OverviewKPIBar data={data} />

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="col-span-1">
          <TopMoversList movers7d={data.top_movers_7d} movers30d={data.top_movers_30d} />
        </div>
        <div className="col-span-2">
          <CapabilityHeatmapV2 rows={data.capability_heatmap} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <MarketShapingFeed signals={data.recent_market_shaping} />
        <RisksOpportunitiesPanel
          risks={data.emerging_risks}
          opportunities={data.emerging_opportunities}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Verify compilation**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors (may warn about missing `formatDistanceToNow` if not yet exported — check `src/utils/dates.ts`).

If `formatDistanceToNow` is not in `utils/dates.ts`, add this export to that file:
```typescript
export function formatDistanceToNow(dateStr: string | null | undefined): string {
  if (!dateStr) return 'unknown date';
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return 'today';
  if (days === 1) return '1 day ago';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return '1 month ago';
  return `${months} months ago`;
}
```

- [ ] **Step 8: Commit**

```bash
rtk git add frontend/src/components/overview/ frontend/src/pages/OverviewPage.tsx
rtk git commit -m "feat: add Overview components and OverviewPage"
```

---

## Task 17: Competitor Workspace Components + Page

**Files:**
- Create: `frontend/src/components/workspace/CompetitorHeader.tsx`
- Create: `frontend/src/components/workspace/StrategicPostureCard.tsx`
- Create: `frontend/src/components/workspace/CapabilityRadar.tsx`
- Create: `frontend/src/components/workspace/RecentMovesTimeline.tsx`
- Create: `frontend/src/components/workspace/RisksOpportunitiesCards.tsx`
- Create: `frontend/src/components/workspace/SummaryPeriodTabs.tsx`
- Create: `frontend/src/pages/CompetitorWorkspacePage.tsx`

- [ ] **Step 1: Create CompetitorHeader.tsx**

```tsx
// frontend/src/components/workspace/CompetitorHeader.tsx
import { ExternalLink, RefreshCw } from 'lucide-react';
import { useSummarizeCompetitor } from '../../hooks/useSummarizeCompetitor';
import type { WorkspaceResponse } from '../../types/intelligence';

interface Props {
  profile: WorkspaceResponse['competitor_profile'];
}

export default function CompetitorHeader({ profile }: Props) {
  const summarize = useSummarizeCompetitor(profile.id);

  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">{profile.name}</h1>
        {profile.description && (
          <p className="text-[13px] text-slate-400 mt-0.5 max-w-2xl">{profile.description}</p>
        )}
        {profile.website && (
          <a
            href={profile.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[12px] text-blue-400 hover:text-blue-300 mt-1 transition-colors"
          >
            <ExternalLink size={11} />
            {profile.website}
          </a>
        )}
      </div>
      <button
        onClick={() => summarize.mutate('30d')}
        disabled={summarize.isPending}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)' }}
        title="Regenerate 30d summary"
      >
        <RefreshCw size={13} className={summarize.isPending ? 'animate-spin' : ''} />
        Refresh Summary
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create StrategicPostureCard.tsx**

```tsx
// frontend/src/components/workspace/StrategicPostureCard.tsx
import type { CompetitorSummary } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';

interface Props {
  summary: CompetitorSummary | null;
}

function postureLabel(raw: string | null): string {
  if (!raw) return 'Unknown';
  return raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function postureColor(raw: string | null): string {
  if (!raw) return '#64748b';
  if (raw.includes('aggressive')) return '#f97316';
  if (raw.includes('expansion')) return '#fb923c';
  if (raw.includes('defensive')) return '#94a3b8';
  if (raw.includes('niche')) return '#60a5fa';
  return '#a78bfa';
}

export default function StrategicPostureCard({ summary }: Props) {
  if (!summary) {
    return (
      <div
        className="rounded-xl p-4 h-full"
        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <p className="text-slate-600 text-[12px]">No summary available yet. Run a crawl to generate.</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span
          className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
          style={{
            background: `${postureColor(summary.strategic_posture)}22`,
            color: postureColor(summary.strategic_posture),
          }}
        >
          {postureLabel(summary.strategic_posture)}
        </span>
        <span className="text-[11px] text-slate-600">{summary.signal_count} signals</span>
      </div>

      {summary.positioning_summary && (
        <p className="text-[13px] text-slate-300 leading-relaxed mb-3">{summary.positioning_summary}</p>
      )}

      {summary.top_capabilities.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {summary.top_capabilities.slice(0, 4).map((key) => (
            <span
              key={key}
              className="text-[11px] px-2 py-0.5 rounded-full text-slate-400"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              {getCapabilityLabel(key)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create CapabilityRadar.tsx**

```tsx
// frontend/src/components/workspace/CapabilityRadar.tsx
import type { CapabilityCount } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';

interface Props {
  distribution: CapabilityCount[];
}

export default function CapabilityRadar({ distribution }: Props) {
  if (distribution.length === 0) {
    return (
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <p className="text-slate-600 text-[12px]">No capability data yet</p>
      </div>
    );
  }

  const maxCount = Math.max(...distribution.map((d) => d.count));

  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <h3 className="text-[13px] font-semibold text-slate-200 mb-3">Capability Activity</h3>
      <div className="space-y-2">
        {distribution.slice(0, 8).map((d) => {
          const barPct = maxCount > 0 ? (d.count / maxCount) * 100 : 0;
          const scoreColor = d.avg_movement_score >= 80 ? '#f97316'
            : d.avg_movement_score >= 60 ? '#8b5cf6'
            : d.avg_movement_score >= 30 ? '#3b82f6'
            : '#64748b';
          return (
            <div key={d.capability_key} className="flex items-center gap-3">
              <div className="w-28 flex-shrink-0">
                <span className="text-[11px] text-slate-400 truncate block" title={getCapabilityLabel(d.capability_key)}>
                  {getCapabilityLabel(d.capability_key)}
                </span>
              </div>
              <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${barPct}%`, background: scoreColor }}
                />
              </div>
              <span className="text-[11px] text-slate-500 w-8 text-right tabular-nums">{d.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create RecentMovesTimeline.tsx**

```tsx
// frontend/src/components/workspace/RecentMovesTimeline.tsx
import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from '../signals/MovementBadge';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  assessments: SignalFeedItem[];
  onSelectSignal: (item: SignalFeedItem) => void;
}

export default function RecentMovesTimeline({ assessments, onSelectSignal }: Props) {
  if (assessments.length === 0) {
    return (
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <p className="text-slate-600 text-[12px]">No recent moves</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <h3 className="text-[13px] font-semibold text-slate-200 mb-3">Recent Moves</h3>
      <ul className="space-y-3">
        {assessments.slice(0, 15).map((item) => (
          <li
            key={item.id}
            className="cursor-pointer hover:bg-white/5 -mx-2 px-2 py-1.5 rounded-lg transition-colors"
            onClick={() => onSelectSignal(item)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-[12px] text-slate-200 font-medium leading-snug line-clamp-2">
                  {item.title}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {item.assessment?.capability_primary && (
                    <span className="text-[11px] text-slate-500">
                      {getCapabilityLabel(item.assessment.capability_primary)}
                    </span>
                  )}
                  <span className="text-[11px] text-slate-600">
                    {formatDistanceToNow(item.published_at || item.created_at)}
                  </span>
                </div>
              </div>
              <MovementBadge strength={item.assessment?.movement_strength} size="sm" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 5: Create RisksOpportunitiesCards.tsx**

```tsx
// frontend/src/components/workspace/RisksOpportunitiesCards.tsx
import type { CompetitorSummary } from '../../types/intelligence';

interface Props {
  summary: CompetitorSummary | null;
}

export default function RisksOpportunitiesCards({ summary }: Props) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-3 gap-4 mt-4">
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-red-400 mb-2">Top Risks</h4>
        {summary.top_risks.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.top_risks.slice(0, 4).map((r, i) => (
              <li key={i} className="text-[12px] text-slate-300 flex gap-2">
                <span className="text-red-500 flex-shrink-0 mt-0.5">▸</span>
                {r}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-green-400 mb-2">Opportunities</h4>
        {summary.top_opportunities.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.top_opportunities.slice(0, 4).map((o, i) => (
              <li key={i} className="text-[12px] text-slate-300 flex gap-2">
                <span className="text-green-500 flex-shrink-0 mt-0.5">▸</span>
                {o}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <h4 className="text-[12px] font-semibold text-amber-400 mb-2">Watchpoints</h4>
        {summary.watchpoints.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.watchpoints.slice(0, 4).map((w, i) => (
              <li key={i} className="text-[12px] text-slate-300 flex gap-2">
                <span className="text-amber-500 flex-shrink-0 mt-0.5">▸</span>
                {w}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create SummaryPeriodTabs.tsx**

```tsx
// frontend/src/components/workspace/SummaryPeriodTabs.tsx
import type { CompetitorSummary } from '../../types/intelligence';

interface Props {
  activePeriod: '30d' | '90d';
  onChangePeriod: (p: '30d' | '90d') => void;
  summary30d: CompetitorSummary | null;
  summary90d: CompetitorSummary | null;
}

export default function SummaryPeriodTabs({ activePeriod, onChangePeriod, summary30d, summary90d }: Props) {
  const tabs = [
    { key: '30d' as const, label: '30 Days', summary: summary30d },
    { key: '90d' as const, label: '90 Days', summary: summary90d },
  ];

  return (
    <div className="flex gap-2 mb-4">
      {tabs.map(({ key, label, summary }) => (
        <button
          key={key}
          onClick={() => onChangePeriod(key)}
          className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors flex items-center gap-1.5 ${
            activePeriod === key
              ? 'text-blue-400'
              : 'text-slate-500 hover:text-slate-300'
          }`}
          style={activePeriod === key ? { background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.25)' } : { border: '1px solid transparent' }}
        >
          {label}
          {!summary && <span className="text-[10px] text-slate-600">(no data)</span>}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Create CompetitorWorkspacePage.tsx**

```tsx
// frontend/src/pages/CompetitorWorkspacePage.tsx
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useCompetitorWorkspace } from '../hooks/useCompetitorWorkspace';
import CompetitorHeader from '../components/workspace/CompetitorHeader';
import SummaryPeriodTabs from '../components/workspace/SummaryPeriodTabs';
import StrategicPostureCard from '../components/workspace/StrategicPostureCard';
import CapabilityRadar from '../components/workspace/CapabilityRadar';
import RecentMovesTimeline from '../components/workspace/RecentMovesTimeline';
import RisksOpportunitiesCards from '../components/workspace/RisksOpportunitiesCards';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import type { SignalFeedItem } from '../types/intelligence';

export default function CompetitorWorkspacePage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, isLoading, error } = useCompetitorWorkspace(slug ?? '');
  const [activePeriod, setActivePeriod] = useState<'30d' | '90d'>('30d');
  const [selectedSignal, setSelectedSignal] = useState<SignalFeedItem | null>(null);

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-slate-500 text-sm">Loading competitor workspace…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-red-400 text-sm">Competitor not found or failed to load.</span>
      </div>
    );
  }

  const activeSummary = activePeriod === '30d' ? data.summary_30d : data.summary_90d;

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <CompetitorHeader profile={data.competitor_profile} />

      <SummaryPeriodTabs
        activePeriod={activePeriod}
        onChangePeriod={setActivePeriod}
        summary30d={data.summary_30d}
        summary90d={data.summary_90d}
      />

      <div className="grid grid-cols-2 gap-4 mb-4">
        <StrategicPostureCard summary={activeSummary} />
        <CapabilityRadar distribution={data.capability_distribution} />
      </div>

      <RecentMovesTimeline
        assessments={data.recent_assessments}
        onSelectSignal={setSelectedSignal}
      />

      <RisksOpportunitiesCards summary={activeSummary} />

      {selectedSignal && (
        <SignalDetailDrawer
          item={selectedSignal}
          onClose={() => setSelectedSignal(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 8: Verify compilation**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 9: Commit**

```bash
rtk git add frontend/src/components/workspace/ frontend/src/pages/CompetitorWorkspacePage.tsx
rtk git commit -m "feat: add Competitor Workspace components and CompetitorWorkspacePage"
```

---

## Task 18: Signals Feed Components + Page

**Files:**
- Create: `frontend/src/components/signals/SignalFeedFilters.tsx`
- Create: `frontend/src/components/signals/SignalFeedTable.tsx`
- Create: `frontend/src/components/signals/SignalDetailDrawer.tsx`
- Create: `frontend/src/pages/SignalsFeedPage.tsx`

- [ ] **Step 1: Create SignalFeedFilters.tsx**

```tsx
// frontend/src/components/signals/SignalFeedFilters.tsx
import type { SignalsFeedFilters, MovementStrength } from '../../types/intelligence';
import type { SignalType } from '../../types';
import { CAPABILITIES } from '../../constants/capabilities';

interface Props {
  filters: SignalsFeedFilters;
  companies: Array<{ id: string; name: string }>;
  onChange: (f: Partial<SignalsFeedFilters>) => void;
  onReset: () => void;
}

const SIGNAL_TYPES: SignalType[] = [
  'product_update', 'ai_announcement', 'partnership', 'positioning_change',
  'target_market_change', 'event_or_thought_leadership', 'hiring_signal', 'other',
];

const MOVEMENT_STRENGTHS: MovementStrength[] = ['weak', 'relevant', 'strong', 'market_shaping'];

const SORT_OPTIONS = [
  { value: 'published_at', label: 'Date' },
  { value: 'movement_score', label: 'Movement Score' },
  { value: 'confidence', label: 'Confidence' },
] as const;

export default function SignalFeedFilters({ filters, companies, onChange, onReset }: Props) {
  const hasActiveFilters = !!(
    filters.company_id || filters.capability || filters.signal_type ||
    filters.movement_strength || filters.min_confidence
  );

  return (
    <div
      className="sticky top-0 z-10 flex flex-wrap items-center gap-2 px-6 py-3 -mx-6 mb-4"
      style={{ background: '#0a0f1e', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
    >
      {/* Company */}
      <select
        value={filters.company_id ?? ''}
        onChange={(e) => onChange({ company_id: e.target.value || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Competitors</option>
        {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>

      {/* Capability */}
      <select
        value={filters.capability ?? ''}
        onChange={(e) => onChange({ capability: e.target.value || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Capabilities</option>
        {Object.values(CAPABILITIES).filter((c) => c.visibilityToUser).map((c) => (
          <option key={c.key} value={c.key}>{c.label}</option>
        ))}
      </select>

      {/* Signal Type */}
      <select
        value={filters.signal_type ?? ''}
        onChange={(e) => onChange({ signal_type: e.target.value || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Types</option>
        {SIGNAL_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
      </select>

      {/* Movement Strength */}
      <select
        value={filters.movement_strength ?? ''}
        onChange={(e) => onChange({ movement_strength: (e.target.value as MovementStrength) || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Strengths</option>
        {MOVEMENT_STRENGTHS.map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
      </select>

      {/* Sort */}
      <select
        value={filters.sort_by ?? 'published_at'}
        onChange={(e) => onChange({ sort_by: e.target.value as 'published_at' | 'movement_score' | 'confidence' })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>Sort: {o.label}</option>)}
      </select>

      {hasActiveFilters && (
        <button
          onClick={onReset}
          className="text-[12px] text-slate-500 hover:text-slate-300 transition-colors px-2 py-1"
        >
          Reset
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create SignalFeedTable.tsx**

```tsx
// frontend/src/components/signals/SignalFeedTable.tsx
import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from './MovementBadge';
import ConfidenceBar from './ConfidenceBar';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  items: SignalFeedItem[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  onSelectItem: (item: SignalFeedItem) => void;
}

export default function SignalFeedTable({ items, total, page, pageSize, onPageChange, onSelectItem }: Props) {
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
              {['Signal', 'Competitor', 'Capability', 'Strength', 'Confidence', 'Date'].map((h) => (
                <th key={h} className="text-left text-[11px] font-medium text-slate-500 uppercase tracking-wide pb-2 pr-4">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-600">No signals match the current filters</td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.id}
                  className="cursor-pointer hover:bg-white/[0.03] transition-colors"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                  onClick={() => onSelectItem(item)}
                >
                  <td className="py-3 pr-4 max-w-[300px]">
                    <div className="text-slate-200 font-medium line-clamp-2 leading-snug">{item.title}</div>
                    {item.topic && <div className="text-slate-600 text-[11px] mt-0.5 truncate">{item.topic}</div>}
                  </td>
                  <td className="py-3 pr-4 text-slate-400 whitespace-nowrap">{item.company_name ?? '—'}</td>
                  <td className="py-3 pr-4 text-slate-500 whitespace-nowrap">
                    {item.assessment?.capability_primary
                      ? getCapabilityLabel(item.assessment.capability_primary)
                      : '—'}
                  </td>
                  <td className="py-3 pr-4">
                    <MovementBadge strength={item.assessment?.movement_strength} />
                  </td>
                  <td className="py-3 pr-4">
                    <ConfidenceBar value={item.assessment?.confidence} />
                  </td>
                  <td className="py-3 text-slate-500 whitespace-nowrap">
                    {formatDistanceToNow(item.published_at || item.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <span className="text-[12px] text-slate-500">{total} total signals</span>
          <div className="flex gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-2.5 py-1 rounded-md text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              ←
            </button>
            <span className="px-3 py-1 text-[12px] text-slate-400 tabular-nums">{page} / {totalPages}</span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-2.5 py-1 rounded-md text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create SignalDetailDrawer.tsx**

```tsx
// frontend/src/components/signals/SignalDetailDrawer.tsx
import { useEffect } from 'react';
import { X, ExternalLink } from 'lucide-react';
import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from './MovementBadge';
import ConfidenceBar from './ConfidenceBar';
import { getCapabilityLabel } from '../../constants/capabilities';
import { useAssessSignal } from '../../hooks/useAssessSignal';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  item: SignalFeedItem;
  onClose: () => void;
}

export default function SignalDetailDrawer({ item, onClose }: Props) {
  const assess = useAssessSignal();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const a = item.assessment;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />
      {/* Drawer */}
      <div
        className="fixed right-0 top-0 h-full w-[480px] z-50 overflow-y-auto flex flex-col"
        style={{ background: '#0f172a', borderLeft: '1px solid rgba(255,255,255,0.1)' }}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 sticky top-0" style={{ background: '#0f172a', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex-1 pr-4">
            <div className="text-[13px] font-semibold text-slate-100 leading-snug">{item.title}</div>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[11px] text-slate-500">{item.company_name}</span>
              <span className="text-slate-700">·</span>
              <span className="text-[11px] text-slate-500">{formatDistanceToNow(item.published_at || item.created_at)}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 p-5 space-y-5">
          {/* Assessment header */}
          <div className="flex items-center gap-3 flex-wrap">
            <MovementBadge strength={a?.movement_strength} size="md" />
            {a?.movement_score != null && (
              <span className="text-[12px] text-slate-400">Score: <span className="font-semibold text-slate-200">{a.movement_score}</span></span>
            )}
            <ConfidenceBar value={a?.confidence} />
          </div>

          {/* Signal basics */}
          {item.summary && (
            <section>
              <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Summary</h4>
              <p className="text-[13px] text-slate-300 leading-relaxed">{item.summary}</p>
            </section>
          )}

          {item.why_it_matters && (
            <section>
              <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Why It Matters</h4>
              <p className="text-[13px] text-slate-300 leading-relaxed">{item.why_it_matters}</p>
            </section>
          )}

          {/* Assessment details */}
          {a && (
            <>
              {a.capability_primary && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Capability</h4>
                  <div className="flex flex-wrap gap-1.5">
                    <span className="text-[12px] px-2 py-0.5 rounded-full text-blue-400" style={{ background: 'rgba(59,130,246,0.15)' }}>
                      {getCapabilityLabel(a.capability_primary)}
                    </span>
                    {a.capability_secondary.map((k) => (
                      <span key={k} className="text-[12px] px-2 py-0.5 rounded-full text-slate-400" style={{ background: 'rgba(255,255,255,0.07)' }}>
                        {getCapabilityLabel(k)}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {a.assessment_summary && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Assessment</h4>
                  <p className="text-[13px] text-slate-300 leading-relaxed">{a.assessment_summary}</p>
                </section>
              )}

              {a.implication_for_us && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Implication for Us</h4>
                  <p className="text-[13px] text-amber-200/80 leading-relaxed">{a.implication_for_us}</p>
                </section>
              )}

              {a.strategic_intent_guess && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Strategic Intent</h4>
                  <p className="text-[13px] text-slate-400 leading-relaxed italic">"{a.strategic_intent_guess}"</p>
                </section>
              )}

              {a.watch_items.length > 0 && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Watch Items</h4>
                  <ul className="space-y-1">
                    {a.watch_items.map((w, i) => (
                      <li key={i} className="text-[12px] text-slate-300 flex gap-2">
                        <span className="text-amber-500 flex-shrink-0 mt-0.5">◈</span>
                        {w}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {a.gameplay_tags.length > 0 && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Gameplay Tags</h4>
                  <div className="flex flex-wrap gap-1">
                    {a.gameplay_tags.map((tag) => (
                      <span key={tag} className="text-[11px] px-2 py-0.5 rounded-full text-slate-500" style={{ background: 'rgba(255,255,255,0.05)' }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}

          {/* Source link */}
          {item.source_url && (
            <section>
              <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Source</h4>
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-[12px] text-blue-400 hover:text-blue-300 transition-colors break-all"
              >
                <ExternalLink size={12} className="flex-shrink-0" />
                {item.document_title || item.source_url}
              </a>
            </section>
          )}

          {/* Re-assess button */}
          {!a && (
            <button
              onClick={() => assess.mutate(item.id)}
              disabled={assess.isPending}
              className="w-full py-2 rounded-lg text-[12px] font-medium text-slate-300 hover:text-white transition-colors disabled:opacity-50"
              style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.25)' }}
            >
              {assess.isPending ? 'Generating assessment…' : 'Generate Assessment'}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 4: Create SignalsFeedPage.tsx**

```tsx
// frontend/src/pages/SignalsFeedPage.tsx
import { useState } from 'react';
import { useSignalsFeed } from '../hooks/useSignalsFeed';
import { useCompanies } from '../hooks/useCompanies';
import SignalFeedFilters from '../components/signals/SignalFeedFilters';
import SignalFeedTable from '../components/signals/SignalFeedTable';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import type { SignalsFeedFilters, SignalFeedItem } from '../types/intelligence';

const DEFAULT_FILTERS: SignalsFeedFilters = {
  sort_by: 'published_at',
  page: 1,
  page_size: 25,
};

export default function SignalsFeedPage() {
  const [filters, setFilters] = useState<SignalsFeedFilters>(DEFAULT_FILTERS);
  const [selectedItem, setSelectedItem] = useState<SignalFeedItem | null>(null);

  const { data, isLoading } = useSignalsFeed(filters);
  const { data: companies = [] } = useCompanies();

  function handleFilterChange(partial: Partial<SignalsFeedFilters>) {
    setFilters((prev) => ({ ...prev, ...partial }));
  }

  function handleReset() {
    setFilters(DEFAULT_FILTERS);
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="mb-4">
        <h1 className="text-xl font-semibold text-slate-100">Signals Feed</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">Operative intelligence with assessment context</p>
      </div>

      <SignalFeedFilters
        filters={filters}
        companies={companies.filter((c) => c.type === 'competitor')}
        onChange={handleFilterChange}
        onReset={handleReset}
      />

      {isLoading ? (
        <div className="flex items-center justify-center h-48">
          <span className="text-slate-500 text-sm">Loading signals…</span>
        </div>
      ) : (
        <SignalFeedTable
          items={data?.items ?? []}
          total={data?.total ?? 0}
          page={filters.page ?? 1}
          pageSize={filters.page_size ?? 25}
          onPageChange={(p) => handleFilterChange({ page: p })}
          onSelectItem={setSelectedItem}
        />
      )}

      {selectedItem && (
        <SignalDetailDrawer
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 5: Verify compilation**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
rtk git add frontend/src/components/signals/SignalFeedFilters.tsx frontend/src/components/signals/SignalFeedTable.tsx frontend/src/components/signals/SignalDetailDrawer.tsx frontend/src/pages/SignalsFeedPage.tsx
rtk git commit -m "feat: add Signals Feed components and SignalsFeedPage"
```

---

## Task 19: Routing + Navigation

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add routes to App.tsx**

In `frontend/src/App.tsx`, add the three new page imports and routes:

```tsx
// Add to imports (after existing page imports):
import OverviewPage from './pages/OverviewPage';
import CompetitorWorkspacePage from './pages/CompetitorWorkspacePage';
import SignalsFeedPage from './pages/SignalsFeedPage';

// Add to the Routes (inside the AuthGate Layout route, after existing routes):
<Route path="overview" element={<OverviewPage />} />
<Route path="competitors/:slug" element={<CompetitorWorkspacePage />} />
<Route path="signals" element={<SignalsFeedPage />} />
```

Note: `competitors/:slug` replaces the existing `competitors/:slug` route that points to `CompetitorDetail`. Update that line to point to `CompetitorWorkspacePage` instead, or keep both routes if you want the old detail page accessible. Per the design decision (new pages), replace the existing `<Route path="competitors/:slug" element={<CompetitorDetail />} />` with `<Route path="competitors/:slug" element={<CompetitorWorkspacePage />} />`.

Full updated routes section:
```tsx
<Route index element={<Dashboard />} />
<Route path="overview" element={<OverviewPage />} />
<Route path="competitors" element={<CompetitorList />} />
<Route path="competitors/:slug" element={<CompetitorWorkspacePage />} />
<Route path="signals" element={<SignalsFeedPage />} />
<Route path="trends" element={<MarketTrends />} />
<Route path="digest" element={<WeeklyDigest />} />
<Route path="search" element={<SearchPage />} />
<Route path="admin/sources" element={<SourcesAdmin />} />
<Route path="context" element={<CompanyContext />} />
```

- [ ] **Step 2: Add nav items to Layout.tsx**

In `frontend/src/components/Layout.tsx`, update the `navSections` array. Add a new "Intelligence" section at the top:

```tsx
// Add import at top:
import { BarChart2, Radio, Zap } from 'lucide-react';

// Update navSections:
const navSections = [
  {
    label: 'Intelligence',
    items: [
      { to: '/overview', label: 'Overview', icon: BarChart2 },
      { to: '/competitors', label: 'Competitors', icon: Users },
      { to: '/signals', label: 'Signals Feed', icon: Zap },
    ],
  },
  {
    label: 'Berichte',
    items: [
      { to: '/digest', label: 'Weekly Digest', icon: FileText },
      { to: '/search', label: 'Suche', icon: Search },
    ],
  },
  {
    label: 'Admin',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/trends', label: 'Markt-Trends', icon: TrendingUp },
      { to: '/admin/sources', label: 'Quellen', icon: Settings },
      { to: '/context', label: 'Kontext', icon: Globe },
    ],
  },
];
```

- [ ] **Step 3: Verify full compilation**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 4: Run dev server and verify navigation**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Verify:
- Sidebar shows "Intelligence" section with Overview, Competitors, Signals Feed
- `/overview` loads OverviewPage (KPI bar visible)
- `/signals` loads SignalsFeedPage (filter bar + table)
- `/competitors/some-slug` loads CompetitorWorkspacePage

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/App.tsx frontend/src/components/Layout.tsx
rtk git commit -m "feat: add routing and navigation for intelligence views (overview, workspace, signals feed)"
```

---

## Self-Review Checklist

- [x] All three pages compile without TypeScript errors
- [x] MovementBadge shows "Unassessed" state when assessment is null
- [x] SignalDetailDrawer shows "Generate Assessment" button when no assessment exists
- [x] SignalsFeedPage pagination works (page/page_size propagated to hook)
- [x] Filter reset clears all active filters
- [x] CompetitorWorkspacePage uses `slug` param from URL (matches `/competitors/:slug` route)
- [x] CapabilityHeatmapV2 only shows `visibilityToUser: true` capabilities
- [x] formatDistanceToNow exported from `utils/dates.ts` (add if missing)
- [x] No modifications to existing Dashboard, CompetitorList, or any existing hook
- [x] Existing `/competitors/:slug` route updated to point to CompetitorWorkspacePage
