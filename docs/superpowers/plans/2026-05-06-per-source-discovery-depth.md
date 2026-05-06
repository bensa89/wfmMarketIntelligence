# Per-Source Discovery Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional per-source `discovery_depth` field that overrides the global `DISCOVERY_DEPTH` env setting, configurable from the source edit modal in the UI.

**Architecture:** Add a nullable integer column to `sources`; `discovery.py` resolves `effective_depth = source.discovery_depth ?? settings.discovery_depth`; the edit modal exposes a number input (empty = global default, 0 = disable, 1–5 = override).

**Tech Stack:** Python/SQLAlchemy/Alembic, FastAPI/Pydantic v2, React 18/TypeScript

---

## File Map

| File | Change |
|------|--------|
| `backend/alembic/versions/add_discovery_depth_to_sources.py` | **Create** — migration adding nullable integer column |
| `backend/app/models/source.py` | **Modify** — add `discovery_depth` column |
| `backend/app/schemas/source.py` | **Modify** — add field to `SourceCreate`, `SourceUpdate`, `SourceRead` |
| `backend/app/crawler/discovery.py` | **Modify** — use `effective_depth` instead of `settings.discovery_depth` |
| `backend/tests/test_sources.py` | **Modify** — tests for new field in API |
| `backend/tests/test_discovery.py` | **Modify** — tests for per-source depth override |
| `frontend/src/types/index.ts` | **Modify** — add field to `Source`, `SourceUpdate` |
| `frontend/src/pages/SourcesAdmin.tsx` | **Modify** — edit modal field + state |

---

### Task 1: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/add_discovery_depth_to_sources.py`

- [ ] **Step 1: Create the migration file**

```python
# backend/alembic/versions/add_discovery_depth_to_sources.py
"""add discovery_depth to sources

Revision ID: add_discovery_depth_to_sources
Revises: 7c1829582bbd
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_discovery_depth_to_sources'
down_revision: Union[str, Sequence[str], None] = '7c1829582bbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sources',
        sa.Column('discovery_depth', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('sources', 'discovery_depth')
```

> **Note:** `down_revision` must match the last migration. Verify with:
> ```bash
> cd backend && alembic history --verbose | head -5
> ```
> Update `down_revision` to the actual latest revision ID shown.

- [ ] **Step 2: Apply migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Expected: `Running upgrade ... -> add_discovery_depth_to_sources, add discovery_depth to sources`

- [ ] **Step 3: Commit**

```bash
rtk git add backend/alembic/versions/add_discovery_depth_to_sources.py
rtk git commit -m "feat: migration — add discovery_depth column to sources"
```

---

### Task 2: SQLAlchemy Model

**Files:**
- Modify: `backend/app/models/source.py`

- [ ] **Step 1: Add column to model**

In `backend/app/models/source.py`, add after the `respect_robots_txt` line:

```python
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SAEnum, Integer
```

(Replace the existing import — add `Integer` to it.)

Then add the column after `respect_robots_txt`:

```python
    respect_robots_txt = Column(Boolean, default=True, nullable=False)
    discovery_depth = Column(Integer, nullable=True, default=None)
```

- [ ] **Step 2: Commit**

```bash
rtk git add backend/app/models/source.py
rtk git commit -m "feat: add discovery_depth to Source model"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/source.py`

- [ ] **Step 1: Add field to all three schemas**

Replace the full content of `backend/app/schemas/source.py`:

```python
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
from app.models.source import SourceType, CrawlStatus


class SourceCreate(BaseModel):
    company_id: str
    url: str
    label: Optional[str] = None
    source_type: SourceType = SourceType.news
    is_active: bool = True
    respect_robots_txt: bool = True
    discovery_depth: Optional[int] = None


class SourceUpdate(BaseModel):
    label: Optional[str] = None
    source_type: Optional[SourceType] = None
    is_active: Optional[bool] = None
    respect_robots_txt: Optional[bool] = None
    discovery_depth: Optional[int] = None


class SourceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    url: str
    label: Optional[str]
    source_type: SourceType
    is_active: bool
    respect_robots_txt: bool
    discovery_depth: Optional[int]
    crawl_status: CrawlStatus
    content_hash: Optional[str]
    last_crawled_at: Optional[datetime]
    last_changed_at: Optional[datetime]
    created_at: datetime
    discovered_pages_summary: Dict[str, int] = {}
```

- [ ] **Step 2: Write failing tests**

Add to `backend/tests/test_sources.py`:

