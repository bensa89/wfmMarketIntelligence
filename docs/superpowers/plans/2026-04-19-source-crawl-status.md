# Source Crawl Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add crawl status tracking (new/known/changed) to Source model and show it in the frontend with discovered pages summary.

**Architecture:** Add `crawl_status`, `content_hash`, `last_changed_at` columns to Source model (mirroring DiscoveredPage pattern). Crawler pipeline updates these fields. API returns status + aggregated sub-page summary. Frontend shows status badge and summary per source row.

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic (backend), React/TypeScript/Tailwind (frontend)

---

### Task 1: Add CrawlStatus enum and new columns to Source model

**Files:**
- Modify: `backend/app/models/source.py`

- [ ] **Step 1: Add CrawlStatus enum and new columns to Source model**

```python
# backend/app/models/source.py
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class SourceType(str, enum.Enum):
    news = "news"
    blog = "blog"
    product = "product"
    press = "press"
    jobs = "jobs"


class CrawlStatus(str, enum.Enum):
    new = "new"
    known = "known"
    changed = "changed"


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    url = Column(String(2000), unique=True, nullable=False)
    label = Column(String(255), nullable=True)
    source_type = Column(SAEnum(SourceType), nullable=False, default=SourceType.news)
    is_active = Column(Boolean, default=True)
    crawl_status = Column(
        SAEnum(CrawlStatus), nullable=False, default=CrawlStatus.new
    )
    content_hash = Column(String(64), nullable=True)
    last_changed_at = Column(DateTime, nullable=True)
    last_crawled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="sources")
    documents = relationship(
        "Document", back_populates="source", cascade="all, delete-orphan"
    )
    discovered_pages = relationship(
        "DiscoveredPage", back_populates="source", cascade="all, delete-orphan"
    )
```

- [ ] **Step 2: Commit**

```bash
rtk git add backend/app/models/source.py && rtk git commit -m "feat: add CrawlStatus enum and crawl_status/content_hash/last_changed_at columns to Source model"
```

---

### Task 2: Create Alembic migration

**Files:**
- Create: `backend/alembic/versions/<auto>_add_source_crawl_status.py`

- [ ] **Step 1: Generate the migration**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && alembic revision --autogenerate -m "add source crawl_status content_hash last_changed_at"
```

- [ ] **Step 2: Review the generated migration file** — ensure it adds the 3 columns with `crawl_status` defaulting to `'new'`, and that `crawl_status` uses the appropriate ENUM type. If PostgreSQL, the enum type must be created before the column. The autogenerate should handle this.

- [ ] **Step 3: Run the migration against the dev database**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
rtk git add backend/alembic/versions/ && rtk git commit -m "feat: add alembic migration for source crawl_status columns"
```

---

### Task 3: Update Source schemas to include new fields

**Files:**
- Modify: `backend/app/schemas/source.py`

- [ ] **Step 1: Add CrawlStatus import and new fields to SourceRead, add discovered_pages_summary**

```python
# backend/app/schemas/source.py
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


class SourceUpdate(BaseModel):
    label: Optional[str] = None
    source_type: Optional[SourceType] = None
    is_active: Optional[bool] = None


class SourceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    url: str
    label: Optional[str]
    source_type: SourceType
    is_active: bool
    crawl_status: CrawlStatus
    content_hash: Optional[str]
    last_crawled_at: Optional[datetime]
    last_changed_at: Optional[datetime]
    created_at: datetime
    discovered_pages_summary: Dict[str, int] = {}


class SourceReadWithSummary(SourceRead):
    discovered_pages_summary: Dict[str, int]
```

Note: `discovered_pages_summary` has a default empty dict so it works with `from_attributes` when not populated. The router will populate it.

- [ ] **Step 2: Commit**

```bash
rtk git add backend/app/schemas/source.py && rtk git commit -m "feat: add crawl_status/content_hash/last_changed_at/discovered_pages_summary to SourceRead schema"
```

---

### Task 4: Update sources router to populate discovered_pages_summary

**Files:**
- Modify: `backend/app/routers/sources.py`

- [ ] **Step 1: Add summary computation to list_sources and include it in source responses**

