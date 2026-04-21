# Dashboard Briefing & Discovered Page Auto-Ignore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an LLM-generated intelligence briefing to the dashboard and automatically ignore discovered pages whose signals are all below 0.3 relevance.

**Architecture:** Feature 1 adds a `CrawlBriefing` model persisted after each crawl and on-demand, displayed in a new `BriefingPanel` on the dashboard. Feature 2 adds a `last_signal_relevance` field to `DiscoveredPage` and a post-analysis hook in `discovery.py` that auto-ignores pages with uniformly low-relevance signals.

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic (backend), React/TypeScript/Vite (frontend), existing `call_llm` abstraction (Anthropic/Ollama).

---

### Task 1: CrawlBriefing model + migration

**Files:**
- Create: `backend/app/models/crawl_briefing.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the model**

```python
# backend/app/models/crawl_briefing.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class CrawlBriefing(Base):
    __tablename__ = "crawl_briefings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    crawl_run_id = Column(String(36), ForeignKey("crawl_runs.id"), nullable=True)
    content = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Export from models `__init__.py`**

Add to `backend/app/models/__init__.py`:
```python
from app.models.crawl_briefing import CrawlBriefing
```
And add `"CrawlBriefing"` to the `__all__` list.

- [ ] **Step 3: Generate and run migration**

```bash
cd backend && alembic revision --autogenerate -m "add crawl briefings"
alembic upgrade head
```

Expected: migration file created, table `crawl_briefings` exists.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/crawl_briefing.py backend/app/models/__init__.py backend/alembic/versions/
git commit -m "feat: add CrawlBriefing model and migration"
```

---

### Task 2: CrawlBriefing schema + briefing generation logic

**Files:**
- Create: `backend/app/schemas/crawl_briefing.py`
- Modify: `backend/app/analyser/client.py` (add `max_tokens` param)
- Create: `backend/app/analyser/briefing.py`

- [ ] **Step 1: Create Pydantic schemas**

```python
# backend/app/schemas/crawl_briefing.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CrawlBriefingRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    crawl_run_id: Optional[str]
    content: str
    generated_at: datetime


class CrawlBriefingCreate(BaseModel):
    crawl_run_id: Optional[str] = None
```

- [ ] **Step 2: Add `max_tokens` parameter to `call_llm`**

In `backend/app/analyser/client.py`, update all three functions:

```python
def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    if settings.llm_provider == "ollama":
        return _call_ollama(prompt)
    return _call_claude(prompt, max_tokens=max_tokens)


def _call_claude(prompt: str, max_tokens: int = 1024) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_ollama(prompt: str) -> str:
    import httpx

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"]
```

- [ ] **Step 3: Create briefing generation module**

```python
# backend/app/analyser/briefing.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.company import Company
from app.analyser.client import call_llm


def _build_briefing_prompt(ctx: dict) -> str:
    lines = [
        "Du bist ein Market Intelligence Analyst.",
        "Erstelle eine prägnante, handlungsorientierte Zusammenfassung der wichtigsten Marktentwicklungen.",
        "",
        f"Analysezeitraum: letzte {ctx['days']} Tage",
        f"Neue Signale gesamt: {ctx['total_new']}",
        f"Davon hohe Relevanz (≥0.7): {ctx['high_relevance_count']}",
        "",
        "Aktivste Unternehmen (neue Signale):",
    ]
    for name, count in ctx["company_activity"]:
        lines.append(f"  - {name}: {count} Signale")

    lines += ["", "Top-Signale nach Relevanz:"]
    for s in ctx["top_signals"]:
        lines.append(
            f"  - [{s['company']}] {s['title']} "
            f"(Relevanz: {s['relevance']:.2f}, Typ: {s['type']})"
        )
        if s.get("why_it_matters"):
            lines.append(f"    → {s['why_it_matters']}")

    lines += ["", "Signaltyp-Verteilung:"]
    for stype, count in ctx["type_distribution"]:
        lines.append(f"  - {stype}: {count}")

    lines += [
        "",
        "Erstelle auf Deutsch:",
        "1. Kurze Zusammenfassung (2-3 Sätze) der wichtigsten Entwicklungen",
        "2. Top 3 Empfehlungen: Was sollte der Nutzer sich zuerst anschauen? (mit Begründung)",
        "3. Ausblick: Was könnte sich als nächstes entwickeln?",
        "",
        "Halte es prägnant und konkret.",
    ]
    return "\n".join(lines)


