# Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the WFM Intel frontend from a generic dark theme to a modern SaaS design with a deep navy sidebar, light main panel, Geist font, and blue-violet accent system.

**Architecture:** Pure styling pass — no logic, routing, or API changes. New Tailwind color tokens replace the old `dark-*` tokens; CSS component classes are updated in `index.css`; each component gets restyled Tailwind classnames while keeping its JSX structure and props intact.

**Tech Stack:** React 18, TypeScript, Tailwind CSS v3, Lucide icons, Geist font (Google Fonts CDN)

---

## Files

| File | Change |
|------|--------|
| `frontend/index.html` | Add Geist font `<link>` |
| `frontend/tailwind.config.js` | Replace `dark-*` tokens with new design tokens |
| `frontend/src/index.css` | New CSS variables, updated `.card`, `.btn-primary`, `.btn-secondary`, `.input-field` |
| `frontend/src/components/Layout.tsx` | Navy sidebar, grouped nav sections, user footer |
| `frontend/src/components/RelevanceBadge.tsx` | New color tokens + bar variant |
| `frontend/src/components/SignalTypeIcon.tsx` | Replace `text-type-${type}` dynamic class with lookup object; add chip variant |
| `frontend/src/components/SignalCard.tsx` | New card style using updated tokens + chip components |
| `frontend/src/components/FilterBar.tsx` | Pill-style filter buttons replacing select + slider |
| `frontend/src/pages/Dashboard.tsx` | 4-column KPI grid + signal table layout |

> **Note:** There are no unit tests for styling changes. Each task includes a **visual verification** step — start the dev server and confirm the change looks correct in the browser before committing.

---

## Task 1: Font & design tokens

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/src/index.css`

- [ ] **Step 1.1: Add Geist font to index.html**

Replace the `<title>` line area — add font preconnect and stylesheet before `</head>`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>WFM Intel</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700;800&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 1.2: Replace Tailwind color tokens**

Replace the entire contents of `frontend/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Geist Mono', 'monospace'],
      },
      colors: {
        sidebar: {
          bg:           '#0f172a',
          text:         'rgba(248,250,252,0.45)',
          'text-active':'#93c5fd',
          'active-bg':  'rgba(37,99,235,0.18)',
          border:       'rgba(255,255,255,0.06)',
          label:        'rgba(248,250,252,0.20)',
        },
        app: {
          bg:           '#f8f8fa',
          card:         '#ffffff',
          border:       '#ececf0',
          'border-sub': '#f4f4f6',
        },
        ink: {
          DEFAULT: '#09090b',
          secondary: '#71717a',
          muted:    '#a1a1aa',
        },
        accent: {
          blue:   '#2563eb',
          purple: '#7c3aed',
        },
        signal: {
          high:   '#10b981',
          medium: '#f59e0b',
          low:    '#ef4444',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
```

- [ ] **Step 1.3: Update index.css base styles and component classes**

Replace the entire contents of `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-family: 'Geist', system-ui, -apple-system, sans-serif;
    @apply bg-app-bg text-ink;
    -webkit-font-smoothing: antialiased;
  }
}

@layer components {
  .card {
    @apply bg-app-card border border-app-border rounded-xl p-4;
  }
  .btn-primary {
    @apply bg-accent-blue hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-sm;
  }
  .btn-secondary {
    @apply bg-transparent hover:bg-app-bg text-ink-secondary border border-app-border px-4 py-2 rounded-lg text-sm font-medium transition-colors;
  }
  .input-field {
    @apply bg-app-card border border-app-border rounded-lg px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent-blue/30 focus:border-accent-blue transition-colors;
  }
}
```

- [ ] **Step 1.4: Visual verification**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. The app should now use Geist font. The overall layout will look broken (old dark classes no longer map to anything visible) — that's expected and will be fixed in subsequent tasks.

- [ ] **Step 1.5: Commit**

```bash
rtk git add frontend/index.html frontend/tailwind.config.js frontend/src/index.css
rtk git commit -m "feat: update design tokens and Geist font for redesign"
```

---

## Task 2: Sidebar — Layout.tsx

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 2.1: Rewrite Layout.tsx**

Replace the entire file:

```tsx
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  TrendingUp,
  FileText,
  History,
  Settings,
  Search,
  Globe,
  LogOut,
} from 'lucide-react';
import { hasCredentials, clearCredentials } from '../api/client';
import { useNavigate } from 'react-router-dom';