```python
def test_create_source_default_discovery_depth_is_null(client, company):
    r = client.post(
        "/api/sources",
        json={"company_id": company["id"], "url": "https://atoss.com/depth-default", "source_type": "news"},
    )
    assert r.status_code == 201
    assert r.json()["discovery_depth"] is None


def test_update_source_discovery_depth(client, company):
    r = client.post(
        "/api/sources",
        json={"company_id": company["id"], "url": "https://atoss.com/depth-update", "source_type": "news"},
    )
    source_id = r.json()["id"]
    r2 = client.put(f"/api/sources/{source_id}", json={"discovery_depth": 3})
    assert r2.status_code == 200
    assert r2.json()["discovery_depth"] == 3


def test_update_source_discovery_depth_to_null(client, company):
    r = client.post(
        "/api/sources",
        json={"company_id": company["id"], "url": "https://atoss.com/depth-null", "source_type": "news", "discovery_depth": 2},
    )
    source_id = r.json()["id"]
    r2 = client.put(f"/api/sources/{source_id}", json={"discovery_depth": None})
    assert r2.status_code == 200
    assert r2.json()["discovery_depth"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_sources.py::test_create_source_default_discovery_depth_is_null tests/test_sources.py::test_update_source_discovery_depth tests/test_sources.py::test_update_source_discovery_depth_to_null -v
```

Expected: FAIL — `discovery_depth` not in response yet (or KeyError).

- [ ] **Step 4: Run tests to verify they pass after schema change**

```bash
cd backend && python -m pytest tests/test_sources.py::test_create_source_default_discovery_depth_is_null tests/test_sources.py::test_update_source_discovery_depth tests/test_sources.py::test_update_source_discovery_depth_to_null -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/schemas/source.py backend/tests/test_sources.py
rtk git commit -m "feat: add discovery_depth to source schemas + API tests"
```

---

### Task 4: Discovery Pipeline

**Files:**
- Modify: `backend/app/crawler/discovery.py`

- [ ] **Step 1: Write failing tests for per-source override**

Add to `backend/tests/test_discovery.py`:

```python
def test_discover_uses_source_depth_override(db_session, monkeypatch):
    """Source with discovery_depth=0 skips discovery even if global depth > 0."""
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 2)
    source = _make_source(db_session, slug="disc-src-override")
    source.discovery_depth = 0
    db_session.commit()

    result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)
    assert result["discovered"] == 0
    assert db_session.query(DiscoveredPage).count() == 0


def test_discover_falls_back_to_global_depth_when_source_depth_is_none(db_session, monkeypatch):
    """Source with discovery_depth=None uses global settings.discovery_depth=0 → skips."""
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 0)
    source = _make_source(db_session, slug="disc-src-fallback")
    source.discovery_depth = None
    db_session.commit()

    result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)
    assert result["discovered"] == 0
    assert db_session.query(DiscoveredPage).count() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_discovery.py::test_discover_uses_source_depth_override tests/test_discovery.py::test_discover_falls_back_to_global_depth_when_source_depth_is_none -v
```

Expected: FAIL — current code ignores `source.discovery_depth`.

- [ ] **Step 3: Update `discover_and_crawl` to use effective depth**

In `backend/app/crawler/discovery.py`, at the top of `discover_and_crawl` (after the function signature), replace:

```python
    if settings.discovery_depth == 0:
        logger.info(
            "Discovery disabled (discovery_depth=0), skipping for source %s", source.url
        )
        return {"discovered": 0, "new": 0, "changed": 0, "known": 0}
```

with:

```python
    effective_depth = source.discovery_depth if source.discovery_depth is not None else settings.discovery_depth
    if effective_depth == 0:
        logger.info(
            "Discovery disabled (discovery_depth=0), skipping for source %s", source.url
        )
        return {"discovered": 0, "new": 0, "changed": 0, "known": 0}
```

- [ ] **Step 4: Replace remaining `settings.discovery_depth` references with `effective_depth` in that function**

Still in `discover_and_crawl`, replace these three occurrences:

Line ~185 (log message):
```python
        "Discovery for source %s: %d known inactive pages, discovery_depth=%d",
        source.url,
        len(known_inactive),
        settings.discovery_depth,
```
→
```python
        "Discovery for source %s: %d known inactive pages, effective_depth=%d",
        source.url,
        len(known_inactive),
        effective_depth,
```

Line ~237 (depth guard):
```python
        if depth > settings.discovery_depth:
            logger.debug(
                "Skipping URL (depth %d > discovery_depth %d): %s",
                depth,
                settings.discovery_depth,
```
→
```python
        if depth > effective_depth:
            logger.debug(
                "Skipping URL (depth %d > effective_depth %d): %s",
                depth,
                effective_depth,
```

Line ~360 (sub-link enqueue guard):
```python
        if depth < settings.discovery_depth:
```
→
```python
        if depth < effective_depth:
```

