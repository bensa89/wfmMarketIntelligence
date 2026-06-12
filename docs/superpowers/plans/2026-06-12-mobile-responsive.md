# Mobile Responsive Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the WFM Market Intelligence frontend usable on smartphones (375px+) by adding a hamburger drawer navigation and applying responsive layouts to Sources Admin, Weekly Digest, and Signals Feed.

**Architecture:** The desktop sidebar stays untouched above `md` (768px). Below `md`, a fixed `h-12` top header with a hamburger button replaces the sidebar; tapping it opens a slide-in drawer overlay with the full nav. The three pages get Tailwind `sm:`/`md:` breakpoints and, for the Signals Feed table, a dedicated mobile card list view.

**Tech Stack:** React 18, TypeScript, Tailwind CSS v3, lucide-react

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/components/Layout.tsx` | Mobile header + hamburger drawer, sidebar `hidden md:flex` |
| `frontend/src/pages/WeeklyDigest.tsx` | `flex-col md:flex-row`, mobile `<select>` for digest picker |
| `frontend/src/pages/SignalsFeedPage.tsx` | `px-4 md:px-6` padding |
| `frontend/src/components/signals/SignalFeedFilters.tsx` | `sticky top-12 md:top-0`, mobile padding |
| `frontend/src/components/signals/SignalFeedTable.tsx` | Mobile card list (hidden on `md+`), table hidden below `md` |
| `frontend/src/pages/SourcesAdmin.tsx` | Responsive header/form, `overflow-x-auto` on all tables |

---

### Task 1: Layout.tsx — Mobile header and hamburger drawer

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Replace Layout.tsx with the mobile-responsive version**

Full file replacement. Three sub-components are extracted (`SidebarLogo`, `NavItems`, `LogoutButton`) so both the desktop sidebar and the mobile drawer can share them without duplication. A new `drawerOpen` state controls the mobile drawer.

```tsx
import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard, Users, TrendingUp, FileText, Settings, Search,
  Globe, LogOut, BarChart2, Zap, BookOpen, Clock, Terminal, Menu, X,
} from 'lucide-react';
import { hasCredentials, clearCredentials } from '../api/client';
import { useNavigate } from 'react-router-dom';

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
    label: 'Übersicht',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
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
      { to: '/admin/schedule', label: 'Automation', icon: Clock },
      { to: '/admin/logs', label: 'Logs', icon: Terminal },
      { to: '/context', label: 'Kontext', icon: Globe },
      { to: '/how-it-works', label: "Wie funktioniert's?", icon: BookOpen },
    ],
  },
];

function SidebarLogo() {
  return (
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
  );
}

function NavItems({ onNavClick }: { onNavClick?: () => void }) {
  return (
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
              onClick={onNavClick}
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
  );
}

function LogoutButton({ onLogout }: { onLogout: () => void }) {
  return (
    <div className="px-2 py-3" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
      <button
        onClick={onLogout}
        className="flex items-center gap-2 w-full px-2 py-[7px] rounded-[7px] text-[12px] font-medium transition-colors hover:bg-white/5"
        style={{ color: 'rgba(248,250,252,0.35)' }}
      >
        <LogOut size={14} />
        Logout
      </button>
    </div>
  );
}

