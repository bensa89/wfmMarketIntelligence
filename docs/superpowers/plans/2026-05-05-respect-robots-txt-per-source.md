# Per-Source `respect_robots_txt` Toggle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-source boolean flag `respect_robots_txt` (default `True`) that controls whether the discovery crawler honours `robots.txt` restrictions, with a Shield icon indicator in the source table and a checkbox in the edit modal.

**Architecture:** Field added to the `Source` SQLAlchemy model and exposed through Pydantic schemas and the existing REST endpoint. The single `if not robot_parser.can_fetch()` check in `discovery.py` is gated by the flag. Frontend adds the field to the `Source` TypeScript interface and wires it into `SourcesAdmin.tsx`.

**Tech Stack:** Python/SQLAlchemy, Alembic, FastAPI/Pydantic, React 18 + TypeScript, Lucide icons

---

## File Map

| File | Change |
|---|---|
| `backend/app/models/source.py` | Add `respect_robots_txt` column |
| `backend/alembic/versions/add_respect_robots_txt.py` | New migration |
| `backend/app/schemas/source.py` | Add field to Create/Update/Read schemas |
| `backend/app/crawler/discovery.py` | Gate robots check on `source.respect_robots_txt` |
| `backend/tests/test_sources.py` | Test field in create/read/update |
| `backend/tests/test_discovery.py` | Test bypass when `respect_robots_txt=False` |
| `frontend/src/types/index.ts` | Add field to `Source`, `SourceCreate`, `SourceUpdate` |
| `frontend/src/pages/SourcesAdmin.tsx` | Shield column + edit modal checkbox |

---

## Task 1: Backend model + migration

**Files:**
- Modify: `backend/app/models/source.py`
- Create: `backend/alembic/versions/add_respect_robots_txt.py`

- [ ] **Step 1: Add column to Source model**

In `backend/app/models/source.py`, add after the `is_active` line:

```python
respect_robots_txt = Column(Boolean, default=True, nullable=False)
```