```python
# backend/app/routers/sources.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models.source import Source
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate

router = APIRouter()


def _attach_summary(source: Source, db: Session) -> dict:
    rows = (
        db.query(DiscoveredPage.status, func.count(DiscoveredPage.id))
        .filter(DiscoveredPage.source_id == source.id)
        .group_by(DiscoveredPage.status)
        .all()
    )
    summary = {status.value: count for status, count in rows}
    for s in DiscoveredPageStatus:
        if s.value not in summary:
            summary[s.value] = 0
    return summary


@router.get("", response_model=List[SourceRead])
def list_sources(company_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Source)
    if company_id:
        query = query.filter(Source.company_id == company_id)
    sources = query.all()
    sources_with_summary = []
    for source in sources:
        source_dict = SourceRead.model_validate(source).model_dump()
        source_dict["discovered_pages_summary"] = _attach_summary(source, db)
        sources_with_summary.append(source_dict)
    return sources_with_summary


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="URL already exists")
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    result = SourceRead.model_validate(source).model_dump()
    result["discovered_pages_summary"] = {}
    return result


@router.put("/{source_id}", response_model=SourceRead)
def update_source(source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    result = SourceRead.model_validate(source).model_dump()
    result["discovered_pages_summary"] = _attach_summary(source, db)
    return result


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
```

- [ ] **Step 2: Run source tests to verify nothing is broken**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_sources.py -v
```

- [ ] **Step 3: Commit**

```bash
rtk git add backend/app/routers/sources.py && rtk git commit -m "feat: add discovered_pages_summary to source API responses"
```

---

### Task 5: Update crawler pipeline to set Source crawl_status

**Files:**
- Modify: `backend/app/crawler/pipeline.py`

- [ ] **Step 1: Update run_crawl_source to set crawl_status on Source**

```python
# backend/app/crawler/pipeline.py
import logging
from typing import Callable, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.source import Source, CrawlStatus
from app.models.document import Document
from app.crawler.fetcher import fetch_url
from app.crawler.js_fetcher import fetch_url_js
from app.crawler.extractor import extract_content
from app.crawler.discovery import discover_and_crawl, _extract_internal_links
from app.config import settings

logger = logging.getLogger(__name__)

_JS_RENDER_LINK_THRESHOLD = 5


def _looks_like_js_app(html: str) -> bool:
    js_indicators = [
        '<div id="root"',
        '<div id="__next"',
        '<div id="app"',
        "ng-app",
        "data-reactroot",
        "data-reactid",
        '<script id="__NEXT_DATA__"',
        "___gatsby",
        "/gatsby.js",
        "/gatsby-static/",
        "window.___GATSBY",
    ]
    lower = html.lower()
    return any(ind.lower() in lower for ind in js_indicators)


def _needs_js_rendering(html: str, url: str) -> bool:
    links = _extract_internal_links(html, url)
    if len(links) < _JS_RENDER_LINK_THRESHOLD:
        return True
    return _looks_like_js_app(html)