export default function Layout() {
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);

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
      {/* ── Desktop Sidebar ── */}
      <nav
        className="hidden md:flex w-56 flex-col flex-shrink-0"
        style={{ background: '#0f172a' }}
      >
        <SidebarLogo />
        <NavItems />
        <LogoutButton onLogout={handleLogout} />
      </nav>

      {/* ── Mobile Header ── */}
      <header
        className="md:hidden fixed top-0 left-0 right-0 h-12 z-40 flex items-center px-4 gap-3"
        style={{ background: '#0f172a', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        <button
          onClick={() => setDrawerOpen(true)}
          className="text-slate-400 hover:text-slate-200 p-1"
          aria-label="Navigation öffnen"
        >
          <Menu size={20} />
        </button>
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded-[6px] flex items-center justify-center text-[10px] font-extrabold text-white flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #2563eb, #7c3aed)' }}
          >
            W
          </div>
          <span className="text-[13px] font-semibold text-slate-50">WFM Intel</span>
        </div>
      </header>

      {/* ── Mobile Drawer Backdrop ── */}
      {drawerOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 z-40"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* ── Mobile Drawer ── */}
      <nav
        className={`md:hidden fixed inset-y-0 left-0 w-72 z-50 flex flex-col transition-transform duration-200 ${
          drawerOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ background: '#0f172a' }}
      >
        <div
          className="flex items-center justify-between px-4 py-[18px]"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-2.5">
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
          <button
            onClick={() => setDrawerOpen(false)}
            className="text-slate-400 hover:text-slate-200 p-1"
            aria-label="Navigation schließen"
          >
            <X size={18} />
          </button>
        </div>
        <NavItems onNavClick={() => setDrawerOpen(false)} />
        <LogoutButton onLogout={handleLogout} />
      </nav>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-auto pt-12 md:pt-0">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser at 375px**

Open DevTools → Toggle device toolbar → iPhone SE (375×667).  
Expected:
- Sidebar is **not** visible
- Dark top header with hamburger icon + "WFM Intel" logo
- Tapping hamburger opens drawer from the left with full nav
- Tapping any nav link closes drawer and navigates
- Tapping the backdrop closes drawer
- At ≥768px: sidebar appears, no header bar, no drawer

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat: add mobile hamburger drawer and responsive layout shell"
```

---

### Task 2: WeeklyDigest.tsx — Responsive layout

**Files:**
- Modify: `frontend/src/pages/WeeklyDigest.tsx`

- [ ] **Step 1: Update outer padding**

Find line 117:
```tsx
<div className="p-6">
```
Replace with:
```tsx
<div className="p-4 md:p-6">
```

- [ ] **Step 2: Make page header wrap on small screens**

Find lines 118–130:
```tsx
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
```
Replace with:
```tsx
<div className="flex flex-wrap items-start justify-between gap-3 mb-6">
  <h1 className="text-2xl font-bold flex items-center gap-2">
    <Calendar size={24} /> Weekly Digest
  </h1>
  <button
    onClick={() => generateDigest.mutate()}
    disabled={generateDigest.isPending}
    className="btn-primary flex items-center gap-2 flex-shrink-0"
  >
    <RefreshCw size={16} className={generateDigest.isPending ? 'animate-spin' : ''} />
    {generateDigest.isPending ? 'Generating...' : 'Generate New Digest'}
  </button>
</div>
```

- [ ] **Step 3: Add mobile select + hide desktop digest list on mobile**

Find line 146 — the outer two-column container:
```tsx
<div className="flex gap-6">
  <div className="w-64 shrink-0 space-y-2">
    {digests?.map((digest: Digest) => (
      <button
        key={digest.id}
        onClick={() => setSelectedDigestId(digest.id)}
        className={`w-full text-left p-3 rounded border transition-colors ${
          selectedDigest?.id === digest.id
            ? 'border-accent-blue bg-accent-blue/5'
            : 'border-gray-200 bg-white hover:bg-gray-50'
        }`}
      >
        <div className="text-sm font-medium text-gray-900">
          {digest.week_start} — {digest.week_end}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {digest.sections?.length ?? 0} sections · {digest.is_published ? 'Published' : 'Draft'}
        </div>
      </button>
    ))}
  </div>

  {selectedDigest && (
    <div className="flex-1 min-w-0">
      <div className="card">
        <div className="flex items-center justify-between mb-4">
```

Replace the entire block (through the closing `</div>` of the outer `flex gap-6` div) with:

```tsx
{/* Mobile: dropdown to pick a digest */}
<select
  className="md:hidden w-full mb-4 input-field"
  value={selectedDigest?.id ?? ''}
  onChange={(e) => setSelectedDigestId(e.target.value)}
>
  {digests?.map((digest: Digest) => (
    <option key={digest.id} value={digest.id}>
      KW {getISOWeek(digest.week_start)}: {digest.week_start} — {digest.week_end}
    </option>
  ))}
</select>

<div className="flex gap-6">
  {/* Desktop: sidebar button list */}
  <div className="hidden md:block w-64 shrink-0 space-y-2">
    {digests?.map((digest: Digest) => (
      <button
        key={digest.id}
        onClick={() => setSelectedDigestId(digest.id)}
        className={`w-full text-left p-3 rounded border transition-colors ${
          selectedDigest?.id === digest.id
            ? 'border-accent-blue bg-accent-blue/5'
            : 'border-gray-200 bg-white hover:bg-gray-50'
        }`}
      >
        <div className="text-sm font-medium text-gray-900">
          {digest.week_start} — {digest.week_end}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {digest.sections?.length ?? 0} sections · {digest.is_published ? 'Published' : 'Draft'}
        </div>
      </button>
    ))}
  </div>

  {selectedDigest && (
    <div className="flex-1 min-w-0">
      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              KW {getISOWeek(selectedDigest.week_start)}: {formatDateDE(selectedDigest.week_start)} – {formatDateDE(selectedDigest.week_end)}
            </h2>
            {selectedDigest.summary && (
              <p className="text-sm text-gray-600 mt-1">{selectedDigest.summary}</p>
            )}
          </div>
          <button
            onClick={() => handleCopyEmail(selectedDigest)}
            disabled={!selectedDigest.sections?.length}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
          >
            {copied ? '✓ Kopiert' : 'Als E-Mail kopieren'}
          </button>
        </div>

        {selectedDigest.sections && selectedDigest.sections.length > 0 ? (
          <div className="space-y-8">
            {selectedDigest.sections.map((section) => (
              <div key={section.key}>
                <h3 className="text-base font-semibold text-gray-900 mb-3 pb-2 border-b border-gray-200">
                  {section.title}
                </h3>
                <SectionItems items={section.items} />
              </div>
            ))}
          </div>
        ) : selectedDigest.key_signals && selectedDigest.key_signals.length > 0 ? (
          <ul className="space-y-3">
            {selectedDigest.key_signals.map((sig) => (
              <li key={sig.id} className="text-sm">
                <span className="font-medium">{sig.company_name}</span> — {sig.title}
                {sig.source_url && (
                  <a href={sig.source_url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600 hover:underline text-xs">
                    source
                  </a>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">Keine Signale für diese Woche.</p>
        )}
      </div>
    </div>
  )}
</div>
```

- [ ] **Step 4: Verify in browser at 375px**

Open `/digest`. Expected:
- `<select>` dropdown at top for picking a digest
- Selected digest content displayed below it, full width
- "Generate New Digest" button wraps below title if needed
- At ≥768px: sidebar button list + content side-by-side, `<select>` hidden

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/WeeklyDigest.tsx
git commit -m "feat: make Weekly Digest page responsive for mobile"
```

---

### Task 3: SignalFeedFilters.tsx — Fix sticky offset for mobile header

**Files:**
- Modify: `frontend/src/components/signals/SignalFeedFilters.tsx`

- [ ] **Step 1: Adjust sticky top and padding**

The mobile header is `h-12` (48px). The sticky filter bar must sit below it on mobile.

Find line 33:
```tsx
<div
  className="sticky top-0 z-10 flex flex-wrap items-center gap-2 px-6 py-3 -mx-6 mb-4"
  style={{ background: '#ffffff', borderBottom: '1px solid #e2e8f0' }}
>
```
Replace with:
```tsx
<div
  className="sticky top-12 md:top-0 z-10 flex flex-wrap items-center gap-2 px-4 md:px-6 py-3 -mx-4 md:-mx-6 mb-4"
  style={{ background: '#ffffff', borderBottom: '1px solid #e2e8f0' }}
>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/signals/SignalFeedFilters.tsx
git commit -m "fix: signal feed filter bar accounts for mobile header height"
```

---

### Task 4: SignalsFeedPage.tsx — Mobile padding

**Files:**
- Modify: `frontend/src/pages/SignalsFeedPage.tsx`

- [ ] **Step 1: Reduce page padding on mobile**

Find line 38:
```tsx
<div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
```
Replace with:
```tsx
<div className="bg-white border-b border-slate-200 px-4 md:px-6 py-4 flex-shrink-0">
```

Find line 42:
```tsx
<div className="flex-1 overflow-auto px-6 py-5">
```
Replace with:
```tsx
<div className="flex-1 overflow-auto px-4 md:px-6 py-5">
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/SignalsFeedPage.tsx
git commit -m "fix: reduce signals feed page padding on mobile"
```

---

### Task 5: SignalFeedTable.tsx — Mobile card view

**Files:**
- Modify: `frontend/src/components/signals/SignalFeedTable.tsx`

- [ ] **Step 1: Replace SignalFeedTable with mobile card + desktop table**

Full file replacement. A `Pagination` sub-component is extracted to avoid duplication. Below `md`: card list. At `md+`: original table (already had `overflow-x-auto`).

```tsx
import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from './MovementBadge';
import ConfidenceBar from './ConfidenceBar';
import { getCapabilityLabel } from '../../constants/capabilities';
import DateWithTooltip from '../DateWithTooltip';

interface Props {
  items: SignalFeedItem[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  onSelectItem: (item: SignalFeedItem) => void;
}

function Pagination({ page, total, pageSize, onPageChange }: Pick<Props, 'page' | 'total' | 'pageSize' | 'onPageChange'>) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-200">
      <span className="text-[12px] text-slate-500">{total} total signals</span>
      <div className="flex gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="px-2.5 py-1 rounded-md text-[12px] bg-white border border-slate-200 text-slate-600 hover:text-slate-900 disabled:opacity-30 transition-colors"
        >
          ←
        </button>
        <span className="px-3 py-1 text-[12px] text-slate-600 tabular-nums">{page} / {totalPages}</span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="px-2.5 py-1 rounded-md text-[12px] bg-white border border-slate-200 text-slate-600 hover:text-slate-900 disabled:opacity-30 transition-colors"
        >
          →
        </button>
      </div>
    </div>
  );
}

export default function SignalFeedTable({ items, total, page, pageSize, onPageChange, onSelectItem }: Props) {
  if (items.length === 0) {
    return (
      <div className="py-12 text-center text-slate-500 text-sm">
        No signals match the current filters
      </div>
    );
  }

  return (
    <div>
      {/* ── Mobile card list (hidden on md+) ── */}
      <div className="md:hidden space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="bg-white rounded-lg border border-slate-200 p-3 cursor-pointer hover:bg-slate-50 transition-colors"
            onClick={() => onSelectItem(item)}
          >
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <span className="text-[11px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded whitespace-nowrap">
                {item.company_name ?? '—'}
              </span>
              <MovementBadge strength={item.assessment?.movement_strength} />
            </div>
            <div className="text-[13px] font-medium text-slate-900 line-clamp-2 leading-snug mb-1.5">
              {item.title}
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              {item.assessment?.capability_primary && (
                <span className="text-[11px] text-slate-500 truncate">
                  {getCapabilityLabel(item.assessment.capability_primary)}
                </span>
              )}
              <ConfidenceBar value={item.assessment?.confidence} />
              {item.published_at && (
                <span className="text-[11px] text-slate-400 ml-auto whitespace-nowrap">
                  <DateWithTooltip date={item.published_at} />
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* ── Desktop table (hidden below md) ── */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              {['Signal', 'Competitor', 'Capability', 'Strength', 'Confidence', 'Datum'].map((h) => (
                <th key={h} className="text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500 pb-2 pr-4 pt-2">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => onSelectItem(item)}
              >
                <td className="py-3 pr-4 max-w-[300px]">
                  <div className="text-slate-900 font-medium line-clamp-2 leading-snug">{item.title}</div>
                  {item.topic && <div className="text-slate-500 text-[11px] mt-0.5 truncate">{item.topic}</div>}
                </td>
                <td className="py-3 pr-4 text-slate-600 whitespace-nowrap">{item.company_name ?? '—'}</td>
                <td className="py-3 pr-4 text-slate-600 whitespace-nowrap">
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
                <td className="py-3 text-slate-600">
                  {item.published_at && (
                    <div>
                      <DateWithTooltip date={item.published_at} />
                    </div>
                  )}
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    analysiert: <DateWithTooltip date={item.created_at} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} total={total} pageSize={pageSize} onPageChange={onPageChange} />
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Open `/signals` at 375px. Expected:
- Card list visible (no table)
- Each card shows company badge top-left, movement badge top-right, signal title (max 2 lines), capability text, confidence bar, date
- Tapping a card opens `SignalDetailDrawer`
- At ≥768px: original table visible, card list hidden

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/signals/SignalFeedTable.tsx
git commit -m "feat: add mobile card view to SignalFeedTable"
```

---

### Task 6: SourcesAdmin.tsx — Responsive header, form, and table overflow

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Responsive outer padding**

Find line 378:
```tsx
<div className="p-6">
```
Replace with:
```tsx
<div className="p-4 md:p-6">
```

- [ ] **Step 2: Responsive page header**

Find lines 379–389:
```tsx
<div className="flex items-center justify-between mb-6">
  <h1 className="text-2xl font-bold">Sources Admin</h1>
  <div className="flex gap-2">
    <button onClick={() => crawl.start()} disabled={crawl.isRunning} className="btn-primary flex items-center gap-2">
      <Play size={16} /> {crawl.phase === 'analysing' ? 'Analysiere...' : crawl.phase === 'crawling' ? 'Crawling...' : 'Run Full Crawl'}
    </button>
    <button onClick={() => setNewCompanyOpen(true)} className="btn-secondary flex items-center gap-2">
      <Plus size={16} /> Add Company
    </button>
  </div>
</div>
```
Replace with:
```tsx
<div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6">
  <h1 className="text-2xl font-bold">Sources Admin</h1>
  <div className="flex gap-2 flex-wrap">
    <button onClick={() => crawl.start()} disabled={crawl.isRunning} className="btn-primary flex items-center gap-2">
      <Play size={16} /> {crawl.phase === 'analysing' ? 'Analysiere...' : crawl.phase === 'crawling' ? 'Crawling...' : 'Run Full Crawl'}
    </button>
    <button onClick={() => setNewCompanyOpen(true)} className="btn-secondary flex items-center gap-2">
      <Plus size={16} /> Add Company
    </button>
  </div>
</div>
```

- [ ] **Step 3: Responsive "Add Source" form**

Find line 417:
```tsx
<form onSubmit={handleCreateSource} className="flex items-end gap-3">
```
Replace with:
```tsx
<form onSubmit={handleCreateSource} className="flex flex-col sm:flex-row items-stretch sm:items-end gap-3">
```

- [ ] **Step 4: Wrap the source table in the main company list with overflow-x-auto**

The table is rendered inside the `{isExpanded && (...)}` block. Find (around line 624):
```tsx
                 <table className="w-full text-sm mt-3">
                    <thead>
                      <tr className="border-b border-app-border">
                       <th className="w-8 py-2"></th>
                       <th className="text-left py-2 text-ink-muted font-medium">URL</th>
```
Replace with:
```tsx
                 <div className="overflow-x-auto mt-3">
                 <table className="w-full text-sm min-w-[640px]">
                    <thead>
                      <tr className="border-b border-app-border">
                       <th className="w-8 py-2"></th>
                       <th className="text-left py-2 text-ink-muted font-medium">URL</th>
```
Then find the closing `</table>` that ends this table (before `</div>` of the `{isExpanded && ...}` block, around line 721) and add `</div>` after it:
```tsx
                 </table>
                 </div>
```

- [ ] **Step 5: Wrap the source table in the search results section with overflow-x-auto**

Find the second identical table block (inside `byCompany.entries().map`, around line 488):
```tsx
                      <table className="w-full text-sm mt-3">
                      <thead>
                        <tr className="border-b border-app-border">
                          <th className="w-8 py-2"></th>
                          <th className="text-left py-2 text-ink-muted font-medium">URL</th>
```
Replace with:
```tsx
                      <div className="overflow-x-auto mt-3">
                      <table className="w-full text-sm min-w-[640px]">
                      <thead>
                        <tr className="border-b border-app-border">
                          <th className="w-8 py-2"></th>
                          <th className="text-left py-2 text-ink-muted font-medium">URL</th>
```
Add `</div>` after the closing `</table>` of this block (around line 567).

- [ ] **Step 6: Wrap the DiscoveredPagesSection table**

In `DiscoveredPagesSection` (around line 131), find:
```tsx
  return (
    <table className="w-full text-xs mt-1">
```
Replace with:
```tsx
  return (
    <div className="overflow-x-auto">
    <table className="w-full text-xs mt-1 min-w-[700px]">
```
Find the closing `</table>` at the end of `DiscoveredPagesSection` and add `</div>` after it:
```tsx
    </table>
    </div>
  );
```

- [ ] **Step 7: Verify in browser at 375px**

Open `/admin/sources`. Expected:
- "Sources Admin" title and action buttons stack vertically
- "Add Source" form fields stack vertically, each full width
- Expanding a company shows a horizontally scrollable table
- Discovered pages also horizontally scrollable
- At ≥640px: form fields align horizontally again

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/SourcesAdmin.tsx
git commit -m "feat: make Sources Admin page responsive for mobile"
```