Full updated class fields section (just the column block, not the whole file):
```python
id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
company_id = Column(
    String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
)
url = Column(String(2000), unique=True, nullable=False)
label = Column(String(255), nullable=True)
source_type = Column(SAEnum(SourceType), nullable=False, default=SourceType.news)
is_active = Column(Boolean, default=True)
respect_robots_txt = Column(Boolean, default=True, nullable=False)
crawl_status = Column(SAEnum(CrawlStatus), nullable=False, default=CrawlStatus.new)
content_hash = Column(String(64), nullable=True)
last_changed_at = Column(DateTime, nullable=True)
last_crawled_at = Column(DateTime, nullable=True)
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Create Alembic migration**

Create `backend/alembic/versions/add_respect_robots_txt.py`:

```python
"""add_respect_robots_txt

Revision ID: add_respect_robots_txt
Revises: add_crawl_source_timing
Create Date: 2026-05-05 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_respect_robots_txt'
down_revision: Union[str, Sequence[str], None] = 'add_crawl_source_timing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sources',
        sa.Column('respect_robots_txt', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    op.drop_column('sources', 'respect_robots_txt')
```

- [ ] **Step 3: Apply migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Expected output ends with: `Running upgrade add_crawl_source_timing -> add_respect_robots_txt`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/source.py backend/alembic/versions/add_respect_robots_txt.py
git commit -m "feat: add respect_robots_txt column to sources"
```

---

## Task 2: Pydantic schemas

**Files:**
- Modify: `backend/app/schemas/source.py`

- [ ] **Step 1: Update all three schemas**

In `backend/app/schemas/source.py`:

```python
class SourceCreate(BaseModel):
    company_id: str
    url: str
    label: Optional[str] = None
    source_type: SourceType = SourceType.news
    is_active: bool = True
    respect_robots_txt: bool = True


class SourceUpdate(BaseModel):
    label: Optional[str] = None
    source_type: Optional[SourceType] = None
    is_active: Optional[bool] = None
    respect_robots_txt: Optional[bool] = None


class SourceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    url: str
    label: Optional[str]
    source_type: SourceType
    is_active: bool
    respect_robots_txt: bool
    crawl_status: CrawlStatus
    content_hash: Optional[str]
    last_crawled_at: Optional[datetime]
    last_changed_at: Optional[datetime]
    created_at: datetime
    discovered_pages_summary: Dict[str, int] = {}
```

- [ ] **Step 2: Write failing tests in test_sources.py**

Add to `backend/tests/test_sources.py` (uses the existing `company` fixture already defined in that file):

```python
def test_source_respect_robots_defaults_true(client, company):
    response = client.post("/api/sources", json={
        "company_id": company["id"],
        "url": "https://robots-default.example.com",
        "source_type": "news",
    })
    assert response.status_code == 201
    assert response.json()["respect_robots_txt"] is True


def test_source_respect_robots_can_be_set_false_and_updated(client, company):
    response = client.post("/api/sources", json={
        "company_id": company["id"],
        "url": "https://robots-false.example.com",
        "source_type": "news",
        "respect_robots_txt": False,
    })
    assert response.status_code == 201
    assert response.json()["respect_robots_txt"] is False
    source_id = response.json()["id"]

    patch_resp = client.put(f"/api/sources/{source_id}", json={"respect_robots_txt": True})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["respect_robots_txt"] is True
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_sources.py::test_source_respect_robots_defaults_true tests/test_sources.py::test_source_respect_robots_can_be_set_false -v
```

Expected: FAIL (field not in schema yet — but actually schema is already updated, so these should pass after schema update). If they pass, move on.

- [ ] **Step 4: Run all source tests**

```bash
cd backend && python -m pytest tests/test_sources.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/source.py backend/tests/test_sources.py
git commit -m "feat: expose respect_robots_txt in source schemas"
```

---

## Task 3: Crawler — gate robots check on flag

**Files:**
- Modify: `backend/app/crawler/discovery.py`
- Modify: `backend/tests/test_discovery.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_discovery.py` after the existing `test_discover_skips_robots_disallowed` test:

```python
def test_discover_ignores_robots_when_disabled(db_session, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-robots-off")
    source.respect_robots_txt = False
    db_session.commit()

    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = False  # robots.txt blocks everything

    with (
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
        patch("app.crawler.discovery.fetch_url") as mock_fetch,
        patch("app.crawler.discovery.extract_content") as mock_extract,
    ):
        mock_fetch.return_value = MagicMock(
            html=ARTICLE_HTML, final_url="https://example.com/blog/2024/04/article-one"
        )
        mock_extract.return_value = MagicMock(
            title="Article", markdown="content", content_hash="abc123", published_at=None
        )
        result = discover_and_crawl(source, SEED_HTML, db_session, analyse=False)

    assert result["discovered"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_discovery.py::test_discover_ignores_robots_when_disabled -v
```

Expected: FAIL — discovered == 0 because robots check still blocks.

- [ ] **Step 3: Update the robots check in discovery.py**

In `backend/app/crawler/discovery.py`, find the line (around line 246):
```python
        if not robot_parser.can_fetch("*", url):
            logger.info("Blocked by robots.txt: %s", url)
            continue
```

Replace with:
```python
        if source.respect_robots_txt and not robot_parser.can_fetch("*", url):
            logger.info("Blocked by robots.txt: %s", url)
            continue
```

- [ ] **Step 4: Run new test**

```bash
cd backend && python -m pytest tests/test_discovery.py::test_discover_ignores_robots_when_disabled -v
```

Expected: PASS

- [ ] **Step 5: Run full discovery test suite**

```bash
cd backend && python -m pytest tests/test_discovery.py -v
```

Expected: all pass (existing `test_discover_skips_robots_disallowed` still passes because `_make_source` creates sources with default `respect_robots_txt=True`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/crawler/discovery.py backend/tests/test_discovery.py
git commit -m "feat: gate robots.txt check on source.respect_robots_txt"
```

---

## Task 4: Frontend types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add field to Source, SourceCreate, SourceUpdate**

In `frontend/src/types/index.ts`, update the three interfaces:

```typescript
export interface Source {
  id: string;
  company_id: string;
  url: string;
  label: string | null;
  source_type: SourceType;
  is_active: boolean;
  respect_robots_txt: boolean;
  crawl_status: CrawlStatus;
  content_hash: string | null;
  last_crawled_at: string | null;
  last_changed_at: string | null;
  created_at: string;
  discovered_pages_summary: Record<string, number>;
}

export interface SourceCreate {
  company_id: string;
  url: string;
  label?: string | null;
  source_type: SourceType;
  is_active?: boolean;
  respect_robots_txt?: boolean;
}

export interface SourceUpdate {
  label?: string | null;
  source_type?: SourceType;
  is_active?: boolean;
  respect_robots_txt?: boolean;
}
```

- [ ] **Step 2: Check TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add respect_robots_txt to Source TypeScript interfaces"
```

---

## Task 5: Frontend UI — Shield indicator + edit modal checkbox

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Add Shield icons to imports**

At the top of `SourcesAdmin.tsx`, add `Shield` and `ShieldOff` to the lucide-react import:

```typescript
import { Plus, Play, Trash2, Edit2, X, ChevronDown, ChevronRight, Shield, ShieldOff } from 'lucide-react';
```

- [ ] **Step 2: Add Shield indicator column header**

In the `<thead>` of the sources table, add a new `<th>` after the Type column:

```tsx
<th className="text-left py-2 text-ink-muted font-medium">Robots</th>
```

- [ ] **Step 3: Add Shield indicator cell in each source row**

In the `<tbody>` source row, add a new `<td>` after the Type cell:

```tsx
<td className="py-2">
  {source.respect_robots_txt ? (
    <span title="robots.txt wird respektiert">
      <Shield size={14} className="text-signal-high" />
    </span>
  ) : (
    <span title="robots.txt wird ignoriert">
      <ShieldOff size={14} className="text-ink-muted" />
    </span>
  )}
</td>
```

Also add `colSpan={8}` (was 7) to the "No sources configured" fallback row and the `DiscoveredPagesSection` row.

- [ ] **Step 4: Add edit state for respect_robots_txt**

In the component state block, add:

```typescript
const [editRespectRobots, setEditRespectRobots] = useState<boolean>(true);
```

- [ ] **Step 5: Populate state in openEditModal**

In the `openEditModal` function, add:

```typescript
function openEditModal(source: Source) {
  setEditingSource(source);
  setEditUrl(source.url);
  setEditLabel(source.label || '');
  setEditType(source.source_type);
  setEditRespectRobots(source.respect_robots_txt);
}
```

- [ ] **Step 6: Reset state in closeEditModal**

In `closeEditModal`, add:

```typescript
function closeEditModal() {
  setEditingSource(null);
  setEditUrl('');
  setEditLabel('');
  setEditType('news');
  setEditRespectRobots(true);
}
```

- [ ] **Step 7: Include field in handleSaveEdit**

In `handleSaveEdit`, extend the `updates` object type and check:

```typescript
const updates: { url?: string; label?: string | null; source_type?: SourceType; respect_robots_txt?: boolean } = {};
if (editUrl !== editingSource.url) updates.url = editUrl;
if (editLabel !== (editingSource.label || '')) updates.label = editLabel || null;
if (editType !== editingSource.source_type) updates.source_type = editType;
if (editRespectRobots !== editingSource.respect_robots_txt) updates.respect_robots_txt = editRespectRobots;
```

- [ ] **Step 8: Add checkbox to edit modal**

In the edit modal form, after the existing `Active` checkbox block, add:

```tsx
<div className="flex items-center gap-2">
  <input
    type="checkbox"
    checked={editRespectRobots}
    onChange={(e) => setEditRespectRobots(e.target.checked)}
    id="edit-respect-robots"
    className="accent-accent-blue"
  />
  <label htmlFor="edit-respect-robots" className="text-sm text-ink cursor-pointer">
    robots.txt respektieren
  </label>
  <span className="text-xs text-ink-muted">
    — wenn aktiv, werden gesperrte URLs beim Discovery übersprungen
  </span>
</div>
```

- [ ] **Step 9: TypeScript check + dev server smoke test**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors. Then open the Sources Admin page in the browser, verify:
- Each source row shows a Shield or ShieldOff icon in the Robots column
- Edit modal shows the checkbox, checked by default
- Toggling and saving persists the value (check network tab for the PUT request)

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/SourcesAdmin.tsx
git commit -m "feat: add robots.txt shield indicator and edit toggle to SourcesAdmin"
```

---

## Task 6: Full test run + final commit

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all 51+ tests pass.

- [ ] **Step 2: Verify gfos.com source works**

In the UI, find the gfos.com WFM source, open Edit, uncheck "robots.txt respektieren", save. Trigger a crawl and confirm discovery now finds subpages (ShieldOff icon shown in row).