const navSections = [
  {
    label: 'Übersicht',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/competitors', label: 'Wettbewerber', icon: Users },
      { to: '/trends', label: 'Markt-Trends', icon: TrendingUp },
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
      { to: '/admin/sources', label: 'Quellen', icon: Settings },
      { to: '/context', label: 'Kontext', icon: Globe },
    ],
  },
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
    <div className="flex h-screen bg-app-bg">
      {/* ── Sidebar ── */}
      <nav
        className="w-56 flex flex-col flex-shrink-0"
        style={{ background: '#0f172a' }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-2.5 px-4 py-[18px]"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div
            className="w-7 h-7 rounded-[7px] flex items-center justify-center text-[11px] font-extrabold text-white flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #2563eb, #7c3aed)' }}
          >
            W
          </div>
          <div>
            <div className="text-[13px] font-semibold leading-none text-slate-50">WFM Intel</div>
            <div className="text-[9px] mt-0.5" style={{ color: 'rgba(248,250,252,0.3)' }}>
              Market Intelligence
            </div>
          </div>
        </div>

        {/* Nav sections */}
        <div className="flex-1 overflow-y-auto">
          {navSections.map((section) => (
            <div key={section.label} className="pt-3.5 pb-1 px-2">
              <p
                className="text-[9px] font-semibold uppercase px-2 mb-1 tracking-widest"
                style={{ color: 'rgba(248,250,252,0.20)' }}
              >
                {section.label}
              </p>
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-2 py-[7px] rounded-[7px] text-[13px] font-medium mb-px transition-colors ${
                      isActive
                        ? 'text-[#93c5fd]'
                        : 'hover:bg-white/5 hover:text-slate-200'
                    }`
                  }
                  style={({ isActive }) => ({
                    background: isActive ? 'rgba(37,99,235,0.18)' : undefined,
                    color: isActive ? '#93c5fd' : 'rgba(248,250,252,0.45)',
                  })}
                >
                  <Icon size={15} className="flex-shrink-0" />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>

        {/* User footer */}
        <div
          className="px-2 py-3"
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
        >
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-2 py-[7px] rounded-[7px] text-[12px] font-medium transition-colors hover:bg-white/5"
            style={{ color: 'rgba(248,250,252,0.35)' }}
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>
      </nav>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2.2: Visual verification**

Reload http://localhost:5173. The sidebar should show deep navy background, gradient logo mark, grouped navigation sections with muted section labels, and active item highlighted in blue.

- [ ] **Step 2.3: Commit**

```bash
rtk git add frontend/src/components/Layout.tsx
rtk git commit -m "feat: redesign sidebar with deep navy theme and grouped nav"
```

---

## Task 3: Signal type chip component

**Files:**
- Modify: `frontend/src/components/SignalTypeIcon.tsx`

The current component uses `text-type-${type}` which generates dynamic Tailwind classes that won't be picked up by the JIT scanner. Replace with an explicit lookup object and add a chip variant.

- [ ] **Step 3.1: Rewrite SignalTypeIcon.tsx**

Replace the entire file:

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
  product_update:              Package,
  ai_announcement:             Brain,
  partnership:                 Handshake,
  positioning_change:          Compass,
  target_market_change:        Target,
  event_or_thought_leadership: Calendar,
  hiring_signal:               UserPlus,
  other:                       HelpCircle,
};

export const labelMap: Record<SignalType, string> = {
  product_update:              'Product Update',
  ai_announcement:             'AI Announcement',
  partnership:                 'Partnership',
  positioning_change:          'Positioning',
  target_market_change:        'Market Shift',
  event_or_thought_leadership: 'Thought Leadership',
  hiring_signal:               'Hiring Signal',
  other:                       'Other',
};

// Explicit chip styles — avoids dynamic class generation issues with Tailwind JIT
const chipStyles: Record<SignalType, { bg: string; color: string }> = {
  product_update:              { bg: '#f0fdf4', color: '#15803d' },
  ai_announcement:             { bg: '#f5f3ff', color: '#6d28d9' },
  partnership:                 { bg: '#fff7ed', color: '#c2410c' },
  positioning_change:          { bg: '#fdf4ff', color: '#86198f' },
  target_market_change:        { bg: '#fff1f2', color: '#be123c' },
  event_or_thought_leadership: { bg: '#f0fdfa', color: '#0f766e' },
  hiring_signal:               { bg: '#eff6ff', color: '#1d4ed8' },
  other:                       { bg: '#f4f4f5', color: '#52525b' },
};

interface SignalTypeIconProps {
  type: SignalType;
  /** 'chip' renders a colored pill label; 'icon' renders icon only */
  variant?: 'chip' | 'icon';
  size?: number;
}

export default function SignalTypeIcon({ type, variant = 'chip', size = 14 }: SignalTypeIconProps) {
  const Icon = iconMap[type];
  const { bg, color } = chipStyles[type];

  if (variant === 'icon') {
    return <Icon size={size} style={{ color }} />;
  }

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold"
      style={{ background: bg, color }}
    >
      <Icon size={11} />
      {labelMap[type]}
    </span>
  );
}
```

- [ ] **Step 3.2: Visual verification**

Signal type labels should now show as colored chips (e.g. green for Product Update, purple for AI Announcement) wherever `SignalTypeIcon` is rendered.

- [ ] **Step 3.3: Commit**

```bash
rtk git add frontend/src/components/SignalTypeIcon.tsx
rtk git commit -m "feat: replace dynamic type classes with explicit chip styles"
```

---

## Task 4: RelevanceBadge

**Files:**
- Modify: `frontend/src/components/RelevanceBadge.tsx`

- [ ] **Step 4.1: Rewrite RelevanceBadge.tsx**

Replace the entire file:

```tsx
interface RelevanceBadgeProps {
  score: number | null;
  /** 'badge' = colored pill; 'bar' = progress bar + number (for tables) */
  variant?: 'badge' | 'bar';
  size?: 'sm' | 'md';
}

export default function RelevanceBadge({ score, variant = 'badge', size = 'md' }: RelevanceBadgeProps) {
  if (score === null || score === undefined) {
    return <span className="text-ink-muted text-xs">N/A</span>;
  }

  const pct = Math.round(score * 100);
  const isHigh   = score >= 0.7;
  const isMedium = score >= 0.4;

  const badgeStyle = isHigh
    ? { background: '#dcfce7', color: '#15803d' }
    : isMedium
    ? { background: '#fef3c7', color: '#92400e' }
    : { background: '#fee2e2', color: '#b91c1c' };

  const barColor = isHigh ? '#10b981' : isMedium ? '#f59e0b' : '#ef4444';

  if (variant === 'bar') {
    return (
      <div className="flex items-center gap-2 w-full">
        <div className="flex-1 h-1 bg-app-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${pct}%`, background: barColor }}
          />
        </div>
        <span className="text-[11px] font-bold text-ink min-w-[28px] text-right">{pct}%</span>
      </div>
    );
  }

  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-1';

  return (
    <span
      className={`inline-flex items-center rounded-md font-semibold ${sizeClass}`}
      style={badgeStyle}
    >
      {pct}%
    </span>
  );
}
```

- [ ] **Step 4.2: Visual verification**

Relevance badges should show as green/amber/red pills. No visual change in bar variant yet — that gets used in Task 7.

- [ ] **Step 4.3: Commit**

```bash
rtk git add frontend/src/components/RelevanceBadge.tsx
rtk git commit -m "feat: add bar variant to RelevanceBadge, update color tokens"
```

---

## Task 5: SignalCard

**Files:**
- Modify: `frontend/src/components/SignalCard.tsx`

- [ ] **Step 5.1: Rewrite SignalCard.tsx**

Replace the entire file:

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
  onClick?: () => void;
}

export default function SignalCard({ signal, showCompany = false, companyName, companySlug, onClick }: SignalCardProps) {
  const dateStr = signal.published_at
    ? new Date(signal.published_at).toLocaleDateString('de-DE')
    : new Date(signal.created_at).toLocaleDateString('de-DE');

  const cardContent = (
    <>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-[13px] font-semibold text-ink leading-snug mb-1.5">
            {signal.title}
          </h3>
          <div className="flex items-center gap-1.5 flex-wrap">
            <SignalTypeIcon type={signal.signal_type} variant="chip" />
            {signal.topic && (
              <span className="text-[10px] text-ink-muted bg-app-bg px-1.5 py-0.5 rounded-md border border-app-border">
                {signal.topic}
              </span>
            )}
            {signal.from_search && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-md font-semibold"
                style={{ background: '#f5f3ff', color: '#6d28d9' }}>
                Search
              </span>
            )}
          </div>
        </div>
        <RelevanceBadge score={signal.relevance_score} size="sm" />
      </div>

      {signal.summary && (
        <p className="text-[12px] text-ink-secondary line-clamp-2 mb-2 leading-relaxed">
          {signal.summary}
        </p>
      )}
      {signal.why_it_matters && (
        <p className="text-[11px] line-clamp-2 mb-2 leading-relaxed"
          style={{ color: '#2563eb' }}>
          <span className="font-semibold">Why it matters:</span> {signal.why_it_matters}
        </p>
      )}

      <div className="flex items-center justify-between mt-3 text-[11px] text-ink-muted border-t border-app-border pt-2">
        <span>{dateStr}</span>
        {showCompany && companyName && (
          <span className="font-medium text-accent-blue">{companyName}</span>
        )}
      </div>
    </>
  );

  const baseClass = "block w-full text-left bg-app-card border border-app-border rounded-xl p-4 transition-colors hover:border-accent-blue/40 hover:shadow-sm";

  if (onClick) {
    return <button onClick={onClick} className={baseClass}>{cardContent}</button>;
  }
  if (companySlug) {
    return <Link to={`/competitors/${companySlug}`} className={baseClass}>{cardContent}</Link>;
  }
  return <div className={baseClass}>{cardContent}</div>;
}
```

