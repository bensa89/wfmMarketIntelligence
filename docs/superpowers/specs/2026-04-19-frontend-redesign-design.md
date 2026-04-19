# Frontend Redesign — Design Spec
_WFM Market Intelligence Hub · 2026-04-19_

## Context

The existing frontend is functional but generic: dark charcoal background, indigo accents, Inter font, standard card grid — nothing that feels intentionally designed. The goal is a redesign that looks and feels like a modern, premium internal SaaS product while remaining efficient to use.

---

## Design Direction: Modern SaaS — Deep Navy + Clean White

**Core concept:** Deep Navy sidebar anchors the layout and gives the app visual identity. The main content area is light, airy, and high-contrast. The combination creates a professional "product" feeling without heavy-dark-mode fatigue.

### Color System

```css
/* Sidebar */
--sidebar-bg:           #0f172a;   /* deep navy */
--sidebar-text:         rgba(248, 250, 252, 0.45);
--sidebar-text-active:  #93c5fd;
--sidebar-active-bg:    rgba(37, 99, 235, 0.18);
--sidebar-border:       rgba(255, 255, 255, 0.06);
--sidebar-label:        rgba(248, 250, 252, 0.20);

/* Main surface */
--bg-app:               #f8f8fa;
--bg-card:              #ffffff;
--border:               #ececf0;
--border-subtle:        #f4f4f6;

/* Text */
--text-primary:         #09090b;
--text-secondary:       #71717a;
--text-muted:           #a1a1aa;

/* Accents */
--accent-blue:          #2563eb;
--accent-purple:        #7c3aed;
--accent-gradient:      linear-gradient(135deg, #2563eb, #7c3aed);

/* Signal relevance */
--rel-high:             #10b981;   /* ≥70% */
--rel-medium:           #f59e0b;   /* 40–69% */
--rel-low:              #ef4444;   /* <40% */

/* Signal type chips */
--chip-ai:     #f5f3ff / #6d28d9
--chip-hire:   #eff6ff / #1d4ed8
--chip-prod:   #f0fdf4 / #15803d
--chip-part:   #fff7ed / #c2410c
--chip-pos:    #fdf4ff / #86198f
```

### Typography

**Font:** Geist (by Vercel) — clean, modern, highly legible at small sizes.

| Role | Size | Weight |
|------|------|--------|
| Page title | 15px | 700 |
| Section title | 13px | 600 |
| Table title / nav item | 13px | 500 |
| Body / table cell | 12px | 400–500 |
| Labels / meta / chips | 10–11px | 500–600 |
| KPI value | 28px | 800 |

---

## Layout

### App Shell

```
┌─────────────────────────────────────────────┐
│  Browser Chrome                             │
├──────────┬──────────────────────────────────┤
│          │  Topbar (title + actions)        │
│ Sidebar  ├──────────────────────────────────┤
│  Navy    │                                  │
│  228px   │  Content Area (scrollable)       │
│          │                                  │
│  [user]  │                                  │
└──────────┴──────────────────────────────────┘
```

### Sidebar Structure

- **Logo block:** Gradient logo-mark (28px, blue→purple), "WFM Intel" bold, "Market Intelligence" muted subtitle
- **Navigation sections** with uppercase 9px labels:
  - _Übersicht_: Dashboard (with alert badge), Wettbewerber, Markt-Trends
  - _Berichte_: Weekly Digest (with badge), Verlauf
  - _Admin_: Quellen, Suche, Kontext
- **User footer:** Avatar (gradient), name, role

Active nav item: `rgba(37,99,235,0.18)` background, `#93c5fd` text.
Alert badge: `rgba(239,68,68,0.2)` background, `#fca5a5` text.

### Topbar

- Left: page title (700 weight) + subtitle (date + count, muted)
- Right: Live indicator (pulsing green dot), ghost "Suche" button, primary "Crawl starten" button

### Dashboard Content

**KPI Cards (4-column grid):**
Each card has a 3px color-coded top border (gradient / green / amber / purple), large 28px/800w number, label, and delta line.

**Signal Table:**
- Columns: Signal (title + desc), Unternehmen (dot + name), Typ (chip), Datum, Relevanz (bar + %)
- Column widths: `2.2fr 1fr 120px 85px 80px`
- Row hover: `#fafafa` background
- Relevance bar: 4px track, gradient fill for high, amber for medium

---

## Components to Redesign

All existing components keep their logic — only styling changes.

| Component | Key changes |
|-----------|-------------|
| `Layout.tsx` | Navy sidebar, new nav structure, user footer |
| `SignalCard.tsx` | Lighter card style, new chip/badge system |
| `RelevanceBadge.tsx` | New color tokens, bar variant for tables |
| `SignalTypeIcon.tsx` | Chip style instead of icon-only |
| `FilterBar.tsx` | Pill-style filters matching new system |
| `Dashboard.tsx` | KPI grid + table layout |
| All pages | `bg-app` surface, updated spacing |

CSS variables defined in `index.css`, Tailwind config updated with new tokens. Geist font loaded via Google Fonts or local bundle.

---

## Out of Scope

- No changes to routing, API calls, or data logic
- No new features or pages
- No dark mode toggle (navy sidebar + light main is the single theme)
- Mobile responsiveness not addressed in this pass
