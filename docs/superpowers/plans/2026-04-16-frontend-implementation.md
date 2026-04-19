# WFM Market Intelligence — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete React 18 + TypeScript + Vite frontend for the WFM Market Intelligence Hub, connecting to the existing FastAPI backend via HTTP Basic Auth.

**Architecture:** Single-page React app with TanStack Query for server state, React Router v6 for client-side routing, TailwindCSS for dark-theme styling. All API calls go through a fetch wrapper that attaches Basic Auth headers. Pages follow the 7 routes defined in the spec.

**Tech Stack:** React 18, TypeScript 5, Vite 5, TanStack Query v5, React Router v6, TailwindCSS v3, react-markdown, lucide-react (icons)

---

## File Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts              # Fetch wrapper with Basic Auth + error handling
│   ├── types/
│   │   └── index.ts               # TypeScript interfaces matching backend schemas
│   ├── hooks/
│   │   ├── useCompanies.ts        # TanStack Query hooks for /api/companies
│   │   ├── useSources.ts          # TanStack Query hooks for /api/sources
│   │   ├── useDocuments.ts        # TanStack Query hooks for /api/documents
│   │   ├── useSignals.ts          # TanStack Query hooks for /api/signals
│   │   ├── useDigests.ts          # TanStack Query hooks for /api/digests
│   │   ├── useContext.ts           # TanStack Query hooks for /api/context
│   │   └── useCrawl.ts            # TanStack mutation for /api/crawl/run
│   ├── components/
│   │   ├── Layout.tsx             # Shell: sidebar nav + main content area
│   │   ├── SignalCard.tsx          # Signal display with type color + relevance badge
│   │   ├── FilterBar.tsx           # Competitor/type/date/relevance filters
│   │   ├── RelevanceBadge.tsx      # Color-coded score: green ≥0.7, yellow ≥0.4, red <0.4
│   │   ├── MarkdownViewer.tsx      # Render markdown via react-markdown
│   │   ├── TagList.tsx             # Render string arrays as pill tags
│   │   └── SignalTypeIcon.tsx      # Map signal_type to lucide icon
│   ├── pages/
│   │   ├── Dashboard.tsx           # / → KPI cards + latest signals + filters
│   │   ├── CompetitorList.tsx      # /competitors → list with signal counts
│   │   ├── CompetitorDetail.tsx    # /competitors/:slug → signals timeline
│   │   ├── MarketTrends.tsx        # /trends → market_source signals
│   │   ├── WeeklyDigest.tsx        # /digest → weekly list + generate
│   │   ├── SourcesAdmin.tsx        # /admin/sources → CRUD companies + sources + crawl trigger
│   │   └── CompanyContext.tsx       # /context → view + edit InternalCompanyContext
│   ├── App.tsx                     # Router + QueryClientProvider + Layout
│   ├── main.tsx                    # Entry point
│   └── index.css                  # Tailwind directives + custom dark theme
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── Dockerfile
```

---

## Task 1: Project Scaffolding — Vite + React + TypeScript

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/.gitignore`

- [ ] **Step 1: Scaffold Vite project**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install core dependencies**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
npm install react-router-dom @tanstack/react-query react-markdown lucide-react
npm install -D tailwindcss postcss autoprefixer @tailwindcss/typography
npx tailwindcss init -p
```

- [ ] **Step 3: Configure Tailwind for dark theme**

Replace `frontend/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0f1117',
          card: '#1a1d2e',
          border: '#2a2d3e',
          text: '#e2e8f0',
          muted: '#94a3b8',
          accent: '#6366f1',
        },
        signal: {
          high: '#22c55e',
          medium: '#eab308',
          low: '#ef4444',
        },
        type: {
          product_update: '#3b82f6',
          ai_announcement: '#8b5cf6',
          partnership: '#06b6d4',
          positioning_change: '#f97316',
          target_market_change: '#ec4899',
          event_or_thought_leadership: '#14b8a6',
          hiring_signal: '#f59e0b',
          other: '#6b7280',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
```

- [ ] **Step 4: Create global CSS with Tailwind directives**

Replace `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    @apply bg-dark-bg text-dark-text;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
  }
}

@layer components {
  .card {
    @apply bg-dark-card border border-dark-border rounded-lg p-4;
  }
  .btn-primary {
    @apply bg-dark-accent hover:bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors;
  }
  .btn-secondary {
    @apply bg-dark-border hover:bg-slate-700 text-dark-text px-4 py-2 rounded-md text-sm font-medium transition-colors;
  }
  .input-field {
    @apply bg-dark-bg border border-dark-border rounded-md px-3 py-2 text-dark-text text-sm focus:outline-none focus:ring-1 focus:ring-dark-accent;
  }
}
```

- [ ] **Step 5: Update App.tsx to minimal placeholder**

Replace `frontend/src/App.tsx`:

```tsx
function App() {
  return (
    <div className="min-h-screen bg-dark-bg text-dark-text">
      <h1 className="text-xl p-4">WFM Market Intelligence Hub</h1>
    </div>
  );
}

export default App;
```

- [ ] **Step 6: Update main.tsx with proper entry**

Replace `frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 7: Verify dev server starts**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
npm run dev
```

Expected: Vite dev server starts at http://localhost:5173, page renders "WFM Market Intelligence Hub" in dark theme.

- [ ] **Step 8: Commit scaffolding**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence
git add frontend/
git commit -m "feat: scaffold Vite + React + TypeScript frontend with Tailwind dark theme"
```

---

## Task 2: API Client — Fetch Wrapper with Basic Auth

**Files:**
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write the API client**

Create `frontend/src/api/client.ts`:

```typescript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function getCredentials(): { username: string; password: string } {
  const stored = localStorage.getItem('wfm_credentials');
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      localStorage.removeItem('wfm_credentials');
    }
  }
  return { username: '', password: '' };
}

function authHeader(): Record<string, string> {
  const { username, password } = getCredentials();
  if (!username || !password) return {};
  const encoded = btoa(`${username}:${password}`);
  return { Authorization: `Basic ${encoded}` };
}

function headers(extra?: Record<string, string>): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    ...authHeader(),
    ...extra,
  };
}

export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        url.searchParams.set(k, v);
      }
    });
  }
  const res = await fetch(url.toString(), { headers: headers() });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: headers(),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
  return res.json();
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export function setCredentials(username: string, password: string): void {
  localStorage.setItem('wfm_credentials', JSON.stringify({ username, password }));
}

export function clearCredentials(): void {
  localStorage.removeItem('wfm_credentials');
}

export function hasCredentials(): boolean {
  const { username, password } = getCredentials();
  return !!username && !!password;
}
```

- [ ] **Step 2: Commit API client**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/api/client.ts
git commit -m "feat: add API client with Basic Auth fetch wrapper"
```

---

## Task 3: TypeScript Types — Matching Backend Schemas

**Files:**
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: Write TypeScript interfaces**

Create `frontend/src/types/index.ts`:

```typescript
export type CompanyType = 'competitor' | 'market_source';

export interface Company {
  id: string;
  name: string;
  slug: string;
  type: CompanyType;
  description: string | null;
  website: string | null;
  created_at: string;
}

export interface CompanyCreate {
  name: string;
  slug: string;
  type: CompanyType;
  description?: string | null;
  website?: string | null;
}

export interface CompanyUpdate {
  name?: string;
  description?: string | null;
  website?: string | null;
}

export type SourceType = 'news' | 'blog' | 'product' | 'press' | 'jobs';

export interface Source {
  id: string;
  company_id: string;
  url: string;
  label: string | null;
  source_type: SourceType;
  is_active: boolean;
  last_crawled_at: string | null;
  created_at: string;
}

export interface SourceCreate {
  company_id: string;
  url: string;
  label?: string | null;
  source_type: SourceType;
  is_active?: boolean;
}

export interface SourceUpdate {
  label?: string | null;
  source_type?: SourceType;
  is_active?: boolean;
}

export interface Document {
  id: string;
  source_id: string;
  url: string;
  title: string | null;
  content_markdown: string | null;
  published_at: string | null;
  crawled_at: string;
  content_hash: string | null;
  is_analysed: boolean;
}

