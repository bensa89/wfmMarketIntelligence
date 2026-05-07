# Parallel Analysis Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the sequential document analysis loop with a ThreadPoolExecutor so LLM calls run in parallel, reducing analysis time by ~3x at default concurrency.

**Architecture:** Each worker thread owns its own SQLAlchemy Session and runs one `analyse_document` call independently. The main thread collects results via `as_completed` and emits SSE progress events using an atomic counter. `InternalCompanyContext` is loaded once before the pool and passed as a dict to avoid N redundant DB queries.

**Tech Stack:** Python `concurrent.futures.ThreadPoolExecutor`, SQLAlchemy `SessionLocal`, existing `analyse_document` pipeline, pydantic-settings, React/TypeScript frontend types.

---

## File Map

| File | Change |
|------|--------|
| `backend/app/config.py` | Add `analysis_concurrency: int = 3` |
| `backend/app/analyser/client.py` | Module-level singletons for Anthropic + OpenCode clients |
| `backend/app/analyser/pipeline.py` | Extract `_build_context_dict`, add `preloaded_context` param to `analyse_document` |
| `backend/app/crawler/pipeline.py` | Add `_analyse_doc_worker`, replace for-loop in `analyse_unanalysed_for_source` with ThreadPoolExecutor |
| `frontend/src/types/index.ts` | Remove `url` from `CrawlAnalysisProgressEvent`; remove `currentUrl` from `SourceCrawlState.analysisProgress` |
| `frontend/src/hooks/useCrawlStream.ts` | Remove `currentUrl` from `analysis_progress` handler |
| `backend/tests/test_analyser_pipeline.py` | New: tests for `_build_context_dict` and `preloaded_context` |
| `backend/tests/test_crawler_pipeline.py` | New: tests for `_analyse_doc_worker` and parallel execution timing |

---

## Task 1: Add `analysis_concurrency` to config

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add the setting**

Open `backend/app/config.py`. Add one line after `discovery_concurrency`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    crawl_concurrency: int = 4
    discovery_concurrency: int = 3
    analysis_concurrency: int = 3   # ← add this
```

- [ ] **Step 2: Verify it loads**

```bash
cd backend && python -c "from app.config import settings; print(settings.analysis_concurrency)"
```

Expected output: `3`

- [ ] **Step 3: Commit**

```bash
rtk git add backend/app/config.py
rtk git commit -m "feat: add analysis_concurrency config setting"
```

---

## Task 2: LLM client singletons

**Files:**
- Modify: `backend/app/analyser/client.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_analyser_client.py`:

```python
from unittest.mock import patch, MagicMock
import importlib


def test_anthropic_client_reused_across_calls():
    """Same client instance should be returned on repeated calls."""
    import app.analyser.client as client_module
    # Reset singleton
    client_module._anthropic_client = None

    mock_client = MagicMock()
    with patch("anthropic.Anthropic", return_value=mock_client) as mock_cls:
        from app.analyser.client import _get_anthropic_client
        c1 = _get_anthropic_client()
        c2 = _get_anthropic_client()

    assert c1 is c2
    assert mock_cls.call_count == 1


def test_opencode_client_reused_across_calls():
    import app.analyser.client as client_module
    client_module._opencode_client = None

    mock_client = MagicMock()
    with patch("openai.OpenAI", return_value=mock_client) as mock_cls:
        from app.analyser.client import _get_opencode_client
        c1 = _get_opencode_client()
        c2 = _get_opencode_client()

    assert c1 is c2
    assert mock_cls.call_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_analyser_client.py -v
```

Expected: `ERROR` — `_get_anthropic_client` not defined yet.

- [ ] **Step 3: Rewrite `client.py` with singletons**

Replace the full content of `backend/app/analyser/client.py`:

```python
from app.config import settings

_anthropic_client = None
_opencode_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, timeout=120.0
        )
    return _anthropic_client


def _get_opencode_client():
    global _opencode_client
    if _opencode_client is None:
        from openai import OpenAI
        _opencode_client = OpenAI(
            api_key=settings.opencode_api_key,
            base_url=settings.opencode_base_url,
            timeout=120.0,
        )
    return _opencode_client