- [ ] **Step 5: Run failing tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_discovery.py::test_discover_uses_source_depth_override tests/test_discovery.py::test_discover_falls_back_to_global_depth_when_source_depth_is_none -v
```

Expected: PASS

- [ ] **Step 6: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
rtk git add backend/app/crawler/discovery.py backend/tests/test_discovery.py
rtk git commit -m "feat: discovery pipeline respects per-source discovery_depth override"
```

---

### Task 5: Frontend Types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add `discovery_depth` to `Source` and `SourceUpdate`**

In `frontend/src/types/index.ts`, update the `Source` interface:

```typescript
export interface Source {
  id: string;
  company_id: string;
  url: string;
  label: string | null;
  source_type: SourceType;
  is_active: boolean;
  respect_robots_txt: boolean;
  discovery_depth: number | null;
  crawl_status: CrawlStatus;
  content_hash: string | null;
  last_crawled_at: string | null;
  last_changed_at: string | null;
  created_at: string;
  discovered_pages_summary: Record<string, number>;
}
```

Update `SourceUpdate`:

```typescript
export interface SourceUpdate {
  label?: string | null;
  source_type?: SourceType;
  is_active?: boolean;
  respect_robots_txt?: boolean;
  discovery_depth?: number | null;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/types/index.ts
rtk git commit -m "feat: add discovery_depth to Source TypeScript interfaces"
```

---

### Task 6: Frontend Edit Modal

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Add state variable**

In `SourcesAdmin`, add after `editRespectRobots` state (around line 173):

```typescript
  const [editDiscoveryDepth, setEditDiscoveryDepth] = useState<number | null>(null);
```

- [ ] **Step 2: Populate state in `openEditModal`**

In `openEditModal`, add after `setEditRespectRobots(source.respect_robots_txt)`:

```typescript
    setEditDiscoveryDepth(source.discovery_depth);
```

- [ ] **Step 3: Reset state in `closeEditModal`**

In `closeEditModal`, add after `setEditRespectRobots(true)`:

```typescript
    setEditDiscoveryDepth(null);
```

- [ ] **Step 4: Include in `handleSaveEdit` updates**

In `handleSaveEdit`, update the `updates` type and include `discovery_depth`:

```typescript
    const updates: {
      url?: string;
      label?: string | null;
      source_type?: SourceType;
      respect_robots_txt?: boolean;
      discovery_depth?: number | null;
    } = {};
    if (editUrl !== editingSource.url) updates.url = editUrl;
    if (editLabel !== (editingSource.label || '')) updates.label = editLabel || null;
    if (editType !== editingSource.source_type) updates.source_type = editType;
    if (editRespectRobots !== editingSource.respect_robots_txt) updates.respect_robots_txt = editRespectRobots;
    if (editDiscoveryDepth !== editingSource.discovery_depth) updates.discovery_depth = editDiscoveryDepth;
```

- [ ] **Step 5: Add field to edit modal form**

In the edit modal form, add a new field block after the `robots.txt` checkbox block (before the `<div className="flex gap-2 pt-2">` submit buttons div):

```tsx
              <div>
                <label className="block text-sm text-ink-muted mb-1">Discovery Depth</label>
                <input
                  type="number"
                  min={0}
                  max={5}
                  step={1}
                  value={editDiscoveryDepth ?? ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setEditDiscoveryDepth(val === '' ? null : parseInt(val, 10));
                  }}
                  className="input-field w-full"
                  placeholder="Global default"
                />
                <p className="text-xs text-ink-muted mt-1">
                  0 = Discovery deaktiviert · leer = globaler Standard · 1–5 = Override
                </p>
              </div>
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
rtk git add frontend/src/pages/SourcesAdmin.tsx
rtk git commit -m "feat: add discovery depth field to source edit modal"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `null` = global default (Task 4, effective_depth logic)
- ✅ DB migration (Task 1)
- ✅ Model column (Task 2)
- ✅ Schema fields on Create/Update/Read (Task 3)
- ✅ Discovery pipeline override (Task 4)
- ✅ TypeScript types (Task 5)
- ✅ Edit modal field with empty=null, 0=disable, 1–5=override (Task 6)
- ✅ No changes to "Add Source" form (not in any task — correctly omitted)
- ✅ `_MAX_PAGES_PER_RUN` unchanged

**Type consistency:**
- `discovery_depth: Optional[int]` in Python, `number | null` in TypeScript — consistent throughout
- `editDiscoveryDepth` state name used consistently across openEditModal / closeEditModal / handleSaveEdit / JSX

**No placeholders:** All code steps contain complete, runnable code.