export type SignalType =
  | 'product_update'
  | 'ai_announcement'
  | 'partnership'
  | 'positioning_change'
  | 'target_market_change'
  | 'event_or_thought_leadership'
  | 'hiring_signal'
  | 'other';

export interface Signal {
  id: string;
  document_id: string;
  company_id: string;
  title: string;
  signal_type: SignalType;
  topic: string | null;
  summary: string | null;
  why_it_matters: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  published_at: string | null;
  created_at: string;
}

export interface Digest {
  id: string;
  week_start: string;
  week_end: string;
  summary: string | null;
  key_signals: string[];
  generated_at: string;
  is_published: boolean;
}

export interface Context {
  id: string;
  company_name: string | null;
  short_description: string | null;
  target_industries: string[];
  target_segments: string[];
  core_capabilities: string[];
  strategic_priorities: string[];
  differentiators: string[];
  relevant_competitive_areas: string[];
  non_focus_areas: string[];
  updated_at: string;
}

export interface ContextUpdate {
  company_name?: string | null;
  short_description?: string | null;
  target_industries?: string[];
  target_segments?: string[];
  core_capabilities?: string[];
  strategic_priorities?: string[];
  differentiators?: string[];
  relevant_competitive_areas?: string[];
  non_focus_areas?: string[];
}

export interface CrawlResult {
  sources_processed: number;
  results: unknown[];
}

export interface CrawlSingleResult {
  source_id: string;
  document_id?: string;
  status: string;
}
```

- [ ] **Step 2: Commit types**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/types/index.ts
git commit -m "feat: add TypeScript interfaces matching backend schemas"
```

---

## Task 4: TanStack Query Hooks — Data Fetching Layer

**Files:**
- Create: `frontend/src/hooks/useCompanies.ts`
- Create: `frontend/src/hooks/useSources.ts`
- Create: `frontend/src/hooks/useDocuments.ts`
- Create: `frontend/src/hooks/useSignals.ts`
- Create: `frontend/src/hooks/useDigests.ts`
- Create: `frontend/src/hooks/useContext.ts`
- Create: `frontend/src/hooks/useCrawl.ts`

- [ ] **Step 1: Create useCompanies hook**

Create `frontend/src/hooks/useCompanies.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut } from '../api/client';
import type { Company, CompanyCreate, CompanyUpdate } from '../types';

export function useCompanies() {
  return useQuery<Company[]>({
    queryKey: ['companies'],
    queryFn: () => apiGet<Company[]>('/companies'),
  });
}

export function useCompany(slug: string) {
  return useQuery<Company>({
    queryKey: ['companies', slug],
    queryFn: () => apiGet<Company>(`/companies/${slug}`),
    enabled: !!slug,
  });
}

export function useCreateCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CompanyCreate) => apiPost<Company>('/companies', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  });
}

export function useUpdateCompany(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CompanyUpdate) => apiPut<Company>(`/companies/${slug}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['companies'] });
      qc.invalidateQueries({ queryKey: ['companies', slug] });
    },
  });
}
```

- [ ] **Step 2: Create useSources hook**

Create `frontend/src/hooks/useSources.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client';
import type { Source, SourceCreate, SourceUpdate } from '../types';

export function useSources(companyId?: string) {
  const params = companyId ? { company_id: companyId } : undefined;
  return useQuery<Source[]>({
    queryKey: ['sources', params],
    queryFn: () => apiGet<Source[]>('/sources', params),
  });
}

export function useCreateSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SourceCreate) => apiPost<Source>('/sources', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });
}

export function useUpdateSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sourceId, data }: { sourceId: string; data: SourceUpdate }) =>
      apiPut<Source>(`/sources/${sourceId}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });
}

export function useDeleteSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => apiDelete(`/sources/${sourceId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });
}
```

- [ ] **Step 3: Create useDocuments hook**

Create `frontend/src/hooks/useDocuments.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { Document } from '../types';

export function useDocuments(sourceId?: string) {
  const params = sourceId ? { source_id: sourceId } : undefined;
  return useQuery<Document[]>({
    queryKey: ['documents', params],
    queryFn: () => apiGet<Document[]>('/documents', params),
  });
}

export function useDocument(id: string) {
  return useQuery<Document>({
    queryKey: ['documents', id],
    queryFn: () => apiGet<Document>(`/documents/${id}`),
    enabled: !!id,
  });
}
```

- [ ] **Step 4: Create useSignals hook**

Create `frontend/src/hooks/useSignals.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { Signal, SignalType } from '../types';

export interface SignalsFilters {
  company_id?: string;
  signal_type?: SignalType;
  min_relevance?: number;
}

export function useSignals(filters?: SignalsFilters) {
  const params: Record<string, string> = {};
  if (filters?.company_id) params.company_id = filters.company_id;
  if (filters?.signal_type) params.signal_type = filters.signal_type;
  if (filters?.min_relevance !== undefined) params.min_relevance = String(filters.min_relevance);

  return useQuery<Signal[]>({
    queryKey: ['signals', params],
    queryFn: () => apiGet<Signal[]>('/signals', params),
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

- [ ] **Step 5: Create useDigests hook**

Create `frontend/src/hooks/useDigests.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type { Digest } from '../types';

export function useDigests() {
  return useQuery<Digest[]>({
    queryKey: ['digests'],
    queryFn: () => apiGet<Digest[]>('/digests'),
  });
}

export function useDigest(id: string) {
  return useQuery<Digest>({
    queryKey: ['digests', id],
    queryFn: () => apiGet<Digest>(`/digests/${id}`),
    enabled: !!id,
  });
}

export function useGenerateDigest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<Digest>('/digests/generate'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['digests'] }),
  });
}
```

- [ ] **Step 6: Create useContext hook**

Create `frontend/src/hooks/useContext.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut } from '../api/client';
import type { Context, ContextUpdate } from '../types';

export function useContextData() {
  return useQuery<Context>({
    queryKey: ['context'],
    queryFn: () => apiGet<Context>('/context'),
  });
}

export function useUpdateContext() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ContextUpdate) => apiPut<Context>('/context', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['context'] }),
  });
}
```

- [ ] **Step 7: Create useCrawl hook**

Create `frontend/src/hooks/useCrawl.ts`:

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
import type { CrawlResult, CrawlSingleResult } from '../types';

export function useCrawlAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<CrawlResult>('/crawl/run'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['sources'] });
    },
  });
}