def generate_briefing_content(db: Session, crawl_run_id: Optional[str] = None) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    new_signals = db.query(Signal).filter(Signal.created_at >= cutoff).all()
    total_new = len(new_signals)
    high_relevance_count = sum(
        1 for s in new_signals if (s.relevance_score or 0) >= 0.7
    )

    company_activity = (
        db.query(Company.name, func.count(Signal.id).label("count"))
        .join(Signal, Signal.company_id == Company.id)
        .filter(Signal.created_at >= cutoff)
        .group_by(Company.name)
        .order_by(func.count(Signal.id).desc())
        .limit(5)
        .all()
    )

    top_signals_rows = (
        db.query(Signal, Company.name)
        .join(Company, Company.id == Signal.company_id)
        .filter(Signal.created_at >= cutoff)
        .order_by(Signal.relevance_score.desc().nullslast())
        .limit(10)
        .all()
    )
    top_signals = [
        {
            "title": s.title,
            "company": name,
            "relevance": s.relevance_score or 0,
            "type": s.signal_type.value,
            "why_it_matters": s.why_it_matters,
        }
        for s, name in top_signals_rows
    ]

    type_dist = (
        db.query(Signal.signal_type, func.count(Signal.id).label("count"))
        .filter(Signal.created_at >= cutoff)
        .group_by(Signal.signal_type)
        .order_by(func.count(Signal.id).desc())
        .all()
    )
    type_distribution = [(st.value, count) for st, count in type_dist]

    ctx = {
        "days": 7,
        "total_new": total_new,
        "high_relevance_count": high_relevance_count,
        "company_activity": [(name, count) for name, count in company_activity],
        "top_signals": top_signals,
        "type_distribution": type_distribution,
    }

    prompt = _build_briefing_prompt(ctx)
    return call_llm(prompt, max_tokens=2048)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/crawl_briefing.py backend/app/analyser/briefing.py backend/app/analyser/client.py
git commit -m "feat: add briefing generation logic and schema"
```

---

### Task 3: Briefings router + tests

**Files:**
- Create: `backend/app/routers/briefings.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_briefings_router.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_briefings_router.py
from unittest.mock import patch
from app.models.crawl_briefing import CrawlBriefing
from datetime import datetime, timezone


def test_get_latest_briefing_404_when_none(client):
    response = client.get("/api/briefings/latest")
    assert response.status_code == 404