- [ ] **Step 5.2: Visual verification**

Signal cards should now show with white background, rounded-xl border, colored type chips, and blue company name link. Hover state should show a subtle blue border.

- [ ] **Step 5.3: Commit**

```bash
rtk git add frontend/src/components/SignalCard.tsx
rtk git commit -m "feat: restyle SignalCard with new design tokens and chip layout"
```

---

## Task 6: FilterBar

**Files:**
- Modify: `frontend/src/components/FilterBar.tsx`

- [ ] **Step 6.1: Rewrite FilterBar.tsx**

Replace the entire file. The filter bar switches from `<select>` + range to pill buttons for signal type and a minimal relevance slider:

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
  { value: 'product_update',              label: 'Product' },
  { value: 'ai_announcement',             label: 'AI' },
  { value: 'partnership',                 label: 'Partnership' },
  { value: 'positioning_change',          label: 'Positioning' },
  { value: 'target_market_change',        label: 'Market Shift' },
  { value: 'event_or_thought_leadership', label: 'Events' },
  { value: 'hiring_signal',               label: 'Hiring' },
];

const relevanceLevels: { value: number; label: string }[] = [
  { value: 0,   label: 'Alle' },
  { value: 0.4, label: '≥ 40%' },
  { value: 0.7, label: '≥ 70%' },
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
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {/* Company picker */}
      {companies && onCompanyChange && (
        <select
          value={companyId || ''}
          onChange={(e) => onCompanyChange(e.target.value)}
          className="input-field text-[12px] py-1.5 h-8"
        >
          <option value="">Alle Unternehmen</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      )}

      {/* Divider */}
      {companies && <div className="w-px h-5 bg-app-border" />}

      {/* Signal type pills */}
      <button
        onClick={() => onSignalTypeChange('')}
        className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
          signalType === ''
            ? 'bg-accent-blue/10 border-accent-blue/30 text-accent-blue'
            : 'bg-app-card border-app-border text-ink-secondary hover:bg-app-bg'
        }`}
      >
        Alle
      </button>
      {signalTypes.map((t) => (
        <button
          key={t.value}
          onClick={() => onSignalTypeChange(signalType === t.value ? '' : t.value)}
          className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
            signalType === t.value
              ? 'bg-accent-blue/10 border-accent-blue/30 text-accent-blue'
              : 'bg-app-card border-app-border text-ink-secondary hover:bg-app-bg'
          }`}
        >
          {t.label}
        </button>
      ))}

      {/* Divider */}
      <div className="w-px h-5 bg-app-border" />

      {/* Relevance level pills */}
      {relevanceLevels.map((r) => (
        <button
          key={r.value}
          onClick={() => onMinRelevanceChange(r.value)}
          className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
            minRelevance === r.value
              ? 'bg-signal-high/10 border-signal-high/30 text-signal-high'
              : 'bg-app-card border-app-border text-ink-secondary hover:bg-app-bg'
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 6.2: Visual verification**

The filter area should show pill buttons instead of dropdowns. Active pills are blue (type) or green (relevance). Company selector remains a `<select>` for usability.

- [ ] **Step 6.3: Commit**

```bash
rtk git add frontend/src/components/FilterBar.tsx
rtk git commit -m "feat: replace filter selects with pill buttons"
```

---

## Task 7: Dashboard — KPI grid + topbar

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 7.1: Rewrite Dashboard.tsx**

Replace the entire file:

```tsx
import { useState } from 'react';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useCrawlAll } from '../hooks/useCrawl';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import RelevanceBadge from '../components/RelevanceBadge';
import SignalTypeIcon from '../components/SignalTypeIcon';
import type { SignalType } from '../types';
import { Play, Loader2 } from 'lucide-react';

const KPI_BORDER: Record<string, string> = {
  blue:   'linear-gradient(90deg, #2563eb, #7c3aed)',
  green:  '#10b981',
  amber:  '#f59e0b',
  purple: '#7c3aed',
};

function KpiCard({ label, value, delta, color }: { label: string; value: string | number; delta?: string; color: keyof typeof KPI_BORDER }) {
  return (
    <div className="bg-app-card border border-app-border rounded-xl p-4 relative overflow-hidden">
      <div
        className="absolute top-0 left-0 right-0 h-[3px] rounded-t-xl"
        style={{ background: KPI_BORDER[color] }}
      />
      <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide mb-2">{label}</p>
      <p className="text-[28px] font-extrabold text-ink leading-none tracking-tight">{value}</p>
      {delta && <p className="text-[11px] text-signal-high font-medium mt-1">{delta}</p>}
    </div>
  );
}

export default function Dashboard() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [companyId, setCompanyId] = useState('');
  const crawlAll = useCrawlAll();

  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id:    companyId || undefined,
    signal_type:   signalType || undefined,
    min_relevance: minRelevance || undefined,
  });

  const { data: allSignals } = useSignals({});
  const competitorCount    = companies?.filter((c) => c.type === 'competitor').length ?? 0;
  const highRelevanceCount = allSignals?.filter((s) => (s.relevance_score ?? 0) >= 0.7).length ?? 0;
  const activeSourceCount  = companies?.length ?? 0;

  return (
    <div className="flex flex-col h-full">
      {/* Topbar */}
      <div className="bg-app-card border-b border-app-border px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[15px] font-bold text-ink tracking-tight">Dashboard</h1>
          <p className="text-[12px] text-ink-muted mt-0.5">
            {allSignals?.length ?? '–'} Signale gesamt
          </p>
        </div>
        <div className="flex items-center gap-3">
          {crawlAll.isPending && (
            <span className="flex items-center gap-1.5 text-[11px] text-signal-high font-medium">
              <Loader2 size={12} className="animate-spin" />
              Crawling...
            </span>
          )}
          <button
            onClick={() => crawlAll.mutate()}
            disabled={crawlAll.isPending}
            className="btn-primary flex items-center gap-1.5 text-[12px] py-1.5 px-3"
          >
            <Play size={12} />
            Crawl starten
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-5">
        {/* Status banners */}
        {crawlAll.isSuccess && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border"
            style={{ background: '#f0fdf4', color: '#15803d', borderColor: '#bbf7d0' }}>
            Crawl abgeschlossen: {crawlAll.data.sources_processed} Quellen verarbeitet
          </div>
        )}
        {crawlAll.isError && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border"
            style={{ background: '#fef2f2', color: '#b91c1c', borderColor: '#fecaca' }}>
            Crawl fehlgeschlagen
          </div>
        )}

        {/* KPI grid */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <KpiCard label="Signale gesamt"  value={allSignals?.length ?? '–'}  color="blue" />
          <KpiCard label="Hohe Relevanz"   value={highRelevanceCount}          color="green" />
          <KpiCard label="Wettbewerber"    value={competitorCount}             color="amber" />
          <KpiCard label="Unternehmen"     value={activeSourceCount}           color="purple" />
        </div>

        {/* Filters */}
        <FilterBar
          signalType={signalType}
          onSignalTypeChange={setSignalType}
          minRelevance={minRelevance}
          onMinRelevanceChange={setMinRelevance}
          companyId={companyId}
          onCompanyChange={setCompanyId}
          companies={companies}
        />

        {/* Signal table */}
        {signalsLoading || companiesLoading ? (
          <div className="flex items-center gap-2 text-ink-muted text-[13px]">
            <Loader2 size={14} className="animate-spin" />
            Lade Signale...
          </div>
        ) : (
          <div className="bg-app-card border border-app-border rounded-xl overflow-hidden">
            {/* Table head */}
            <div
              className="grid text-[10px] font-semibold uppercase tracking-wider text-ink-muted px-4 py-2.5 border-b border-app-border-sub"
              style={{ gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1fr) 140px 90px 90px' }}
            >
              <span>Signal</span>
              <span>Unternehmen</span>
              <span>Typ</span>
              <span>Datum</span>
              <span>Relevanz</span>
            </div>

            {signals?.length === 0 && (
              <p className="text-ink-muted text-[13px] text-center py-8">
                Keine Signale gefunden. Crawl starten?
              </p>
            )}

            {signals?.map((signal) => {
              const company = companies?.find((c) => c.id === signal.company_id);
              const dateStr = signal.published_at
                ? new Date(signal.published_at).toLocaleDateString('de-DE')
                : new Date(signal.created_at).toLocaleDateString('de-DE');

              return (
                <div
                  key={signal.id}
                  className="grid items-center px-4 py-3 border-b border-app-border-sub last:border-b-0 hover:bg-app-bg cursor-pointer transition-colors"
                  style={{ gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1fr) 140px 90px 90px' }}
                >
                  {/* Signal */}
                  <div className="min-w-0 pr-4">
                    <p className="text-[12px] font-semibold text-ink truncate">{signal.title}</p>
                    {signal.summary && (
                      <p className="text-[11px] text-ink-muted truncate mt-0.5">{signal.summary}</p>
                    )}
                  </div>

                  {/* Company */}
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ background: company ? '#2563eb' : '#a1a1aa' }}
                    />
                    <span className="text-[12px] font-medium text-ink-secondary truncate">
                      {company?.name ?? '—'}
                    </span>
                  </div>

                  {/* Type */}
                  <div>
                    <SignalTypeIcon type={signal.signal_type} variant="chip" />
                  </div>

                  {/* Date */}
                  <span className="text-[11px] text-ink-muted">{dateStr}</span>

                  {/* Relevance */}
                  <RelevanceBadge score={signal.relevance_score} variant="bar" />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 7.2: Visual verification**

Dashboard should now show:
- White topbar with title + crawl button
- 4 KPI cards with colored top borders and large bold numbers
- Pill-style filter bar
- Signal table with type chips, company dots, and progress bar relevance

- [ ] **Step 7.3: Commit**

```bash
rtk git add frontend/src/pages/Dashboard.tsx
rtk git commit -m "feat: redesign Dashboard with KPI grid and signal table"
```

---

## Task 8: Sweep remaining pages

**Files:**
- Modify: `frontend/src/pages/CompetitorList.tsx`
- Modify: `frontend/src/pages/CompetitorDetail.tsx`
- Modify: `frontend/src/pages/MarketTrends.tsx`
- Modify: `frontend/src/pages/WeeklyDigest.tsx`
- Modify: `frontend/src/pages/LoginPage.tsx`

These pages use `.card`, `text-dark-muted`, `text-dark-text`, `text-dark-accent`, `bg-dark-bg`, `bg-dark-card`, `border-dark-border` — all now unmapped. Replace each reference with the new tokens.

- [ ] **Step 8.1: Global token replacements**

For each page listed above, make these replacements (all occurrences):

| Old class | New class |
|-----------|-----------|
| `text-dark-text` | `text-ink` |
| `text-dark-muted` | `text-ink-muted` |
| `text-dark-accent` | `text-accent-blue` |
| `bg-dark-bg` | `bg-app-bg` |
| `bg-dark-card` | `bg-app-card` |
| `border-dark-border` | `border-app-border` |
| `border-dark-accent` | `border-accent-blue` |
| `ring-dark-accent` | `ring-accent-blue` |
| `text-indigo-300` or `text-indigo-400` | `text-accent-blue` |
| `bg-dark-accent` | `bg-accent-blue` |
| `hover:bg-dark-bg` | `hover:bg-app-bg` |
| `hover:bg-slate-700` | `hover:bg-app-bg` |
| `hover:text-dark-text` | `hover:text-ink` |
| `hover:border-dark-accent/50` | `hover:border-accent-blue/40` |
| `focus:ring-dark-accent` | `focus:ring-accent-blue` |

Also add `p-6` to the `<main>` content wrapper inside each page if they rely on outer padding (check: the Layout's `<main>` previously had `p-6` — now it doesn't, so pages need their own padding).

- [ ] **Step 8.2: Add page padding where missing**

Pages that previously relied on Layout's `p-6` need a wrapper. For each page, wrap the root `<div>` in `<div className="p-6">` if it doesn't already have padding. Verify in browser — no content should be flush against the edges.

- [ ] **Step 8.3: Update LoginPage**

`LoginPage.tsx` uses the old dark theme for the login card. Update it to use a light centered layout:
- Outer: `min-h-screen bg-app-bg flex items-center justify-center`
- Card: `bg-app-card border border-app-border rounded-2xl p-8 w-full max-w-sm shadow-sm`
- Title: `text-[20px] font-bold text-ink`
- Inputs: use `.input-field`
- Button: use `.btn-primary w-full`

- [ ] **Step 8.4: Visual verification**

Navigate through each page: Wettbewerber, Markt-Trends, Weekly Digest, Login. All should use light backgrounds with the navy sidebar visible. No dark gray cards or charcoal backgrounds should remain.

- [ ] **Step 8.5: Commit**

```bash
rtk git add frontend/src/pages/
rtk git commit -m "feat: apply new design tokens across all pages"
```

---

## Task 9: Final polish pass

- [ ] **Step 9.1: Check SourcesAdmin and SearchPage**

These two pages (`SourcesAdmin.tsx`, `SearchPage.tsx`) are complex admin interfaces. Apply the same token replacements from Task 8, Step 8.1. Pay attention to tables, modals, and status badges — replace all dark token references.

- [ ] **Step 9.2: Check CrawlProgressPanel**

`CrawlProgressPanel.tsx` — apply token replacements. Status colors (green/red for crawl states) should use `text-signal-high` and `text-signal-low`.

- [ ] **Step 9.3: Check CompanyContext**

`CompanyContext.tsx` uses tag input UI and list fields. Apply token replacements. Verify the tag chips use `bg-app-bg border-app-border text-ink` styling.

- [ ] **Step 9.4: Full walkthrough**

Visit every page in sequence. Look for:
- Any remaining dark backgrounds (charcoal, dark gray)
- Any white text on white background
- Any missing padding / layout issues
- Any unmapped Tailwind class warnings in the browser console

Fix any remaining issues before committing.

- [ ] **Step 9.5: Final commit**

```bash
rtk git add frontend/src/
rtk git commit -m "feat: complete frontend redesign — navy sidebar, Geist font, SaaS design system"
```