def run_crawl_source(
    source: Source,
    db: Session,
    analyse: bool = True,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> Dict:
    def emit(event: dict):
        if progress_callback:
            progress_callback(event)

    result = {
        "source_id": source.id,
        "new_documents": 0,
        "skipped": 0,
        "errors": 0,
        "discovery": {},
    }

    emit({"type": "step", "source_id": source.id, "step": "fetching"})
    fetch_result = fetch_url(source.url)
    if fetch_result is None:
        result["errors"] += 1
        emit({"type": "error", "source_id": source.id, "message": "Fetch failed"})
        return result

    if settings.js_rendering_enabled and _needs_js_rendering(
        fetch_result.html, fetch_result.final_url
    ):
        emit({"type": "step", "source_id": source.id, "step": "js_rendering"})
        js_result = fetch_url_js(fetch_result.final_url)
        if js_result is not None:
            fetch_result = js_result
        else:
            logger.warning("JS rendering failed for %s, using static HTML", source.url)

    emit({"type": "step", "source_id": source.id, "step": "extracting"})
    extraction = extract_content(fetch_result.html, url=fetch_result.final_url)

    existing_by_url = (
        db.query(Document).filter(Document.url == fetch_result.final_url).first()
    )
    if existing_by_url:
        if existing_by_url.content_hash == extraction.content_hash:
            source.crawl_status = CrawlStatus.known
            result["skipped"] += 1
        else:
            existing_by_url.title = extraction.title
            existing_by_url.content_markdown = extraction.markdown
            existing_by_url.content_raw_html = fetch_result.html.replace("\x00", "")
            existing_by_url.content_hash = extraction.content_hash
            existing_by_url.crawled_at = datetime.now(timezone.utc)
            existing_by_url.is_analysed = False
            source.crawl_status = CrawlStatus.changed
            source.content_hash = extraction.content_hash
            source.last_changed_at = datetime.now(timezone.utc)
            db.commit()
            result["skipped"] += 1

            if analyse:
                from app.analyser.pipeline import analyse_document

                db.refresh(existing_by_url)
                emit({"type": "step", "source_id": source.id, "step": "analysing"})
                try:
                    analyse_document(existing_by_url, source.company_id, db)
                except Exception as e:
                    result["errors"] += 1
                    emit(
                        {
                            "type": "error",
                            "source_id": source.id,
                            "message": f"Analysis failed: {e}",
                        }
                    )
                    db.rollback()
    else:
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        source.crawl_status = CrawlStatus.new
        source.content_hash = extraction.content_hash
        db.commit()
        result["new_documents"] += 1

        if analyse:
            from app.analyser.pipeline import analyse_document

            db.refresh(doc)
            emit({"type": "step", "source_id": source.id, "step": "analysing"})
            try:
                analyse_document(doc, source.company_id, db)
            except Exception as e:
                result["errors"] += 1
                emit(
                    {
                        "type": "error",
                        "source_id": source.id,
                        "message": f"Analysis failed: {e}",
                    }
                )
                db.rollback()

    emit({"type": "step", "source_id": source.id, "step": "discovering"})
    result["discovery"] = discover_and_crawl(
        source, fetch_result.html, db, analyse=analyse
    )

    source.last_crawled_at = datetime.now(timezone.utc)
    db.commit()

    return result
```

- [ ] **Step 2: Run the crawler tests**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_crawler.py -v
```

- [ ] **Step 3: Commit**

```bash
rtk git add backend/app/crawler/pipeline.py && rtk git commit -m "feat: update pipeline to set Source crawl_status/content_hash/last_changed_at on crawl"
```

---

### Task 6: Update existing tests for source API to handle new fields

**Files:**
- Modify: `backend/tests/test_sources.py`

- [ ] **Step 1: Add assertions for crawl_status in existing source tests**

The existing `test_create_source` needs to assert that `crawl_status` is `"new"` and `discovered_pages_summary` is `{}`. The existing `test_update_source` should also check `crawl_status` is still `"new"` after update.

In `test_create_source`, after `data = response.json()`:

```python
assert data["crawl_status"] == "new"
assert data["discovered_pages_summary"] == {}
```

In `test_update_source`, after updating, add:

```python
assert response.json()["crawl_status"] == "new"
```

In `test_list_sources_empty`, the assertion stays the same (empty list).

- [ ] **Step 2: Run source tests**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_sources.py -v
```

- [ ] **Step 3: Commit**

```bash
rtk git add backend/tests/test_sources.py && rtk git commit -m "test: update source tests for crawl_status and discovered_pages_summary"
```

---

### Task 7: Add pipeline tests for crawl_status transitions

**Files:**
- Modify: `backend/tests/test_crawler.py`

- [ ] **Step 1: Add test for crawl_status=new on first crawl**

After the existing `test_run_crawl_source_saves_new_document` test:

```python
def test_run_crawl_source_sets_crawl_status_new(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, CrawlStatus

    company = Company(name="ATOSS", slug="atoss-status-new", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/status-new", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html="<html><head><title>New</title></head><body><p>Fresh content</p></body></html>",
            final_url="https://atoss.com/status-new",
            status_code=200,
        )
    )

    with patch("app.crawler.pipeline.fetch_url", mock_fetch), \
         patch("app.crawler.pipeline.discover_and_crawl", return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0}):
        run_crawl_source(source, db_session, analyse=False)

    db_session.refresh(source)
    assert source.crawl_status == CrawlStatus.new
    assert source.content_hash is not None