def test_get_latest_briefing_returns_most_recent(client, db_session):
    older = CrawlBriefing(
        content="older briefing",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = CrawlBriefing(
        content="newer briefing",
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get("/api/briefings/latest")
    assert response.status_code == 200
    assert response.json()["content"] == "newer briefing"


def test_generate_briefing(client):
    with patch(
        "app.routers.briefings.generate_briefing_content",
        return_value="Test briefing content",
    ):
        response = client.post("/api/briefings/generate", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Test briefing content"
    assert data["crawl_run_id"] is None


def test_generate_briefing_with_crawl_run_id(client):
    with patch(
        "app.routers.briefings.generate_briefing_content",
        return_value="Briefing with run",
    ):
        response = client.post(
            "/api/briefings/generate", json={"crawl_run_id": "some-run-id"}
        )
    assert response.status_code == 200
    assert response.json()["crawl_run_id"] == "some-run-id"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_briefings_router.py -v
```

Expected: `FAILED` — router doesn't exist yet.

- [ ] **Step 3: Create the router**

```python
# backend/app/routers/briefings.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.crawl_briefing import CrawlBriefing
from app.schemas.crawl_briefing import CrawlBriefingRead, CrawlBriefingCreate
from app.analyser.briefing import generate_briefing_content

router = APIRouter()


@router.get("/latest", response_model=CrawlBriefingRead)
def get_latest_briefing(db: Session = Depends(get_db)):
    briefing = (
        db.query(CrawlBriefing)
        .order_by(CrawlBriefing.generated_at.desc())
        .first()
    )
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefing found")
    return briefing


@router.post("/generate", response_model=CrawlBriefingRead)
def generate_briefing(payload: CrawlBriefingCreate, db: Session = Depends(get_db)):
    content = generate_briefing_content(db, crawl_run_id=payload.crawl_run_id)
    briefing = CrawlBriefing(
        crawl_run_id=payload.crawl_run_id,
        content=content,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing
```

- [ ] **Step 4: Mount router in `backend/app/main.py`**

Add to the imports block:
```python
from app.routers import (
    companies, sources, documents, signals, digests, context,
    crawl, crawl_runs, discovered_pages, search, stats, briefings,
)
```

Add after the existing `app.include_router(stats.router, ...)` line:
```python
app.include_router(briefings.router, prefix="/api/briefings", tags=["briefings"])
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_briefings_router.py -v
```

Expected: all 4 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/briefings.py backend/app/main.py backend/tests/test_briefings_router.py
git commit -m "feat: add briefings router with GET /latest and POST /generate"
```

---

### Task 4: Auto-trigger briefing after crawl completes

**Files:**
- Modify: `backend/app/routers/crawl.py`

- [ ] **Step 1: Add briefing auto-trigger in `_run_sources_in_thread`**

In `backend/app/routers/crawl.py`, add `import logging` at the top if not present:
```python
import logging
logger = logging.getLogger(__name__)
```

Find the block after `thread_db.commit()` where `crawl_run.status = CrawlRunStatus.completed` is set (around line 182-188). After that `thread_db.commit()` call, add:

```python
        try:
            from app.analyser.briefing import generate_briefing_content
            from app.models.crawl_briefing import CrawlBriefing
            from datetime import datetime, timezone
            briefing_content = generate_briefing_content(thread_db, crawl_run_id=crawl_run_id)
            briefing = CrawlBriefing(
                crawl_run_id=crawl_run_id,
                content=briefing_content,
                generated_at=datetime.now(timezone.utc),
            )
            thread_db.add(briefing)
            thread_db.commit()
        except Exception as e:
            logger.warning("Auto-briefing generation failed: %s", e)
```

- [ ] **Step 2: Verify existing crawl tests still pass**

```bash
cd backend && python -m pytest tests/test_crawl_router.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/crawl.py
git commit -m "feat: auto-generate briefing after crawl completes"
```

---

### Task 5: Frontend — types, hook, BriefingPanel, Dashboard

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/hooks/useBriefing.ts`
- Create: `frontend/src/components/dashboard/BriefingPanel.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Add `CrawlBriefing` type to `frontend/src/types/index.ts`**

Add anywhere in the file:
```typescript
export interface CrawlBriefing {
  id: string;
  crawl_run_id: string | null;
  content: string;
  generated_at: string;
}
```

- [ ] **Step 2: Create the hook**

```typescript
// frontend/src/hooks/useBriefing.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, ApiError } from '../api/client';
import type { CrawlBriefing } from '../types';

export function useLatestBriefing() {
  return useQuery<CrawlBriefing | null>({
    queryKey: ['briefing', 'latest'],
    queryFn: async () => {
      try {
        return await apiGet<CrawlBriefing>('/briefings/latest');
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
}

export function useGenerateBriefing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<CrawlBriefing>('/briefings/generate', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['briefing', 'latest'] });
    },
  });
}
```

- [ ] **Step 4: Create `BriefingPanel`**

```tsx
// frontend/src/components/dashboard/BriefingPanel.tsx
import { RefreshCw } from 'lucide-react';
import { useLatestBriefing, useGenerateBriefing } from '../../hooks/useBriefing';
import MarkdownViewer from '../MarkdownViewer';

export default function BriefingPanel() {
  const { data: briefing, isLoading } = useLatestBriefing();
  const generate = useGenerateBriefing();

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
          Intelligence Briefing
        </p>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={11} className={generate.isPending ? 'animate-spin' : ''} />
          {generate.isPending ? 'Generiere...' : 'Neu generieren'}
        </button>
      </div>

      {isLoading ? (
        <p className="text-[12px] text-slate-400">Lade Briefing...</p>
      ) : briefing ? (
        <>
          <div className="text-[12px] text-slate-700 leading-relaxed">
            <MarkdownViewer content={briefing.content} />
          </div>
          <p className="text-[10px] text-slate-400 mt-3">
            Generiert:{' '}
            {new Date(briefing.generated_at).toLocaleString('de-DE', {
              day: '2-digit',
              month: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </>
      ) : (
        <p className="text-[12px] text-slate-400">
          Noch kein Briefing vorhanden. Starte einen Crawl oder klicke auf "Neu generieren".
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Add `BriefingPanel` to `Dashboard.tsx`**

In `frontend/src/pages/Dashboard.tsx`, add the import:
```typescript
import BriefingPanel from '../components/dashboard/BriefingPanel';
```

In the left column (the `lg:col-span-2 space-y-4` div), add `<BriefingPanel />` directly after `<CrawlSummaryCard ... />`:
```tsx
<CrawlSummaryCard ... />
<BriefingPanel />
<TopSignalsPanel ... />
```

- [ ] **Step 6: Start dev server and verify**

```bash
cd frontend && npm run dev
```

Open the dashboard. Verify:
- BriefingPanel renders below CrawlSummaryCard
- "Neu generieren" button shows loading spinner while pending
- Panel shows placeholder text when no briefing exists
- After clicking "Neu generieren", briefing content appears (requires running backend with `ANTHROPIC_API_KEY`)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/useBriefing.ts frontend/src/components/dashboard/BriefingPanel.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat: add BriefingPanel to dashboard with LLM-generated intelligence summary"
```

---

### Task 6: `DiscoveredPage` model — add `last_signal_relevance` + migration

**Files:**
- Modify: `backend/app/models/discovered_page.py`
- Modify: `backend/app/schemas/discovered_page.py`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add field to the model**

In `backend/app/models/discovered_page.py`, add `Float` to the SQLAlchemy imports:
```python
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Float, ForeignKey, Enum as SAEnum,
)
```

Add the field to the `DiscoveredPage` class after `last_changed_at`:
```python
last_signal_relevance = Column(Float, nullable=True)
```

- [ ] **Step 2: Add field to the schema**

In `backend/app/schemas/discovered_page.py`, add to `DiscoveredPageRead`:
```python
last_signal_relevance: Optional[float] = None
```

- [ ] **Step 3: Generate and run migration**

```bash
cd backend && alembic revision --autogenerate -m "add last_signal_relevance to discovered_pages"
alembic upgrade head
```

Expected: new column `last_signal_relevance` in `discovered_pages` table.

- [ ] **Step 4: Add field to frontend type**

In `frontend/src/types/index.ts`, add to the `DiscoveredPage` interface:
```typescript
last_signal_relevance: number | null;
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/discovered_page.py backend/app/schemas/discovered_page.py backend/alembic/versions/ frontend/src/types/index.ts
git commit -m "feat: add last_signal_relevance field to DiscoveredPage"
```

---

### Task 7: Discovery pipeline — auto-ignore low-relevance pages

**Files:**
- Modify: `backend/app/crawler/discovery.py`
- Modify: `backend/tests/test_discovery.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_discovery.py`:

```python
from app.models.signal import Signal, SignalType
from app.models.document import Document


def _make_signal(db_session, doc_id: str, company_id: str, relevance: float):
    signal = Signal(
        document_id=doc_id,
        company_id=company_id,
        title="Test Signal",
        signal_type=SignalType.other,
        relevance_score=relevance,
        confidence_score=0.8,
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def test_discover_auto_ignores_page_when_all_signals_low(db_session, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-auteignore")

    def mock_save_and_analyse(src, fetch_result, extraction, now, db):
        doc = Document(
            source_id=src.id,
            url=fetch_result.final_url,
            title="Test Article",
            content_markdown="content",
            content_hash=extraction.content_hash,
            crawled_at=now,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        _make_signal(db, doc.id, src.company_id, relevance=0.1)
        _make_signal(db, doc.id, src.company_id, relevance=0.2)

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
        patch("app.crawler.discovery.time.sleep"),
        patch("app.crawler.discovery._save_and_analyse", side_effect=mock_save_and_analyse),
    ):
        discover_and_crawl(source, SEED_HTML, db_session, analyse=True)

    page = db_session.query(DiscoveredPage).first()
    assert page is not None
    assert page.is_active is False
    assert page.status == DiscoveredPageStatus.ignored
    assert page.last_signal_relevance == pytest.approx(0.2)


def test_discover_keeps_page_active_when_one_signal_relevant(db_session, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "discovery_depth", 1)
    source = _make_source(db_session, slug="disc-keep-active")

    def mock_save_and_analyse(src, fetch_result, extraction, now, db):
        doc = Document(
            source_id=src.id,
            url=fetch_result.final_url,
            title="Test Article",
            content_markdown="content",
            content_hash=extraction.content_hash,
            crawled_at=now,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        _make_signal(db, doc.id, src.company_id, relevance=0.1)
        _make_signal(db, doc.id, src.company_id, relevance=0.5)

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=ARTICLE_HTML,
            final_url="https://example.com/blog/2024/04/article-one",
            status_code=200,
        )
    )
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True

    with (
        patch("app.crawler.discovery.fetch_url", mock_fetch),
        patch("app.crawler.discovery._get_robot_parser", return_value=mock_rp),
        patch("app.crawler.discovery.time.sleep"),
        patch("app.crawler.discovery._save_and_analyse", side_effect=mock_save_and_analyse),
    ):
        discover_and_crawl(source, SEED_HTML, db_session, analyse=True)

    page = db_session.query(DiscoveredPage).first()
    assert page.is_active is True
    assert page.last_signal_relevance == pytest.approx(0.5)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_discovery.py::test_discover_auto_ignores_page_when_all_signals_low tests/test_discovery.py::test_discover_keeps_page_active_when_one_signal_relevant -v
```

Expected: `FAILED`.

- [ ] **Step 3: Implement `_update_page_relevance` helper and wire it in**

In `backend/app/crawler/discovery.py`, add `Signal` and `Document` imports at the top:
```python
from app.models.document import Document
from app.models.signal import Signal
```

Add the helper function before `discover_and_crawl`:
```python
def _update_page_relevance(page: DiscoveredPage, url: str, db: Session) -> None:
    doc = db.query(Document).filter(Document.url == url).first()
    if not doc:
        return
    signals = db.query(Signal).filter(Signal.document_id == doc.id).all()
    if not signals:
        return
    scores = [s.relevance_score or 0 for s in signals]
    page.last_signal_relevance = max(scores)
    if all(score < 0.3 for score in scores):
        page.is_active = False
        page.status = DiscoveredPageStatus.ignored
    db.commit()
```

In `discover_and_crawl`, after both `if analyse: _save_and_analyse(...)` calls (new page and changed page branches), call the helper. For the **new page** branch (around line 210):
```python
                if analyse:
                    _save_and_analyse(source, fetch_result, extraction, now, db)
                    _update_page_relevance(page, final_url, db)
```

For the **changed page** branch (around line 226):
```python
                if analyse:
                    _save_and_analyse(source, fetch_result, extraction, now, db)
                    _update_page_relevance(existing, final_url, db)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_discovery.py -v
```

Expected: all tests `PASSED` including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/discovery.py backend/tests/test_discovery.py
git commit -m "feat: auto-ignore discovered pages where all signals have relevance < 0.3"
```

---

### Task 8: SourcesAdmin frontend — show relevance badge

**Files:**
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Add relevance badge to `DiscoveredPagesSection`**

In `frontend/src/pages/SourcesAdmin.tsx`, add a `relevanceBadge` helper inside `DiscoveredPagesSection`, after `statusBadge`:

```tsx
  const relevanceBadge = (score: number | null) => {
    if (score === null || score === undefined) {
      return <span className="text-xs text-ink-muted">—</span>;
    }
    const isRelevant = score >= 0.3;
    return (
      <span
        className={`text-xs px-1.5 py-0.5 rounded font-medium ${
          isRelevant
            ? 'bg-emerald-100 text-emerald-700'
            : 'bg-red-100 text-red-600'
        }`}
      >
        {score.toFixed(2)}
      </span>
    );
  };
```

In the `<thead>` row of the table, add a new `<th>` after the "Status" column:
```tsx
<th className="text-left py-1 text-ink-muted font-medium">Relevanz</th>
```

In the `<tbody>` rows, add a new `<td>` after the status cell:
```tsx
<td className="py-1">{relevanceBadge(page.last_signal_relevance)}</td>
```

Also add an "Auto-ignoriert" chip for auto-ignored pages. In the "Active" `<td>`, update it so that when `!page.is_active` the button text shows "Auto-ignoriert" if `page.last_signal_relevance !== null && page.last_signal_relevance < 0.3`, otherwise "Ignoriert":
```tsx
<td className="py-1">
  <button
    onClick={() => onToggle(page.id, !page.is_active)}
    className={`text-xs px-2 py-0.5 rounded ${
      page.is_active
        ? 'bg-signal-high/20 text-signal-high'
        : 'bg-app-bg text-ink-muted'
    }`}
  >
    {page.is_active
      ? 'Active'
      : page.last_signal_relevance !== null &&
        page.last_signal_relevance < 0.3
      ? 'Auto-ignoriert'
      : 'Ignoriert'}
  </button>
</td>
```

- [ ] **Step 2: Verify in the browser**

With the dev server running, navigate to the Sources admin page, expand a source that has discovered pages. Verify:
- "Relevanz" column appears
- Pages with score ≥ 0.3 show a green badge
- Pages with score < 0.3 show a red badge
- Pages that were auto-ignored show "Auto-ignoriert" label
- Toggle still works (re-activates a page)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SourcesAdmin.tsx
git commit -m "feat: show signal relevance badge and auto-ignored label for discovered pages"
```

---

## Full test run

After all tasks are complete:

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests pass (51 existing + new briefing and discovery tests).
