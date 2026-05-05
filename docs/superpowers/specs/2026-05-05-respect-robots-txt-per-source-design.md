# Spec: Per-Source `respect_robots_txt` Toggle

**Date:** 2026-05-05  
**Status:** Approved

## Problem

The crawler currently respects `robots.txt` globally for all sources. For competitive intelligence use cases (e.g. gfos.com), product subpages are blocked by `robots.txt` for SEO reasons — not because the content is private. This makes discovery completely ineffective for many competitor sources.

## Goal

Allow each source to independently control whether `robots.txt` is respected during discovery crawling. Default is `True` (conservative) so existing sources are unaffected.

---

## Backend

### Model (`backend/app/models/source.py`)
Add field to `Source`:
```python
respect_robots_txt = Column(Boolean, default=True, nullable=False)
```

### Migration
Alembic migration: `ADD COLUMN respect_robots_txt BOOLEAN NOT NULL DEFAULT TRUE`  
Existing rows default to `True` — no behavioral change for existing sources.

### Schemas (`backend/app/schemas/source.py`)
- `SourceCreate`: add `respect_robots_txt: bool = True`
- `SourceUpdate`: add `respect_robots_txt: Optional[bool] = None`
- `SourceRead`: add `respect_robots_txt: bool`

### Crawler (`backend/app/crawler/discovery.py`)
Change the robots.txt check at line 246 from:
```python
if not robot_parser.can_fetch("*", url):
```
to:
```python
if source.respect_robots_txt and not robot_parser.can_fetch("*", url):
```

---

## Frontend

### Types (`frontend/src/types.ts`)
Add `respect_robots_txt: boolean` to the `Source` interface.

### Source table (`frontend/src/pages/SourcesAdmin.tsx`)
Add a narrow column with a `Shield` icon (Lucide) in each source row:
- Green shield: robots.txt respected
- Grey shield with line-through or muted: robots.txt ignored
- Tooltip explains the current state

No column header text needed — icon is self-explanatory with tooltip.

### Edit modal (`frontend/src/pages/SourcesAdmin.tsx`)
Add a checkbox below the existing `Active` checkbox:
```
☑ robots.txt respektieren
  Wenn aktiv, werden durch robots.txt gesperrte URLs beim Discovery übersprungen.
```
Saved via the existing `useUpdateSource` hook — no API or hook changes needed.

---

## Scope

- No changes to the global `JS_RENDERING_ENABLED` config or robots.txt parsing logic
- `robot_parser` is still fetched and parsed regardless — the flag only gates whether the result is acted on
- No changes to the seed page fetch (robots.txt only affects discovered sub-URLs)
