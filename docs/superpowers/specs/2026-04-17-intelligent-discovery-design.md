# Intelligent Crawling & Discovery — Design Spec
**Date:** 2026-04-17  
**Status:** Approved

## Summary

Extend the WFM Market Intelligence crawler so that every crawl run automatically discovers and monitors relevant sub-pages starting from each Source's seed URL. Newly discovered pages are immediately analysed via the existing LLM pipeline. The system detects new, changed, and unchanged pages on subsequent runs.

---

## Scope (V1)

- Seed URL = existing `Source.url` (unchanged)
- No include/exclude patterns
- Global discovery depth (env var), default 1
- Heuristic-based link filtering (URL patterns + content signals)
- Immediate LLM analysis of new/changed discovered pages
- `DiscoveredPage` model for persistent tracking
- Admin UI: expandable discovered pages list per source

Out of scope for V1: per-source depth config, include/exclude patterns, sitemap support, crawl frequency per source, async/queue-based discovery.

---

## Data Model

### New: `DiscoveredPage`

```
discovered_pages
  id                String(36), PK, UUID
  source_id         String(36), FK → sources.id, NOT NULL
  url               String(2000), UNIQUE, NOT NULL
  title             String(500), nullable
  depth             Integer, NOT NULL  (0=seed, 1=direct, 2=deeper)
  status            Enum(new|known|changed|ignored), NOT NULL
  content_hash      String(64), nullable
  is_active         Boolean, default True
  discovered_at     DateTime, NOT NULL
  last_crawled_at   DateTime, nullable
  last_changed_at   DateTime, nullable
```

**Indexes:** `source_id`, `url` (unique), `status`

### `Source` — no changes

`Source.url` is implicitly the seed URL. No new fields required for V1.

### Config — new env var

```
DISCOVERY_DEPTH=1   # 0=seed only, 1=direct links, 2=links of links
```

Added to `config.py` via pydantic-settings.

---

## Discovery Logic (`crawler/discovery.py`)

### Entry point

```python
def discover_and_crawl(source: Source, seed_html: str, db: Session) -> Dict
```

Called from `run_crawl_source` after the seed document is saved. Receives already-fetched seed HTML — no extra request for the seed.

### Link extraction

BeautifulSoup parses `<a href>` tags from seed HTML. Links are normalised to absolute URLs and filtered to:
- Same domain as seed URL
- Not already in `discovered_pages` or `documents` tables
- Not disallowed by robots.txt (cached per domain for the duration of the run)

### Heuristic filter (A + B)

A link is considered article-like if **at least one** of the following is true:

**A — URL heuristics:**
- Contains date segment: `/2024/`, `/2024/04/`, etc.
- Path has ≥ 3 segments (e.g. `/blog/category/article-slug`)
- Path starts with known content prefixes: `/news/`, `/blog/`, `/press/`, `/insights/`, `/resources/`, `/product/`

**B — Content heuristics (evaluated after fetching the page):**
- Page contains an `<article>` HTML tag, **or**
- Word count of extracted main content > 200 words

Both heuristics are applied: URL heuristic runs first (cheap), content heuristic runs after fetch (only for URL-heuristic survivors).

### Depth behaviour

```
DISCOVERY_DEPTH=0  → only seed URL (current behaviour)
DISCOVERY_DEPTH=1  → seed → extract links → filter → crawl survivors
DISCOVERY_DEPTH=2  → + extract links from depth-1 pages → filter → crawl survivors
```

### Safety / defensive crawling

- 1 second pause between requests (`time.sleep(1)`)
- Hard limit: max 50 pages per source per run (not user-configurable in V1)
- robots.txt fetched once per domain, cached in memory for the run duration
- Standard browser User-Agent header (already used by fetcher)

---

## Change Detection

For each discovered URL, on every crawl run:

| Situation | Action |
|-----------|--------|
| URL not in `discovered_pages` | Create record, `status=new`, analyse immediately |
| URL known, hash identical | Update `last_crawled_at`, `status=known`, skip analysis |
| URL known, hash changed | Update `last_changed_at`, `status=changed`, re-analyse |
| `is_active=False` | Skip fetch entirely, set `status=ignored` |

---

## Pipeline Integration

`run_crawl_source` (in `crawler/pipeline.py`) is extended minimally:

```
run_crawl_source(source, db, analyse=True):
  1. Fetch seed URL                          [existing]
  2. Save/dedup seed Document                [existing]
  3. Analyse seed Document if new            [existing]
  4. NEW: discover_and_crawl(source, seed_html, db)
       ├─ Extract + filter links from seed HTML
       ├─ Check robots.txt
       ├─ For each candidate URL:
       │    fetch → hash → compare → set status
       │    if new/changed: save Document → analyse
       └─ Return discovery summary stats
```

The crawl router (`POST /api/crawl/run`, `POST /api/crawl/run/:source_id`) is unchanged — discovery is transparent.

---

## API Endpoints

New router: `routers/discovered_pages.py`, mounted at `/api/discovered-pages/`.

```
GET   /api/discovered-pages/?source_id={id}
      Response: list of DiscoveredPageRead
      Fields: id, url, title, depth, status, is_active,
              discovered_at, last_crawled_at, last_changed_at

PATCH /api/discovered-pages/{id}
      Body: { is_active: bool }
      Response: DiscoveredPageRead
```

No POST (pages are created automatically by discovery).  
No DELETE (deactivation via `is_active=False` is sufficient).

Auth: HTTP Basic, same as all other endpoints.

---

## Frontend

In `SourcesAdmin.tsx`, each source row gets an expandable section showing its discovered pages.

**Source row (unchanged columns + new expand toggle):**
```
URL | Label | Type | Active | Last Crawled | Actions | [▼ N discovered]
```

**Expanded discovered pages table:**
```
URL                              Status   Active  Last Changed
/blog/2024/04/ai-trends          new      ✓       17.04.2026
/blog/2024/03/product-update     changed  ✓       15.04.2026
/blog/category/all               known    —        —
```

- `new` → green badge
- `changed` → amber badge  
- `known` → grey / no badge
- `ignored` → muted row, toggle off
- Each row: `is_active` toggle (calls `PATCH /api/discovered-pages/{id}`)
- Seed URL is shown separately as "Seed" — not mixed into discovered list
- New hook: `useDiscoveredPages(sourceId)` (TanStack Query)

---

## Files to Create / Modify

**Backend — new:**
- `backend/app/models/discovered_page.py`
- `backend/app/schemas/discovered_page.py`
- `backend/app/routers/discovered_pages.py`
- `backend/app/crawler/discovery.py`
- `backend/alembic/versions/<hash>_add_discovered_pages.py`

**Backend — modified:**
- `backend/app/config.py` — add `DISCOVERY_DEPTH`
- `backend/app/crawler/pipeline.py` — call `discover_and_crawl`
- `backend/app/models/__init__.py` — register new model
- `backend/app/main.py` — mount new router

**Frontend — new:**
- `frontend/src/hooks/useDiscoveredPages.ts`

**Frontend — modified:**
- `frontend/src/pages/SourcesAdmin.tsx` — expandable discovered pages section
- `frontend/src/types/index.ts` — add `DiscoveredPage` type