export function useCrawlSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => apiPost<CrawlSingleResult>(`/crawl/run/${sourceId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['sources'] });
    },
  });
}
```

- [ ] **Step 8: Commit all hooks**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/hooks/
git commit -m "feat: add TanStack Query hooks for all API endpoints"
```

---

## Task 5: Shared Components — Layout, SignalCard, RelevanceBadge, Filters

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/SignalCard.tsx`
- Create: `frontend/src/components/RelevanceBadge.tsx`
- Create: `frontend/src/components/FilterBar.tsx`
- Create: `frontend/src/components/MarkdownViewer.tsx`
- Create: `frontend/src/components/TagList.tsx`
- Create: `frontend/src/components/SignalTypeIcon.tsx`

- [ ] **Step 1: Create Layout component (sidebar nav + content area)**

Create `frontend/src/components/Layout.tsx`:

```tsx
import { NavLink, Outlet } from 'react-router-dom';
import {
  BarChart3,
  Users,
  TrendingUp,
  Calendar,
  Settings,
  Globe,
  LogOut,
} from 'lucide-react';
import { hasCredentials, clearCredentials } from '../api/client';
import { useNavigate } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/competitors', label: 'Competitors', icon: Users },
  { to: '/trends', label: 'Market Trends', icon: TrendingUp },
  { to: '/digest', label: 'Weekly Digest', icon: Calendar },
  { to: '/admin/sources', label: 'Sources Admin', icon: Settings },
  { to: '/context', label: 'Company Context', icon: Globe },
];

export default function Layout() {
  const navigate = useNavigate();

  function handleLogout() {
    clearCredentials();
    navigate('/login');
  }

  if (!hasCredentials()) {
    navigate('/login');
    return null;
  }

  return (
    <div className="flex h-screen">
      <nav className="w-56 bg-dark-card border-r border-dark-border flex flex-col">
        <div className="p-4 border-b border-dark-border">
          <h1 className="text-lg font-bold text-dark-text">WFM Intel</h1>
          <p className="text-xs text-dark-muted">Market Intelligence Hub</p>
        </div>
        <div className="flex-1 py-2">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-dark-accent/10 text-dark-accent border-r-2 border-dark-accent'
                    : 'text-dark-muted hover:text-dark-text hover:bg-dark-bg'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>
        <div className="p-4 border-t border-dark-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-dark-muted hover:text-dark-text transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </nav>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create RelevanceBadge component**

Create `frontend/src/components/RelevanceBadge.tsx`:

```tsx
interface RelevanceBadgeProps {
  score: number | null;
  size?: 'sm' | 'md';
}

export default function RelevanceBadge({ score, size = 'md' }: RelevanceBadgeProps) {
  if (score === null || score === undefined) {
    return <span className={`text-dark-muted ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>N/A</span>;
  }

  const pct = Math.round(score * 100);
  let colorClass: string;
  if (score >= 0.7) {
    colorClass = 'bg-signal-high/20 text-signal-high';
  } else if (score >= 0.4) {
    colorClass = 'bg-signal-medium/20 text-signal-medium';
  } else {
    colorClass = 'bg-signal-low/20 text-signal-low';
  }

  const sizeClass = size === 'sm' ? 'text-xs px-1.5 py-0.5' : 'text-sm px-2 py-1';

  return (
    <span className={`inline-flex items-center rounded font-medium ${colorClass} ${sizeClass}`}>
      {pct}%
    </span>
  );
}
```

- [ ] **Step 3: Create SignalTypeIcon component**

Create `frontend/src/components/SignalTypeIcon.tsx`:

```tsx
import {
  Package,
  Brain,
  Handshake,
  Compass,
  Target,
  Calendar,
  UserPlus,
  HelpCircle,
} from 'lucide-react';
import type { SignalType } from '../types';

const iconMap: Record<SignalType, React.ComponentType<{ size?: number }>> = {
  product_update: Package,
  ai_announcement: Brain,
  partnership: Handshake,
  positioning_change: Compass,
  target_market_change: Target,
  event_or_thought_leadership: Calendar,
  hiring_signal: UserPlus,
  other: HelpCircle,
};

const labelMap: Record<SignalType, string> = {
  product_update: 'Product Update',
  ai_announcement: 'AI Announcement',
  partnership: 'Partnership',
  positioning_change: 'Positioning Change',
  target_market_change: 'Market Shift',
  event_or_thought_leadership: 'Thought Leadership',
  hiring_signal: 'Hiring Signal',
  other: 'Other',
};

interface SignalTypeIconProps {
  type: SignalType;
  showLabel?: boolean;
  size?: number;
}

export default function SignalTypeIcon({ type, showLabel = true, size = 16 }: SignalTypeIconProps) {
  const Icon = iconMap[type];
  const colorClass = `text-type-${type}`;

  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon size={size} className={colorClass} />
      {showLabel && <span className={`text-sm ${colorClass}`}>{labelMap[type]}</span>}
    </span>
  );
}

export { labelMap };
```

- [ ] **Step 4: Create SignalCard component**

Create `frontend/src/components/SignalCard.tsx`:

```tsx
import { Link } from 'react-router-dom';
import type { Signal } from '../types';
import RelevanceBadge from './RelevanceBadge';
import SignalTypeIcon from './SignalTypeIcon';

interface SignalCardProps {
  signal: Signal;
  showCompany?: boolean;
  companyName?: string;
  companySlug?: string;
}

export default function SignalCard({ signal, showCompany = false, companyName, companySlug }: SignalCardProps) {
  const dateStr = signal.published_at
    ? new Date(signal.published_at).toLocaleDateString('de-DE')
    : new Date(signal.created_at).toLocaleDateString('de-DE');

  const linkTarget = companySlug
    ? `/competitors/${companySlug}`
    : `/competitors/${signal.company_id}`;

  return (
    <Link
      to={linkTarget}
      className="card block hover:border-dark-accent/50 transition-colors"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-dark-text truncate">{signal.title}</h3>
          <div className="flex items-center gap-2 mt-1">
            <SignalTypeIcon type={signal.signal_type} size={14} />
            {signal.topic && (
              <span className="text-xs text-dark-muted px-1.5 py-0.5 bg-dark-bg rounded">
                {signal.topic}
              </span>
            )}
          </div>
        </div>
        <RelevanceBadge score={signal.relevance_score} size="sm" />
      </div>
      {signal.summary && (
        <p className="text-sm text-dark-muted line-clamp-2 mb-2">{signal.summary}</p>
      )}
      {signal.why_it_matters && (
        <p className="text-xs text-indigo-300 line-clamp-2 mb-2">
          <span className="font-medium">Why it matters:</span> {signal.why_it_matters}
        </p>
      )}
      <div className="flex items-center justify-between mt-2 text-xs text-dark-muted">
        <span>{dateStr}</span>
        {showCompany && companyName && (
          <span className="text-dark-accent">{companyName}</span>
        )}
      </div>
    </Link>
  );
}
```

- [ ] **Step 5: Create FilterBar component**

Create `frontend/src/components/FilterBar.tsx`:

```tsx
import type { SignalType, CompanyType } from '../types';

interface FilterBarProps {
  signalType: SignalType | '';
  onSignalTypeChange: (v: SignalType | '') => void;
  minRelevance: number;
  onMinRelevanceChange: (v: number) => void;
  companyId?: string;
  onCompanyChange?: (v: string) => void;
  companies?: { id: string; name: string; type: CompanyType }[];
}

const signalTypes: { value: SignalType; label: string }[] = [
  { value: 'product_update', label: 'Product Update' },
  { value: 'ai_announcement', label: 'AI Announcement' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'positioning_change', label: 'Positioning Change' },
  { value: 'target_market_change', label: 'Market Shift' },
  { value: 'event_or_thought_leadership', label: 'Thought Leadership' },
  { value: 'hiring_signal', label: 'Hiring Signal' },
  { value: 'other', label: 'Other' },
];

export default function FilterBar({
  signalType,
  onSignalTypeChange,
  minRelevance,
  onMinRelevanceChange,
  companyId,
  onCompanyChange,
  companies,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      {companies && onCompanyChange && (
        <select
          value={companyId || ''}
          onChange={(e) => onCompanyChange(e.target.value)}
          className="input-field"
        >
          <option value="">All Companies</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      )}
      <select
        value={signalType}
        onChange={(e) => onSignalTypeChange(e.target.value as SignalType | '')}
        className="input-field"
      >
        <option value="">All Types</option>
        {signalTypes.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      <div className="flex items-center gap-2">
        <label className="text-sm text-dark-muted">Min Relevance:</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={minRelevance}
          onChange={(e) => onMinRelevanceChange(parseFloat(e.target.value))}
          className="w-24 accent-dark-accent"
        />
        <span className="text-sm text-dark-text w-8">
          {Math.round(minRelevance * 100)}%
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create MarkdownViewer component**

Create `frontend/src/components/MarkdownViewer.tsx`:

```tsx
import ReactMarkdown from 'react-markdown';

interface MarkdownViewerProps {
  content: string;
}

export default function MarkdownViewer({ content }: MarkdownViewerProps) {
  return (
    <div className="prose prose-invert prose-sm max-w-none">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 7: Create TagList component**

Create `frontend/src/components/TagList.tsx`:

```tsx
interface TagListProps {
  items: string[];
  label?: string;
}

export default function TagList({ items, label }: TagListProps) {
  if (!items || items.length === 0) {
    return (
      <div>
        {label && <span className="text-xs text-dark-muted">{label}:</span>}
        <span className="text-xs text-dark-muted italic">None</span>
      </div>
    );
  }

  return (
    <div>
      {label && <span className="text-xs text-dark-muted block mb-1">{label}:</span>}
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span
            key={i}
            className="text-xs px-2 py-0.5 rounded bg-dark-bg border border-dark-border text-dark-text"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Commit shared components**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/components/
git commit -m "feat: add shared UI components — Layout, SignalCard, FilterBar, RelevanceBadge, MarkdownViewer, TagList, SignalTypeIcon"
```

---

## Task 6: Login Page — Auth Gate

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Create Login page**

Create `frontend/src/pages/LoginPage.tsx`:

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setCredentials } from '../api/client';
import { useQueryClient } from '@tanstack/react-query';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');

    setCredentials(username, password);

    try {
      const res = await fetch('http://localhost:8000/api/health', {
        headers: {
          Authorization: `Basic ${btoa(`${username}:${password}`)}`,
        },
      });
      if (res.ok) {
        qc.invalidateQueries();
        navigate('/');
      } else {
        clearCredentials();
        setError('Invalid credentials');
      }
    } catch {
      setError('Cannot connect to server');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center">
      <div className="card w-96">
        <h1 className="text-xl font-bold mb-1">WFM Intel</h1>
        <p className="text-sm text-dark-muted mb-6">Market Intelligence Hub</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-dark-muted mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field w-full"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field w-full"
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-sm text-signal-low">{error}</p>}
          <button
            type="submit"
            disabled={loading || !username || !password}
            className="btn-primary w-full disabled:opacity-50"
          >
            {loading ? 'Connecting...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

Wait - we need `clearCredentials` imported. Let me fix that.

Actually, we already have `clearCredentials` in `client.ts`. The import needs to be added. Let me revise:

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setCredentials, clearCredentials } from '../api/client';
import { useQueryClient } from '@tanstack/react-query';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');

    setCredentials(username, password);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/health`, {
        headers: {
          Authorization: `Basic ${btoa(`${username}:${password}`)}`,
        },
      });
      if (res.ok) {
        qc.invalidateQueries();
        navigate('/');
      } else {
        clearCredentials();
        setError('Invalid credentials');
      }
    } catch {
      setError('Cannot connect to server');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center">
      <div className="card w-96">
        <h1 className="text-xl font-bold mb-1">WFM Intel</h1>
        <p className="text-sm text-dark-muted mb-6">Market Intelligence Hub</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-dark-muted mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field w-full"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field w-full"
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-sm text-signal-low">{error}</p>}
          <button
            type="submit"
            disabled={loading || !username || !password}
            className="btn-primary w-full disabled:opacity-50"
          >
            {loading ? 'Connecting...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit LoginPage**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/pages/LoginPage.tsx
git commit -m "feat: add login page with Basic Auth validation"
```

---

## Task 7: App Router + QueryClient Setup

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/AuthGate.tsx`

- [ ] **Step 1: Create AuthGate component**

Create `frontend/src/components/AuthGate.tsx`:

```tsx
import { hasCredentials } from '../api/client';
import { Navigate } from 'react-router-dom';

export default function AuthGate({ children }: { children: React.ReactNode }) {
  if (!hasCredentials()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
```

- [ ] **Step 2: Create stub page files so router imports resolve**

Create placeholder pages so the App router imports work. Each should be a minimal component:

`frontend/src/pages/Dashboard.tsx`:
```tsx
export default function Dashboard() {
  return <div className="p-4">Dashboard (coming soon)</div>;
}
```

`frontend/src/pages/CompetitorList.tsx`:
```tsx
export default function CompetitorList() {
  return <div className="p-4">Competitor List (coming soon)</div>;
}
```

`frontend/src/pages/CompetitorDetail.tsx`:
```tsx
export default function CompetitorDetail() {
  return <div className="p-4">Competitor Detail (coming soon)</div>;
}
```

`frontend/src/pages/MarketTrends.tsx`:
```tsx
export default function MarketTrends() {
  return <div className="p-4">Market Trends (coming soon)</div>;
}
```

`frontend/src/pages/WeeklyDigest.tsx`:
```tsx
export default function WeeklyDigest() {
  return <div className="p-4">Weekly Digest (coming soon)</div>;
}
```

`frontend/src/pages/SourcesAdmin.tsx`:
```tsx
export default function SourcesAdmin() {
  return <div className="p-4">Sources Admin (coming soon)</div>;
}
```

`frontend/src/pages/CompanyContext.tsx`:
```tsx
export default function CompanyContext() {
  return <div className="p-4">Company Context (coming soon)</div>;
}
```

- [ ] **Step 3: Update App.tsx with router and query provider**

Replace `frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import AuthGate from './components/AuthGate';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import CompetitorList from './pages/CompetitorList';
import CompetitorDetail from './pages/CompetitorDetail';
import MarketTrends from './pages/MarketTrends';
import WeeklyDigest from './pages/WeeklyDigest';
import SourcesAdmin from './pages/SourcesAdmin';
import CompanyContext from './pages/CompanyContext';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <AuthGate>
                <Layout />
              </AuthGate>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="competitors" element={<CompetitorList />} />
            <Route path="competitors/:slug" element={<CompetitorDetail />} />
            <Route path="trends" element={<MarketTrends />} />
            <Route path="digest" element={<WeeklyDigest />} />
            <Route path="admin/sources" element={<SourcesAdmin />} />
            <Route path="context" element={<CompanyContext />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 4: Verify router renders**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
npm run dev
```

Expected: App compiles, shows login page at `/login`. After login, shows Layout with sidebar. Page content shows stub text.

- [ ] **Step 5: Commit router setup**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/App.tsx src/components/AuthGate.tsx src/pages/*.tsx
git commit -m "feat: add router, QueryClient, auth gate, and stub pages"
```

---

## Task 8: Dashboard Page — KPI Cards + Latest Signals

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Create Dashboard page**

Create `frontend/src/pages/Dashboard.tsx`:

```tsx
import { useState } from 'react';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useCrawlAll } from '../hooks/useCrawl';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import type { SignalType } from '../types';
import { TrendingUp, AlertTriangle, FileText, Play } from 'lucide-react';

export default function Dashboard() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [companyId, setCompanyId] = useState('');
  const crawlAll = useCrawlAll();

  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id: companyId || undefined,
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
  });

  const competitorCount = companies?.filter((c) => c.type === 'competitor').length ?? 0;
  const highRelevanceCount = signals?.filter((s) => (s.relevance_score ?? 0) >= 0.7).length ?? 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <button
          onClick={() => crawlAll.mutate()}
          disabled={crawlAll.isPending}
          className="btn-primary flex items-center gap-2"
        >
          <Play size={16} />
          {crawlAll.isPending ? 'Crawling...' : 'Run Crawl'}
        </button>
      </div>

      {crawlAll.isSuccess && (
        <div className="mb-4 p-3 rounded bg-signal-high/10 text-signal-high text-sm">
          Crawl complete: {crawlAll.data.sources_processed} sources processed
        </div>
      )}
      {crawlAll.isError && (
        <div className="mb-4 p-3 rounded bg-signal-low/10 text-signal-low text-sm">
          Crawl failed
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="card flex items-center gap-4">
          <TrendingUp className="text-dark-accent" size={24} />
          <div>
            <p className="text-2xl font-bold">{signals?.length ?? '-'}</p>
            <p className="text-sm text-dark-muted">Total Signals</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <AlertTriangle className="text-signal-high" size={24} />
          <div>
            <p className="text-2xl font-bold">{highRelevanceCount}</p>
            <p className="text-sm text-dark-muted">High Relevance</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <FileText className="text-indigo-400" size={24} />
          <div>
            <p className="text-2xl font-bold">{competitorCount}</p>
            <p className="text-sm text-dark-muted">Competitors</p>
          </div>
        </div>
      </div>

      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
        companyId={companyId}
        onCompanyChange={setCompanyId}
        companies={companies}
      />

      {signalsLoading || companiesLoading ? (
        <p className="text-dark-muted">Loading signals...</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {signals?.map((signal) => {
            const company = companies?.find((c) => c.id === signal.company_id);
            return (
              <SignalCard
                key={signal.id}
                signal={signal}
                showCompany
                companyName={company?.name}
                companySlug={company?.slug}
              />
            );
          })}
          {signals?.length === 0 && (
            <p className="text-dark-muted col-span-2">No signals found. Try running a crawl.</p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit Dashboard**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/pages/Dashboard.tsx
git commit -m "feat: add Dashboard page with KPI cards, filters, and latest signals"
```

---

## Task 9: Competitor Pages — List + Detail

**Files:**
- Create: `frontend/src/pages/CompetitorList.tsx`
- Create: `frontend/src/pages/CompetitorDetail.tsx`

- [ ] **Step 1: Create CompetitorList page**

Create `frontend/src/pages/CompetitorList.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { Users, BarChart3 } from 'lucide-react';

export default function CompetitorList() {
  const { data: companies, isLoading } = useCompanies();
  const { data: allSignals } = useSignals();

  const competitors = companies?.filter((c) => c.type === 'competitor') ?? [];
  const marketSources = companies?.filter((c) => c.type === 'market_source') ?? [];

  function countSignals(companyId: string): number {
    return allSignals?.filter((s) => s.company_id === companyId).length ?? 0;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Competitors & Market Sources</h1>

      {isLoading ? (
        <p className="text-dark-muted">Loading...</p>
      ) : (
        <>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Users size={20} /> Competitors
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {competitors.map((c) => (
              <Link
                key={c.id}
                to={`/competitors/${c.slug}`}
                className="card hover:border-dark-accent/50 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{c.name}</h3>
                  <span className="text-sm text-dark-accent">{c.slug}</span>
                </div>
                {c.description && (
                  <p className="text-sm text-dark-muted line-clamp-2 mb-2">{c.description}</p>
                )}
                <div className="flex items-center gap-1 text-sm text-dark-muted">
                  <BarChart3 size={14} />
                  {countSignals(c.id)} signals
                </div>
              </Link>
            ))}
            {competitors.length === 0 && (
              <p className="text-dark-muted text-sm">No competitors configured yet.</p>
            )}
          </div>

          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <BarChart3 size={20} /> Market Sources
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {marketSources.map((c) => (
              <Link
                key={c.id}
                to={`/competitors/${c.slug}`}
                className="card hover:border-dark-accent/50 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{c.name}</h3>
                  <span className="text-sm text-dark-accent">{c.slug}</span>
                </div>
                {c.description && (
                  <p className="text-sm text-dark-muted line-clamp-2 mb-2">{c.description}</p>
                )}
                <div className="flex items-center gap-1 text-sm text-dark-muted">
                  <BarChart3 size={14} />
                  {countSignals(c.id)} signals
                </div>
              </Link>
            ))}
            {marketSources.length === 0 && (
              <p className="text-dark-muted text-sm">No market sources configured yet.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create CompetitorDetail page**

Create `frontend/src/pages/CompetitorDetail.tsx`:

```tsx
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useCompany } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useDocuments } from '../hooks/useDocuments';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import MarkdownViewer from '../components/MarkdownViewer';
import type { SignalType } from '../types';
import { ArrowLeft, FileText } from 'lucide-react';

export default function CompetitorDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: company, isLoading: companyLoading } = useCompany(slug!);
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);

  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id: company?.id,
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
  });

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const { data: selectedDoc } = useDocuments(selectedDocId ? undefined : undefined);

  if (companyLoading) return <p className="text-dark-muted">Loading...</p>;
  if (!company) return <p className="text-signal-low">Company not found.</p>;

  return (
    <div>
      <Link to="/competitors" className="text-sm text-dark-accent hover:underline flex items-center gap-1 mb-4">
        <ArrowLeft size={14} /> Back to list
      </Link>

      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">{company.name}</h1>
          <p className="text-sm text-dark-muted">
            {company.type === 'competitor' ? 'Competitor' : 'Market Source'}
            {company.website && ` · ${company.website}`}
          </p>
        </div>
        {company.description && (
          <p className="text-sm text-dark-muted max-w-md">{company.description}</p>
        )}
      </div>

      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
      />

      {signalsLoading ? (
        <p className="text-dark-muted">Loading signals...</p>
      ) : (
        <div className="space-y-4">
          {signals?.map((signal) => (
            <div key={signal.id}>
              <SignalCard signal={signal} />
              {signal.document_id && (
                <button
                  onClick={() => setSelectedDocId(signal.document_id)}
                  className="text-xs text-dark-accent hover:underline flex items-center gap-1 mt-1"
                >
                  <FileText size={12} /> View source document
                </button>
              )}
            </div>
          ))}
          {signals?.length === 0 && (
            <p className="text-dark-muted">No signals found for this company.</p>
          )}
        </div>
      )}

      {selectedDocId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50">
          <div className="card max-w-3xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Source Document</h3>
              <button onClick={() => setSelectedDocId(null)} className="text-dark-muted hover:text-dark-text">
                Close
              </button>
            </div>
            <DocumentViewer documentId={selectedDocId} onClose={() => setSelectedDocId(null)} />
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentViewer({ documentId, onClose }: { documentId: string; onClose: () => void }) {
  const { data: doc, isLoading } = useDocument(documentId);
  if (isLoading) return <p className="text-dark-muted">Loading document...</p>;
  if (!doc) return <p className="text-signal-low">Document not found.</p>;

  return (
    <div>
      <h4 className="font-medium mb-2">{doc.title || 'Untitled'}</h4>
      <p className="text-xs text-dark-muted mb-4">
        Crawled: {new Date(doc.crawled_at).toLocaleDateString('de-DE')} ·{' '}
        <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-dark-accent hover:underline">
          Original URL
        </a>
      </p>
      {doc.content_markdown ? (
        <MarkdownViewer content={doc.content_markdown} />
      ) : (
        <p className="text-dark-muted">No markdown content available.</p>
      )}
    </div>
  );
}
```

Wait - I reference `useDocument` but that's a hook that takes an id string. But I import it from `useDocuments`. Let me fix - I need to also import `useDocument` from the hooks. Actually looking at my hook definitions, `useDocument` is defined in `useDocuments.ts`. Let me fix the import:

The `CompetitorDetail` page should import both `useDocuments` and `useDocument` from `useDocuments.ts`. Looking at the code, `useDocument(id)` fetches a single document by id. Let me adjust the imports:

```tsx
import { useDocuments, useDocument } from '../hooks/useDocuments';
```

Actually wait, I need to also add a `useDocument` export. Looking at my hook file for useDocuments, I already defined `useDocument(id)`. Good. Let me just fix the import statement.

Also, I realize the `selectedDoc` variable was unused. Let me clean that up in the final code.

- [ ] **Step 3: Adjust CompetitorDetail to use correct imports**

The corrected `CompetitorDetail.tsx` should properly import `useDocument` from `useDocuments`. Also remove the unused `useDocuments` import for the general list case. Let me finalize:

```tsx
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useCompany } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useDocument } from '../hooks/useDocuments';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import MarkdownViewer from '../components/MarkdownViewer';
import type { SignalType } from '../types';
import { ArrowLeft, FileText } from 'lucide-react';

export default function CompetitorDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: company, isLoading: companyLoading } = useCompany(slug!);
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);

  const { data: signals, isLoading: signalsLoading } = useSignals(
    company
      ? {
          company_id: company.id,
          signal_type: signalType || undefined,
          min_relevance: minRelevance || undefined,
        }
      : undefined,
  );

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  if (companyLoading) return <p className="text-dark-muted">Loading...</p>;
  if (!company) return <p className="text-signal-low">Company not found.</p>;

  return (
    <div>
      <Link to="/competitors" className="text-sm text-dark-accent hover:underline flex items-center gap-1 mb-4">
        <ArrowLeft size={14} /> Back to list
      </Link>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">{company.name}</h1>
          <p className="text-sm text-dark-muted">
            {company.type === 'competitor' ? 'Competitor' : 'Market Source'}
            {company.website && ` · ${company.website}`}
          </p>
        </div>
        {company.description && (
          <p className="text-sm text-dark-muted max-w-md">{company.description}</p>
        )}
      </div>
      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
      />
      {signalsLoading ? (
        <p className="text-dark-muted">Loading signals...</p>
      ) : (
        <div className="space-y-4">
          {signals?.map((signal) => (
            <div key={signal.id}>
              <SignalCard signal={signal} />
              {signal.document_id && (
                <button
                  onClick={() => setSelectedDocId(signal.document_id)}
                  className="text-xs text-dark-accent hover:underline flex items-center gap-1 mt-1"
                >
                  <FileText size={12} /> View source document
                </button>
              )}
            </div>
          ))}
          {signals?.length === 0 && (
            <p className="text-dark-muted">No signals found for this company.</p>
          )}
        </div>
      )}
      {selectedDocId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={() => setSelectedDocId(null)}>
          <div className="card max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Source Document</h3>
              <button onClick={() => setSelectedDocId(null)} className="text-dark-muted hover:text-dark-text">Close</button>
            </div>
            <DocumentViewer documentId={selectedDocId} />
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentViewer({ documentId }: { documentId: string }) {
  const { data: doc, isLoading } = useDocument(documentId);
  if (isLoading) return <p className="text-dark-muted">Loading document...</p>;
  if (!doc) return <p className="text-signal-low">Document not found.</p>;

  return (
    <div>
      <h4 className="font-medium mb-2">{doc.title || 'Untitled'}</h4>
      <p className="text-xs text-dark-muted mb-4">
        Crawled: {new Date(doc.crawled_at).toLocaleDateString('de-DE')} ·{' '}
        <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-dark-accent hover:underline">Original URL</a>
      </p>
      {doc.content_markdown ? (
        <MarkdownViewer content={doc.content_markdown} />
      ) : (
        <p className="text-dark-muted">No markdown content available.</p>
      )}
    </div>
  );
}
```

But wait - there's an issue. The `useSignals` hook uses `SignalsFilters` which expects `company_id?: string`, but the backend signals router uses `company_id` as a query parameter that takes a UUID. The frontend sends the company ID directly. But in the spec, it says `GET /api/signals?company=:slug`. The backend actually uses `company_id` as the query param taking a UUID. Let me check... yes, in the backend router:

```python
def list_signals(
    company_id: Optional[str] = None,
    ...
```

It filters by `Signal.company_id == company_id`. So we need to pass the UUID of the company, not the slug. The slug is only used for the `/api/companies/:slug` endpoint. This is how I've set it up in the hook - I'm passing `company.id` (UUID) to `useSignals`. That's correct.

- [ ] **Step 4: Commit competitor pages**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/pages/CompetitorList.tsx src/pages/CompetitorDetail.tsx
git commit -m "feat: add CompetitorList and CompetitorDetail pages with signal filters and document drilldown"
```

---

## Task 10: Market Trends Page

**Files:**
- Create: `frontend/src/pages/MarketTrends.tsx`

- [ ] **Step 1: Create MarketTrends page**

Create `frontend/src/pages/MarketTrends.tsx`:

```tsx
import { useState } from 'react';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import type { SignalType } from '../types';
import { TrendingUp } from 'lucide-react';

export default function MarketTrends() {
  const { data: companies } = useCompanies();
  const marketSources = companies?.filter((c) => c.type === 'market_source') ?? [];
  const marketCompanyIds = marketSources.map((c) => c.id);

  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [selectedCompanyId, setSelectedCompanyId] = useState('');

  const { data: allSignals, isLoading } = useSignals({
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
  });

  const marketSignals = allSignals?.filter((s) => {
    const isMarket = selectedCompanyId ? s.company_id === selectedCompanyId : marketCompanyIds.includes(s.company_id);
    return isMarket;
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
        <TrendingUp size={24} /> Market Trends
      </h1>
      <p className="text-sm text-dark-muted mb-4">
        Signals from market and industry sources
      </p>

      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
        companyId={selectedCompanyId}
        onCompanyChange={setSelectedCompanyId}
        companies={marketSources}
      />

      {isLoading ? (
        <p className="text-dark-muted">Loading signals...</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {(marketSignals ?? []).map((signal) => {
            const company = marketSources.find((c) => c.id === signal.company_id);
            return (
              <SignalCard
                key={signal.id}
                signal={signal}
                showCompany
                companyName={company?.name}
                companySlug={company?.slug}
              />
            );
          })}
          {marketSignals?.length === 0 && (
            <p className="text-dark-muted col-span-2">
              No market trend signals found. Add market sources and run a crawl.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit MarketTrends**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/pages/MarketTrends.tsx
git commit -m "feat: add Market Trends page with market source signal filtering"
```

---

## Task 11: Weekly Digest Page

**Files:**
- Create: `frontend/src/pages/WeeklyDigest.tsx`

- [ ] **Step 1: Create WeeklyDigest page**

Create `frontend/src/pages/WeeklyDigest.tsx`:

```tsx
import { useDigests, useGenerateDigest } from '../hooks/useDigests';
import { useSignals } from '../hooks/useSignals';
import RelevanceBadge from '../components/RelevanceBadge';
import SignalTypeIcon from '../components/SignalTypeIcon';
import { Calendar, RefreshCw } from 'lucide-react';
import type { Signal } from '../types';

export default function WeeklyDigest() {
  const { data: digests, isLoading } = useDigests();
  const generateDigest = useGenerateDigest();
  const { data: allSignals } = useSignals();

  function getSignalById(id: string): Signal | undefined {
    return allSignals?.find((s) => s.id === id);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Calendar size={24} /> Weekly Digest
        </h1>
        <button
          onClick={() => generateDigest.mutate()}
          disabled={generateDigest.isPending}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw size={16} className={generateDigest.isPending ? 'animate-spin' : ''} />
          {generateDigest.isPending ? 'Generating...' : 'Generate New Digest'}
        </button>
      </div>

      {generateDigest.isError && (
        <div className="mb-4 p-3 rounded bg-signal-low/10 text-signal-low text-sm">
          Failed to generate digest. Try again.
        </div>
      )}

      {isLoading ? (
        <p className="text-dark-muted">Loading digests...</p>
      ) : digests?.length === 0 ? (
        <div className="card text-center py-8">
          <Calendar size={48} className="mx-auto text-dark-muted mb-3" />
          <p className="text-dark-muted">No digests yet. Generate one to get started.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {digests?.map((digest) => (
            <div key={digest.id} className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">
                  {digest.week_start} — {digest.week_end}
                </h2>
                <span className={`text-xs px-2 py-0.5 rounded ${digest.is_published ? 'bg-signal-high/20 text-signal-high' : 'bg-dark-bg text-dark-muted'}`}>
                  {digest.is_published ? 'Published' : 'Draft'}
                </span>
              </div>
              {digest.summary && (
                <div className="text-sm text-dark-text whitespace-pre-line mb-4">
                  {digest.summary}
                </div>
              )}
              {digest.key_signals.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-dark-muted mb-2">Key Signals:</h3>
                  <div className="space-y-2">
                    {digest.key_signals.map((sid) => {
                      const signal = getSignalById(sid);
                      if (!signal) return null;
                      return (
                        <div key={sid} className="flex items-center justify-between bg-dark-bg rounded p-2">
                          <div className="flex items-center gap-2">
                            <SignalTypeIcon type={signal.signal_type} size={14} />
                            <span className="text-sm">{signal.title}</span>
                          </div>
                          <RelevanceBadge score={signal.relevance_score} size="sm" />
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit WeeklyDigest**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/pages/WeeklyDigest.tsx
git commit -m "feat: add Weekly Digest page with generation and signal listing"
```

---

## Task 12: Sources Admin Page — CRUD + Crawl Trigger

**Files:**
- Create: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Create SourcesAdmin page**

Create `frontend/src/pages/SourcesAdmin.tsx`:

```tsx
import { useState } from 'react';
import { useCompanies, useCreateCompany, useUpdateCompany } from '../hooks/useCompanies';
import { useSources, useCreateSource, useUpdateSource, useDeleteSource } from '../hooks/useSources';
import { useCrawlAll, useCrawlSource } from '../hooks/useCrawl';
import type { CompanyType, SourceType } from '../types';
import { Plus, Play, Trash2, Edit2 } from 'lucide-react';

const sourceTypes: SourceType[] = ['news', 'blog', 'product', 'press', 'jobs'];

export default function SourcesAdmin() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const { data: sources, isLoading: sourcesLoading } = useSources();
  const createCompany = useCreateCompany();
  const updateCompany = useUpdateCompany();
  const createSource = useCreateSource();
  const updateSource = useUpdateSource();
  const deleteSource = useDeleteSource();
  const crawlAll = useCrawlAll();
  const crawlSingle = useCrawlSource();

  const [newCompanyOpen, setNewCompanyOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanySlug, setNewCompanySlug] = useState('');
  const [newCompanyType, setNewCompanyType] = useState<CompanyType>('competitor');
  const [newCompanyWebsite, setNewCompanyWebsite] = useState('');

  const [newSourceCompanyId, setNewSourceCompanyId] = useState('');
  const [newSourceUrl, setNewSourceUrl] = useState('');
  const [newSourceLabel, setNewSourceLabel] = useState('');
  const [newSourceType, setNewSourceType] = useState<SourceType>('news');

  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);

  function handleCreateCompany(e: React.FormEvent) {
    e.preventDefault();
    if (!newCompanyName || !newCompanySlug) return;
    createCompany.mutate(
      { name: newCompanyName, slug: newCompanySlug, type: newCompanyType, website: newCompanyWebsite || null },
      { onSuccess: () => {
        setNewCompanyOpen(false);
        setNewCompanyName('');
        setNewCompanySlug('');
        setNewCompanyWebsite('');
      }},
    );
  }

  function handleCreateSource(e: React.FormEvent) {
    e.preventDefault();
    if (!newSourceCompanyId || !newSourceUrl) return;
    createSource.mutate(
      { company_id: newSourceCompanyId, url: newSourceUrl, label: newSourceLabel || null, source_type: newSourceType },
      { onSuccess: () => {
        setNewSourceUrl('');
        setNewSourceLabel('');
        setNewSourceType('news');
      }},
    );
  }

  function handleToggleSource(sourceId: string, currentActive: boolean) {
    updateSource.mutate({ sourceId, data: { is_active: !currentActive } });
  }(sourceId: string) {
    if (window.confirm('Delete this source?')) {
      deleteSource.mutate(sourceId);
    }
  }

  function handleCrawlSource(sourceId: string) {
    crawlSingle.mutate(sourceId);
  }

  const isLoading = companiesLoading || sourcesLoading;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Sources Admin</h1>
        <div className="flex gap-2">
          <button onClick={() => crawlAll.mutate()} disabled={crawlAll.isPending} className="btn-primary flex items-center gap-2">
            <Play size={16} /> {crawlAll.isPending ? 'Crawling...' : 'Run Full Crawl'}
          </button>
          <button onClick={() => setNewCompanyOpen(true)} className="btn-secondary flex items-center gap-2">
            <Plus size={16} /> Add Company
          </button>
        </div>
      </div>

      {crawlAll.isSuccess && (
        <div className="mb-4 p-3 rounded bg-signal-high/10 text-signal-high text-sm">
          Crawl complete: {crawlAll.data.sources_processed} sources processed
        </div>
      )}

      {isLoading ? (
        <p className="text-dark-muted">Loading...</p>
      ) : (
        <div className="space-y-6">
          {companies?.map((company) => {
            const companySources = sources?.filter((s) => s.company_id === company.id) ?? [];
            return (
              <div key={company.id} className="card">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold">{company.name}</h2>
                  <span className={`text-xs px-2 py-0.5 rounded ${company.type === 'competitor' ? 'bg-type-product_update/20 text-type-product_update' : 'bg-type-ai_announcement/20 text-type-ai_announcement'}`}>
                    {company.type === 'competitor' ? 'Competitor' : 'Market Source'}
                  </span>
                </div>
                {company.website && <p className="text-xs text-dark-muted mb-3">{company.website}</p>}
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-border">
                      <th className="text-left py-2 text-dark-muted font-medium">URL</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Label</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Type</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Active</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Last Crawled</th>
                      <th className="text-right py-2 text-dark-muted font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {companySources.map((source) => (
                      <tr key={source.id} className="border-b border-dark-border/50">
                        <td className="py-2 max-w-xs truncate" title={source.url}>{source.url}</td>
                        <td className="py-2">{source.label || '-'}</td>
                        <td className="py-2">
                          <span className="text-xs px-1.5 py-0.5 rounded bg-dark-bg">{source.source_type}</span>
                        </td>
                        <td className="py-2">
                          <button
                            onClick={() => handleToggleSource(source.id, source.is_active)}
                            className={`text-xs px-2 py-0.5 rounded ${source.is_active ? 'bg-signal-high/20 text-signal-high' : 'bg-dark-bg text-dark-muted'}`}
                          >
                            {source.is_active ? 'Active' : 'Inactive'}
                          </button>
                        </td>
                        <td className="py-2 text-dark-muted text-xs">
                          {source.last_crawled_at ? new Date(source.last_crawled_at).toLocaleDateString('de-DE') : 'Never'}
                        </td>
                        <td className="py-2 text-right">
                          <button onClick={() => handleCrawlSource(source.id)} className="text-dark-accent hover:text-indigo-300 mr-2" title="Crawl this source">
                            <Play size={14} />
                          </button>
                          <button onClick={() => handleDeleteSource(source.id)} className="text-signal-low hover:text-red-400" title="Delete source">
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                    {companySources.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-2 text-dark-muted text-center">No sources configured</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}

      {newCompanyOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={() => setNewCompanyOpen(false)}>
          <div className="card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Add Company</h2>
            <form onSubmit={handleCreateCompany} className="space-y-3">
              <div>
                <label className="block text-sm text-dark-muted mb-1">Name</label>
                <input value={newCompanyName} onChange={(e) => setNewCompanyName(e.target.value)} className="input-field w-full" required />
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Slug</label>
                <input value={newCompanySlug} onChange={(e) => setNewCompanySlug(e.target.value)} className="input-field w-full" required placeholder="e.g. company-name" />
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Type</label>
                <select value={newCompanyType} onChange={(e) => setNewCompanyType(e.target.value as CompanyType)} className="input-field w-full">
                  <option value="competitor">Competitor</option>
                  <option value="market_source">Market Source</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Website (optional)</label>
                <input value={newCompanyWebsite} onChange={(e) => setNewCompanyWebsite(e.target.value)} className="input-field w-full" />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={createCompany.isPending} className="btn-primary flex-1">
                  {createCompany.isPending ? 'Creating...' : 'Create'}
                </button>
                <button type="button" onClick={() => setNewCompanyOpen(false)} className="btn-secondary flex-1">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card mt-6">
        <h2 className="text-lg font-semibold mb-4">Add Source</h2>
        <form onSubmit={handleCreateSource} className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-sm text-dark-muted mb-1">Company</label>
            <select value={newSourceCompanyId} onChange={(e) => setNewSourceCompanyId(e.target.value)} className="input-field w-full" required>
              <option value="">Select...</option>
              {companies?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-[2]">
            <label className="block text-sm text-dark-muted mb-1">URL</label>
            <input value={newSourceUrl} onChange={(e) => setNewSourceUrl(e.target.value)} className="input-field w-full" required placeholder="https://..." />
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Label</label>
            <input value={newSourceLabel} onChange={(e) => setNewSourceLabel(e.target.value)} className="input-field w-full" placeholder="News" />
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Type</label>
            <select value={newSourceType} onChange={(e) => setNewSourceType(e.target.value as SourceType)} className="input-field w-full">
              {sourceTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <button type="submit" disabled={createSource.isPending} className="btn-primary">
            {createSource.isPending ? 'Adding...' : 'Add Source'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit SourcesAdmin**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/pages/SourcesAdmin.tsx
git commit -m "feat: add Sources Admin page with company/source CRUD and crawl trigger"
```

---

## Task 13: Company Context Page

**Files:**
- Create: `frontend/src/pages/CompanyContext.tsx`

- [ ] **Step 1: Create CompanyContext page**

Create `frontend/src/pages/CompanyContext.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useContextData, useUpdateContext } from '../hooks/useContext';
import TagList from '../components/TagList';
import type { ContextUpdate } from '../types';
import { Save, Globe } from 'lucide-react';

const listFields: { key: keyof ContextUpdate; label: string; placeholder: string }[] = [
  { key: 'target_industries', label: 'Target Industries', placeholder: 'Add industry...' },
  { key: 'target_segments', label: 'Target Segments', placeholder: 'Add segment...' },
  { key: 'core_capabilities', label: 'Core Capabilities', placeholder: 'Add capability...' },
  { key: 'strategic_priorities', label: 'Strategic Priorities', placeholder: 'Add priority...' },
  { key: 'differentiators', label: 'Differentiators', placeholder: 'Add differentiator...' },
  { key: 'relevant_competitive_areas', label: 'Relevant Competitive Areas', placeholder: 'Add area...' },
  { key: 'non_focus_areas', label: 'Non-Focus Areas', placeholder: 'Add area...' },
];

export default function CompanyContext() {
  const { data: context, isLoading } = useContextData();
  const updateContext = useUpdateContext();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<ContextUpdate>({});
  const [inputValues, setInputValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (context && !editing) {
      setForm({
        company_name: context.company_name ?? '',
        short_description: context.short_description ?? '',
        target_industries: context.target_industries,
        target_segments: context.target_segments,
        core_capabilities: context.core_capabilities,
        strategic_priorities: context.strategic_priorities,
        differentiators: context.differentiators,
        relevant_competitive_areas: context.relevant_competitive_areas,
        non_focus_areas: context.non_focus_areas,
      });
    }
  }, [context, editing]);

  if (isLoading) return <p className="text-dark-muted">Loading context...</p>;
  if (!context) return <p className="text-signal-low">Failed to load context.</p>;

  function handleSave() {
    const payload: ContextUpdate = {};
    if (form.company_name !== context.company_name) payload.company_name = form.company_name;
    if (form.short_description !== context.short_description) payload.short_description = form.short_description;
    for (const field of listFields) {
      const key = field.key;
      if (JSON.stringify(form[key]) !== JSON.stringify(context[key as keyof typeof context])) {
        (payload as Record<string, string[]>)[key as string] = form[key] as string[];
      }
    }
    updateContext.mutate(payload, { onSuccess: () => setEditing(false) });
  }

  function handleAddItem(key: string) {
    const val = inputValues[key]?.trim();
    if (!val) return;
    const currentList = (form[key as keyof ContextUpdate] as string[]) ?? [];
    setForm({ ...form, [key]: [...currentList, val] });
    setInputValues({ ...inputValues, [key]: '' });
  }

  function handleRemoveItem(key: string, index: number) {
    const currentList = (form[key as keyof ContextUpdate] as string[]) ?? [];
    setForm({ ...form, [key]: currentList.filter((_, i) => i !== index) });
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Globe size={24} /> Company Context
        </h1>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button onClick={handleSave} disabled={updateContext.isPending} className="btn-primary flex items-center gap-2">
                <Save size={16} /> {updateContext.isPending ? 'Saving...' : 'Save'}
              </button>
              <button onClick={() => setEditing(false)} className="btn-secondary">Cancel</button>
            </>
          ) : (
            <button onClick={() => setEditing(true)} className="btn-primary">Edit</button>
          )}
        </div>
      </div>

      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-dark-muted mb-1">Company Name</label>
            {editing ? (
              <input
                value={form.company_name ?? ''}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                className="input-field w-full"
              />
            ) : (
              <p className="text-dark-text">{context.company_name || '—'}</p>
            )}
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Short Description</label>
            {editing ? (
              <textarea
                value={form.short_description ?? ''}
                onChange={(e) => setForm({ ...form, short_description: e.target.value })}
                className="input-field w-full h-20"
              />
            ) : (
              <p className="text-dark-text">{context.short_description || '—'}</p>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {listFields.map(({ key, label, placeholder }) => {
          const items = (form[key] as string[]) ?? [];
          return (
            <div key={key} className="card">
              <h3 className="text-sm font-semibold mb-2">{label}</h3>
              {editing ? (
                <div>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {items.map((item, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded bg-dark-bg border border-dark-border text-dark-text flex items-center gap-1">
                        {item}
                        <button onClick={() => handleRemoveItem(key, i)} className="text-signal-low hover:text-red-400">×</button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={inputValues[key] ?? ''}
                      onChange={(e) => setInputValues({ ...inputValues, [key]: e.target.value })}
                      className="input-field flex-1"
                      placeholder={placeholder}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddItem(key); } }}
                    />
                    <button onClick={() => handleAddItem(key)} className="btn-secondary text-sm">Add</button>
                  </div>
                </div>
              ) : (
                <TagList items={items} />
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-dark-muted mt-4">
        Last updated: {new Date(context.updated_at).toLocaleString('de-DE')}
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit CompanyContext**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/pages/CompanyContext.tsx
git commit -m "feat: add Company Context page with editable list fields"
```

---

## Task 14: Frontend Dockerfile + Docker Compose Integration

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Modify: `docker-compose.dev.yml` (add frontend service)
- Modify: `docker-compose.yml` (update frontend build context)

- [ ] **Step 1: Create Vite proxy config for dev**

Update `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 2: Create nginx.conf for production**

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 3: Create Dockerfile for frontend**

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 4: Update docker-compose.dev.yml to include frontend**

Replace `docker-compose.dev.yml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: wfm
      POSTGRES_PASSWORD: wfm
      POSTGRES_DB: wfmintel
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    ports:
      - "5435:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wfm"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

volumes:
  postgres_data_dev:
```

- [ ] **Step 5: Create Dockerfile.dev for frontend dev mode**

Create `frontend/Dockerfile.dev`:

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

- [ ] **Step 6: Verify the docker-compose.dev.yml is valid**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence
docker compose -f docker-compose.dev.yml config
```

Expected: Valid config output with all three services (db, backend, frontend).

- [ ] **Step 7: Commit Docker setup**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence
git add frontend/Dockerfile frontend/Dockerfile.dev frontend/nginx.conf frontend/vite.config.ts docker-compose.dev.yml
git commit -m "feat: add frontend Docker setup with Vite proxy and nginx config"
```

---

## Task 15: Vite Proxy for API + CORS Verification

**Files:**
- Modify: `frontend/src/api/client.ts` (update API_BASE to use relative path in dev)

- [ ] **Step 1: Update API client to use relative path with Vite proxy**

In `frontend/src/api/client.ts`, update the `API_BASE` constant:

```typescript
const API_BASE = '/api';
```

This works because the Vite dev proxy handles `/api` → `http://localhost:8000/api`, and in production nginx handles `/api/` → backend:8000.

- [ ] **Step 2: Verify CORS and proxy are compatible**

The backend CORS already allows `http://localhost:5173`. With the Vite proxy, requests come from the frontend dev server, so CORS is satisfied. In production, nginx proxies API calls, so CORS isn't needed (same origin).

- [ ] **Step 3: Commit API client update**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add src/api/client.ts
git commit -m "fix: use relative /api path for Vite proxy and nginx compatibility"
```

---

## Task 16: Final Integration Test — Full Stack Smoke Test

**Files:** None (testing only)

- [ ] **Step 1: Start the dev stack**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence
docker compose -f docker-compose.dev.yml up -d
```

- [ ] **Step 2: Run backend migrations**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

- [ ] **Step 3: Verify frontend loads at http://localhost:5173**

Open browser, verify:
- Login page renders
- Can enter credentials and log in
- Dashboard loads (empty, but no errors)

- [ ] **Step 4: Verify API proxy works**

```bash
curl -u admin:changeme http://localhost:5173/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Build frontend for production**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
npm run build
```

Expected: Build succeeds, `dist/` folder created.

- [ ] **Step 6: Commit any final fixes**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend
git add -A
git commit -m "chore: final integration fixes"
```

---

## Task 17: Update docker-compose.yml (Production) for Frontend

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Update production docker-compose.yml**

Replace `docker-compose.yml` with proper frontend build:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: wfm
      POSTGRES_PASSWORD: wfm
      POSTGRES_DB: wfmintel
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wfm"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

- [ ] **Step 2: Verify production config is valid**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence
docker compose config
```

- [ ] **Step 3: Commit production compose update**

```bash
git add docker-compose.yml
git commit -m "feat: update production docker-compose with frontend service"
```