```

- [ ] **Step 2: Add test for crawl_status=known on re-crawl with same content**

```python
def test_run_crawl_source_sets_crawl_status_known_on_same_content(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, CrawlStatus

    company = Company(name="ATOSS", slug="atoss-status-known", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/status-known", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    html = "<html><head><title>Same</title></head><body><p>Same content</p></body></html>"
    mock_fetch = MagicMock(
        return_value=MagicMock(html=html, final_url="https://atoss.com/status-known", status_code=200)
    )

    with patch("app.crawler.pipeline.fetch_url", mock_fetch), \
         patch("app.crawler.pipeline.discover_and_crawl", return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0}):
        run_crawl_source(source, db_session, analyse=False)
        run_crawl_source(source, db_session, analyse=False)

    db_session.refresh(source)
    assert source.crawl_status == CrawlStatus.known
```

- [ ] **Step 3: Add test for crawl_status=changed on content change**

```python
def test_run_crawl_source_sets_crawl_status_changed_on_content_change(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType, CrawlStatus

    company = Company(name="ATOSS", slug="atoss-status-changed", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/status-changed", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    html_v1 = "<html><head><title>V1</title></head><body><p>Version 1</p></body></html>"
    html_v2 = "<html><head><title>V2</title></head><body><p>Version 2</p></body></html>"
    mock_fetch_v1 = MagicMock(
        return_value=MagicMock(html=html_v1, final_url="https://atoss.com/status-changed", status_code=200)
    )
    mock_fetch_v2 = MagicMock(
        return_value=MagicMock(html=html_v2, final_url="https://atoss.com/status-changed", status_code=200)
    )

    with patch("app.crawler.pipeline.fetch_url", mock_fetch_v1), \
         patch("app.crawler.pipeline.discover_and_crawl", return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0}):
        run_crawl_source(source, db_session, analyse=False)

    with patch("app.crawler.pipeline.fetch_url", mock_fetch_v2), \
         patch("app.crawler.pipeline.discover_and_crawl", return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0}):
        run_crawl_source(source, db_session, analyse=False)

    db_session.refresh(source)
    assert source.crawl_status == CrawlStatus.changed
    assert source.last_changed_at is not None
```

- [ ] **Step 4: Run all crawler tests**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_crawler.py -v
```

- [ ] **Step 5: Commit**

```bash
rtk git add backend/tests/test_crawler.py && rtk git commit -m "test: add crawl_status transition tests (new/known/changed)"
```

---

### Task 8: Update frontend types and Source interface

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add CrawlStatus type and update Source interface**

In the types file, add the `CrawlStatus` type and update the `Source` interface:

```typescript
export type CrawlStatus = 'new' | 'known' | 'changed';

export interface Source {
  id: string;
  company_id: string;
  url: string;
  label: string | null;
  source_type: SourceType;
  is_active: boolean;
  crawl_status: CrawlStatus;
  content_hash: string | null;
  last_crawled_at: string | null;
  last_changed_at: string | null;
  created_at: string;
  discovered_pages_summary: Record<string, number>;
}
```

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/src/types/index.ts && rtk git commit -m "feat: add CrawlStatus type and discovery summary to Source interface"
```

---

### Task 9: Add status badge and discovered pages summary to SourcesAdmin

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Add crawlStatusBadge helper and DiscoveredPagesSummary component to SourcesAdmin**

Add a `crawlStatusBadge` helper function near the top of the file (after imports, before `DiscoveredPagesSection`):

```tsx
function crawlStatusBadge(status: CrawlStatus) {
  const styles: Record<CrawlStatus, string> = {
    new: 'bg-signal-high/20 text-signal-high',
    changed: 'bg-yellow-500/20 text-yellow-400',
    known: 'bg-dark-bg text-dark-muted',
  };
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${styles[status] ?? ''}`}>
      {status}
    </span>
  );
}

function DiscoveredPagesSummary({ summary }: { summary: Record<string, number> }) {
  const parts: string[] = [];
  if ((summary['new'] ?? 0) > 0) parts.push(`${summary['new']} new`);
  if ((summary['changed'] ?? 0) > 0) parts.push(`${summary['changed']} changed`);
  if ((summary['known'] ?? 0) > 0) parts.push(`${summary['known']} known`);
  if (parts.length === 0) return null;
  return <span className="text-xs text-dark-muted">{parts.join(' · ')}</span>;
}
```

- [ ] **Step 2: Add imports for CrawlStatus type**

Update the imports line in SourcesAdmin.tsx to include `CrawlStatus`:

```tsx
import type { CompanyType, SourceType, Source, DiscoveredPage, Company, CrawlStatus } from '../types';
```

- [ ] **Step 3: Add status badge and summary to each source table row**

Find the source table row rendering. In each source row, add the status badge after the `last_crawled_at` column and add a summary line below it. Look for where `source.last_crawled_at` is displayed and add `crawlStatusBadge(source.crawl_status)` next to it. Beneath the row or in a subtitle area, add `<DiscoveredPagesSummary summary={source.discovered_pages_summary} />`.

The exact location depends on the current table structure. Find the cell showing `last_crawled_at` and append the badge there. Add the summary in a row below or as a small text under the source URL.

- [ ] **Step 4: Run frontend build to verify no type errors**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npm run build 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/pages/SourcesAdmin.tsx && rtk git commit -m "feat: add crawl status badge and discovered pages summary to SourcesAdmin"
```

---

### Task 10: Run full test suite and verify

- [ ] **Step 1: Run all backend tests**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/ -v
```

- [ ] **Step 2: Run frontend build**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npm run build
```

- [ ] **Step 3: Verify all tests pass and build succeeds. If any failures, fix them.**