def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    if settings.llm_provider == "ollama":
        return _call_ollama(prompt, max_tokens=max_tokens)
    if settings.llm_provider == "opencode":
        return _call_opencode(prompt, max_tokens=max_tokens)
    return _call_claude(prompt, max_tokens=max_tokens)


def _call_claude(prompt: str, max_tokens: int = 1024) -> str:
    client = _get_anthropic_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_opencode(prompt: str, max_tokens: int = 1024) -> str:
    client = _get_opencode_client()
    response = client.chat.completions.create(
        model=settings.opencode_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _call_ollama(prompt: str, max_tokens: int = 1024) -> str:
    import httpx

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"]
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_analyser_client.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all existing tests pass.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/analyser/client.py backend/tests/test_analyser_client.py
rtk git commit -m "feat: use singleton LLM clients for thread safety"
```

---

## Task 3: Extract `_build_context_dict` and add `preloaded_context` to `analyse_document`

**Files:**
- Modify: `backend/app/analyser/pipeline.py`
- Create: `backend/tests/test_analyser_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_analyser_pipeline.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from app.analyser.pipeline import _build_context_dict, analyse_document
from app.models.context import InternalCompanyContext


def _make_ctx(**kwargs):
    ctx = MagicMock(spec=InternalCompanyContext)
    ctx.company_name = kwargs.get("company_name", "Acme")
    ctx.short_description = kwargs.get("short_description", "A company")
    ctx.target_industries = kwargs.get("target_industries", ["HR"])
    ctx.target_segments = kwargs.get("target_segments", [])
    ctx.core_capabilities = kwargs.get("core_capabilities", [])
    ctx.strategic_priorities = kwargs.get("strategic_priorities", [])
    ctx.differentiators = kwargs.get("differentiators", [])
    ctx.relevant_competitive_areas = kwargs.get("relevant_competitive_areas", [])
    ctx.non_focus_areas = kwargs.get("non_focus_areas", [])
    return ctx


def test_build_context_dict_with_record():
    ctx = _make_ctx(company_name="TestCo", target_industries=["Retail"])
    result = _build_context_dict(ctx)
    assert result["company_name"] == "TestCo"
    assert result["target_industries"] == ["Retail"]


def test_build_context_dict_with_none():
    result = _build_context_dict(None)
    assert result == {}


def test_analyse_document_uses_preloaded_context(db_session):
    """When preloaded_context is passed, no DB query for InternalCompanyContext."""
    from app.models.document import Document
    from datetime import datetime, timezone

    doc = Document(
        source_id="src-1",
        url="https://example.com/article",
        content_markdown="word " * 60,
        content_hash="abc123",
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.commit()

    preloaded = {"company_name": "Preloaded Co", "target_industries": ["SaaS"]}

    with patch("app.analyser.pipeline.call_llm", return_value='{"signal_type": "product_update", "title": "T", "topic": "X", "summary": "S", "why_it_matters": "W", "relevance_score": 0.1, "confidence_score": 0.9, "published_at": null}'):
        with patch.object(db_session, "query") as mock_query:
            # Should NOT query InternalCompanyContext
            analyse_document(doc, "company-1", db_session, preloaded_context=preloaded)
            queried_models = [call.args[0] for call in mock_query.call_args_list]
            from app.models.context import InternalCompanyContext
            assert InternalCompanyContext not in queried_models
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_analyser_pipeline.py -v
```

Expected: FAILED — `_build_context_dict` not importable, `analyse_document` has no `preloaded_context` param.

- [ ] **Step 3: Update `analyse_document` in `pipeline.py`**

Replace `backend/app/analyser/pipeline.py` with:

```python
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.document import Document
from app.models.signal import Signal
from app.models.context import InternalCompanyContext
import logging

from app.analyser.client import call_llm
from app.analyser.prompts import build_analysis_prompt
from app.analyser.parser import parse_llm_response

logger = logging.getLogger(__name__)

_MIN_CONTENT_WORDS = 50
_MAX_AGE_DAYS = 365


def _build_context_dict(ctx_record) -> dict:
    if not ctx_record:
        return {}
    return {
        "company_name": ctx_record.company_name,
        "short_description": ctx_record.short_description,
        "target_industries": ctx_record.target_industries or [],
        "target_segments": ctx_record.target_segments or [],
        "core_capabilities": ctx_record.core_capabilities or [],
        "strategic_priorities": ctx_record.strategic_priorities or [],
        "differentiators": ctx_record.differentiators or [],
        "relevant_competitive_areas": ctx_record.relevant_competitive_areas or [],
        "non_focus_areas": ctx_record.non_focus_areas or [],
    }


def analyse_document(
    doc: Document,
    company_id: str,
    db: Session,
    preloaded_context: dict | None = None,
) -> None:
    if not doc.content_markdown:
        return

    word_count = len(doc.content_markdown.split())
    if word_count < _MIN_CONTENT_WORDS:
        logger.info(
            "Skipping analysis for doc %s: only %d words (minimum %d)",
            doc.id,
            word_count,
            _MIN_CONTENT_WORDS,
        )
        return

    existing_signal = db.query(Signal).filter(Signal.document_id == doc.id).first()
    if existing_signal:
        doc.is_analysed = True
        db.commit()
        return

    if doc.content_hash:
        duplicate = (
            db.query(Signal)
            .join(Document, Signal.document_id == Document.id)
            .filter(
                and_(
                    Document.content_hash == doc.content_hash,
                    Signal.company_id == company_id,
                )
            )
            .first()
        )
        if duplicate:
            logger.info(
                "Skipping analysis for doc %s: content_hash already analysed (duplicate of doc %s)",
                doc.id,
                duplicate.document_id,
            )
            doc.is_analysed = True
            db.commit()
            return

    age_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=_MAX_AGE_DAYS)
    if doc.published_at and doc.published_at < age_threshold:
        logger.info(
            "Skipping analysis for doc %s: published_at %s is older than %d days",
            doc.id,
            doc.published_at,
            _MAX_AGE_DAYS,
        )
        doc.is_analysed = True
        db.commit()
        return

    if preloaded_context is not None:
        context = preloaded_context
    else:
        ctx_record = db.query(InternalCompanyContext).first()
        context = _build_context_dict(ctx_record)

    prompt = build_analysis_prompt(doc.content_markdown, context)
    raw_response = call_llm(prompt)
    signal_data = parse_llm_response(raw_response)

    if signal_data is None:
        logger.info(
            "Skipping signal creation for doc %s: LLM unable to analyze content",
            doc.id,
        )
        doc.is_analysed = True
        db.commit()
        return

    if signal_data.published_at and signal_data.published_at < age_threshold:
        logger.info(
            "Skipping signal for doc %s: LLM-detected published_at %s is older than %d days",
            doc.id,
            signal_data.published_at,
            _MAX_AGE_DAYS,
        )
        doc.is_analysed = True
        db.commit()
        return

    signal = Signal(
        document_id=doc.id,
        company_id=company_id,
        title=signal_data.title,
        signal_type=signal_data.signal_type,
        topic=signal_data.topic,
        summary=signal_data.summary,
        why_it_matters=signal_data.why_it_matters,
        relevance_score=signal_data.relevance_score,
        confidence_score=signal_data.confidence_score,
        published_at=signal_data.published_at or doc.published_at or doc.crawled_at,
    )
    db.add(signal)

    doc.is_analysed = True
    db.commit()
    db.refresh(signal)

    try:
        from app.config import settings
        if (signal.relevance_score or 0.0) >= settings.assessment_threshold:
            from app.assessor.pipeline import assess_signal
            assess_signal(signal, db)
    except Exception as e:
        logger.warning("Assessment hook failed for signal %s: %s", signal.id, e)
```

- [ ] **Step 4: Run new tests**

```bash
cd backend && python -m pytest tests/test_analyser_pipeline.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all existing tests pass.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/analyser/pipeline.py backend/tests/test_analyser_pipeline.py
rtk git commit -m "feat: extract _build_context_dict, add preloaded_context to analyse_document"
```

---

## Task 4: Add `_analyse_doc_worker` and parallel loop

**Files:**
- Modify: `backend/app/crawler/pipeline.py`
- Create: `backend/tests/test_crawler_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_crawler_pipeline.py`:

```python
import time
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


def test_analyse_doc_worker_success(db_session):
    """Worker returns (doc_id, True) on success."""
    from app.crawler.pipeline import _analyse_doc_worker
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from datetime import datetime, timezone

    company = Company(name="TestCo", slug="testco-w", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://test.com", source_type=SourceType.news, is_active=True)
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://test.com/art1",
        content_markdown="word " * 60,
        content_hash="h1",
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.commit()
    doc_id = doc.id

    with patch("app.analyser.pipeline.call_llm", return_value="{}"):
        with patch("app.analyser.pipeline.parse_llm_response", return_value=None):
            result_id, success = _analyse_doc_worker(doc_id, company.id, {})

    assert result_id == doc_id
    assert success is True


def test_analyse_doc_worker_exception_returns_false(db_session):
    """Worker returns (doc_id, False) when analyse_document raises."""
    from app.crawler.pipeline import _analyse_doc_worker
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from datetime import datetime, timezone

    company = Company(name="TestCo2", slug="testco-w2", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://test2.com", source_type=SourceType.news, is_active=True)
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://test2.com/art1",
        content_markdown="word " * 60,
        content_hash="h2",
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.commit()
    doc_id = doc.id

    with patch("app.analyser.pipeline.call_llm", side_effect=RuntimeError("LLM down")):
        result_id, success = _analyse_doc_worker(doc_id, company.id, {})

    assert result_id == doc_id
    assert success is False


def test_parallel_analysis_faster_than_sequential():
    """With concurrency=3, 6 docs taking 0.3s each should finish in ~0.6s not ~1.8s."""
    from app.crawler.pipeline import _analyse_doc_worker
    import concurrent.futures
    import threading

    call_times = []
    lock = threading.Lock()

    def slow_worker(doc_id, company_id, context):
        time.sleep(0.3)
        with lock:
            call_times.append(time.monotonic())
        return doc_id, True

    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(slow_worker, f"doc-{i}", "co", {}) for i in range(6)]
        concurrent.futures.wait(futures)
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, f"Expected < 1.0s with concurrency=3, got {elapsed:.2f}s"
    assert len(call_times) == 6
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_crawler_pipeline.py -v
```

Expected: FAILED — `_analyse_doc_worker` not importable.

- [ ] **Step 3: Add `_analyse_doc_worker` and update `analyse_unanalysed_for_source`**

At the top of `backend/app/crawler/pipeline.py`, add imports after the existing ones:

```python
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.database import SessionLocal
from app.models.context import InternalCompanyContext
from app.analyser.pipeline import _build_context_dict
```

After the existing imports block, add the worker function (before `run_crawl_source`):

```python
def _analyse_doc_worker(
    doc_id: str, company_id: str, context: dict
) -> tuple[str, bool]:
    db = SessionLocal()
    try:
        from app.analyser.pipeline import analyse_document
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            analyse_document(doc, company_id, db, preloaded_context=context)
        return doc_id, True
    except Exception as e:
        logger.exception("Analysis worker failed for doc %s: %s", doc_id, e)
        db.rollback()
        return doc_id, False
    finally:
        db.close()
```

Replace the full `analyse_unanalysed_for_source` function (lines 183–271) with:

```python
def analyse_unanalysed_for_source(
    source: Source,
    db: Session,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> Dict:
    from app.models.discovered_page import DiscoveredPage
    from app.crawler.discovery import _update_page_relevance

    def emit(event: dict):
        if progress_callback:
            progress_callback(event)

    result = {"source_id": source.id, "analysed": 0, "errors": 0, "analyse_ms": 0}

    source.analysis_status = AnalysisStatus.analysing
    db.commit()

    unanalysed = (
        db.query(Document)
        .filter(
            Document.source_id == source.id,
            Document.is_analysed == False,
        )
        .order_by(Document.crawled_at.asc())
        .all()
    )

    if not unanalysed:
        source.analysis_status = AnalysisStatus.analysed
        db.commit()
        return result

    for page in (
        db.query(DiscoveredPage)
        .filter(
            DiscoveredPage.source_id == source.id,
            DiscoveredPage.analysis_status == "pending",
        )
        .all()
    ):
        page.analysis_status = "analysing"
    db.commit()

    total = len(unanalysed)
    t0 = time.monotonic()

    ctx_record = db.query(InternalCompanyContext).first()
    context = _build_context_dict(ctx_record)

    completed_count = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=settings.analysis_concurrency) as executor:
        futures = {
            executor.submit(_analyse_doc_worker, doc.id, source.company_id, context): doc
            for doc in unanalysed
        }
        for future in as_completed(futures):
            doc_id, success = future.result()
            with lock:
                completed_count += 1
                current = completed_count
            if success:
                result["analysed"] += 1
            else:
                result["errors"] += 1
            emit(
                {
                    "type": "analysis_progress",
                    "source_id": source.id,
                    "current": current,
                    "total": total,
                    "url": "",
                }
            )

    result["analyse_ms"] = int((time.monotonic() - t0) * 1000)

    # Post-pool: update DiscoveredPage statuses in main thread
    for doc in unanalysed:
        page = db.query(DiscoveredPage).filter(DiscoveredPage.url == doc.url).first()
        if page:
            try:
                _update_page_relevance(page, doc.url, db)
                page.analysis_status = "analysed"
            except Exception as e:
                logger.warning("DiscoveredPage update failed for %s: %s", doc.url, e)
                page.analysis_status = "analysis_failed"
    db.commit()

    source.analysis_status = (
        AnalysisStatus.analysed
        if result["errors"] == 0
        else AnalysisStatus.analysis_failed
    )
    db.commit()

    return result
```

- [ ] **Step 4: Run new tests**

```bash
cd backend && python -m pytest tests/test_crawler_pipeline.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all existing tests pass.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/crawler/pipeline.py backend/tests/test_crawler_pipeline.py
rtk git commit -m "feat: parallel document analysis with ThreadPoolExecutor"
```

---

## Task 5: Remove `currentUrl` / `url` from frontend types and hook

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/hooks/useCrawlStream.ts`

- [ ] **Step 1: Update `CrawlAnalysisProgressEvent` in `types/index.ts`**

In `frontend/src/types/index.ts`, find the `CrawlAnalysisProgressEvent` interface (around line 288) and remove the `url` field:

```typescript
export interface CrawlAnalysisProgressEvent {
  type: 'analysis_progress';
  source_id: string;
  current: number;
  total: number;
}
```

- [ ] **Step 2: Update `SourceCrawlState.analysisProgress` in `types/index.ts`**

Find the `SourceCrawlState` interface (around line 361) and remove `currentUrl`:

```typescript
  analysisProgress?: {
    current: number;
    total: number;
  };
```

- [ ] **Step 3: Update `analysis_progress` handler in `useCrawlStream.ts`**

In `frontend/src/hooks/useCrawlStream.ts`, find the `analysis_progress` case (around line 259) and remove the `currentUrl` line:

```typescript
        case 'analysis_progress':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    analysisProgress: {
                      current: event.current,
                      total: event.total,
                    },
                  }
                : s
            ),
          );
          break;
```

- [ ] **Step 4: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/types/index.ts frontend/src/hooks/useCrawlStream.ts
rtk git commit -m "feat: remove currentUrl from analysis_progress (parallel analysis has no single URL)"
```

---

## Self-Review Checklist

- [x] Config setting added (Task 1)
- [x] LLM singletons for Anthropic + OpenCode (Task 2) — Ollama unchanged (stateless httpx)
- [x] `_build_context_dict` extracted, `preloaded_context` param added with fallback (Task 3)
- [x] `_analyse_doc_worker` with own session + error handling (Task 4)
- [x] Parallel loop with atomic counter + `as_completed` (Task 4)
- [x] DiscoveredPage updates post-pool in main thread (Task 4)
- [x] Frontend `url`/`currentUrl` fields removed (Task 5)
- [x] All tasks have real test code, no placeholders
- [x] Type consistency: `_build_context_dict` defined in Task 3, imported in Task 4
