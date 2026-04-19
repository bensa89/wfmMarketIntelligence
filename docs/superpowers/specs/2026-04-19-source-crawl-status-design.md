# Source Crawl Status Design

## Problem

Sources lack change-tracking that DiscoveredPages already have. When re-crawling a Source URL:
- There's no `new`/`known`/`changed` status on the Source itself
- Users can't see at a glance whether a Source or its sub-pages have changes
- They must expand every Source to check DiscoveredPage statuses individually

## Solution

Add `crawl_status`, `content_hash`, and `last_changed_at` to the `Source` model, mirroring the `DiscoveredPage` pattern. Add a computed `discovered_pages_summary` to the API response. Update the frontend to show status badges and summaries.

## Data Model Changes

### Source model — 3 new columns

| Column | Type | Default | Description |
|---|---|---|---|
| `crawl_status` | Enum(`new`/`known`/`changed`) | `new` | Crawl status of the source URL |
| `content_hash` | String(64), nullable | null | SHA-256 of extracted markdown |
| `last_changed_at` | DateTime, nullable | null | When content last changed |

The `CrawlStatus` enum reuses `new`/`known` from `DiscoveredPageStatus` but drops `ignored` (not applicable to Sources). Defined as a separate enum type.

### No changes to Document or DiscoveredPage models.

## API Changes

### SourceRead schema — extended

```python
class SourceRead(BaseModel):
    # existing fields...
    crawl_status: CrawlStatus
    content_hash: Optional[str]
    last_changed_at: Optional[datetime]
    discovered_pages_summary: Dict[str, int]  # {"new": 2, "changed": 1, "known": 5}
```

`discovered_pages_summary` is computed from DiscoveredPage records per source via a COUNT GROUP BY status query. It is not stored in the database.

### SourceCreate / SourceUpdate — no changes
Sources are created with `crawl_status = new` by default. The crawler updates it.

## Crawler Pipeline Changes

### pipeline.py — run_crawl_source()

Current logic: check Document by content_hash, skip or insert.

New logic:
1. Check if Source already has a `content_hash`
2. No hash (first crawl) → set `crawl_status = new`, store `content_hash`
3. Same hash → set `crawl_status = known`
4. Different hash → set `crawl_status = changed`, update `content_hash` and `last_changed_at`
5. The Document dedup/update logic (from the previous fix) remains unchanged

### discovery.py — no changes
DiscoveredPage status logic already works correctly.

## Frontend Changes

### SourcesAdmin table

Each Source row gets:
- **Status badge** next to "last crawled": green for `new`, yellow for `changed`, gray for `known`
- **Sub-page summary** below the badge: e.g. `2 new · 1 changed · 5 known`

The DiscoveredPagesSection expandable section remains as-is.

## Migration

Alembic migration adding:
- `crawl_status` column as ENUM with default `'new'`
- `content_hash` column as VARCHAR(64) nullable
- `last_changed_at` column as DATETIME nullable

Existing sources get `crawl_status = 'new'` (will be updated on next crawl).

## Crawl Status Lifecycle

```
Source created → crawl_status = new
  ↓ crawl
Same hash as before → crawl_status = known
Different hash → crawl_status = changed, last_changed_at = now
  ↓ next crawl
Same hash → known | Different hash → changed
```

Status persists between crawls. It only changes when the crawler runs.