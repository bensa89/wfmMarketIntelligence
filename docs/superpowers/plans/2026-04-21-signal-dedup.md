# Signal Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent duplicate signals from overview pages and provide a manual LLM-powered dedup cleanup endpoint.

**Architecture:** Three changes — (1) skip analysis on non-article source pages, (2) guard against double Signal creation per Document, (3) add a POST `/api/signals/deduplicate` endpoint that uses LLM to identify and merge duplicate signals.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Anthropic SDK, pytest

---

### Task 1: Add document_id dedup guard in analyse_document()

**Files:**
- Modify: `backend/app/analyser/pipeline.py`
- Test: `backend/tests/test_analyser.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_analyser.py`:

```python
def test_analyse_document_skips_if_signal_already_exists(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.analyser.pipeline import analyse_document

    company = Company(name="ATOSS", slug="atoss-dedup", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/dedup", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/dedup/1",
        content_markdown="## AI Feature",
        content_hash="h_dedup",
    )
    db_session.add(doc)
    db_session.commit()

    existing_signal = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="Existing Signal",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.8,
    )
    db_session.add(existing_signal)
    db_session.commit()

    with patch(
        "app.analyser.pipeline.call_llm",
        return_value='{"title":"Duplicate","signal_type":"ai_announcement","topic":"AI","summary":"Dup.","why_it_matters":"Dup.","relevance_score":0.7,"confidence_score":0.7}',
    ):
        analyse_document(doc, company.id, db_session)

    assert db_session.query(Signal).count() == 1
    assert db_session.query(Signal).first().title == "Existing Signal"
    assert doc.is_analysed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_analyser.py::test_analyse_document_skips_if_signal_already_exists -v`
Expected: FAIL — second Signal gets created

- [ ] **Step 3: Add dedup guard to `analyse_document()`**

In `backend/app/analyser/pipeline.py`, add the following check at the beginning of `analyse_document()`, after the `if not doc.content_markdown:` check:

```python
def analyse_document(doc: Document, company_id: str, db: Session) -> None:
    if not doc.content_markdown:
        return

    existing_signal = db.query(Signal).filter(Signal.document_id == doc.id).first()
    if existing_signal:
        doc.is_analysed = True
        db.commit()
        return

    ctx_record = db.query(InternalCompanyContext).first()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_analyser.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/analyser/pipeline.py backend/tests/test_analyser.py
git commit -m "feat: guard against duplicate signals per document in analyse_document"
```

---

### Task 2: Skip analysis on non-article source pages

**Files:**
- Modify: `backend/app/crawler/pipeline.py`
- Test: `backend/tests/test_crawler.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_crawler.py`:

```python
def test_run_crawl_source_skips_analysis_on_non_article_page(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document

    company = Company(name="ATOSS", slug="atoss-noart", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/noart",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    nav_html = """<html><head><title>Overview</title></head><body>
        <nav><a href="/link1">Link1</a><a href="/link2">Link2</a></nav>
        <main><p>Short teaser</p></main>
    </body></html>"""

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=nav_html, final_url="https://atoss.com/noart", status_code=200
        )
    )
    mock Analyse = MagicMock()

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.discover_and_crawl", return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0}),
        patch("app.crawler.pipeline._is_article_content", return_value=False),
        patch("app.analyser.pipeline.analyse_document", mock_analyse) as mock_analyse,
    ):
        result = run_crawl_source(source, db_session, analyse=True)

    assert result["new_documents"] == 1
    assert db_session.query(Document).count() == 1
    mock_analyse.assert_not_called()


def test_run_crawl_source_analyses_article_page(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType

    company = Company(name="ATOSS", slug="atoss-art", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://atoss.com/art",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()

    article_html = """<html><head><title>Article</title></head><body>
        <main><p>This is a real article with enough content to be considered substantive for analysis purposes and contains detailed information.</p></main>
    </body></html>"""

    mock_fetch = MagicMock(
        return_value=MagicMock(
            html=article_html, final_url="https://atoss.com/art", status_code=200
        )
    )

    with (
        patch("app.crawler.pipeline.fetch_url", mock_fetch),
        patch("app.crawler.pipeline.discover_and_crawl", return_value={"discovered": 0, "new": 0, "changed": 0, "known": 0}),
        patch("app.crawler.pipeline._is_article_content", return_value=True),
        patch("app.analyser.pipeline.analyse_document") as mock_analyse,
    ):
        result = run_crawl_source(source, db_session, analyse=True)

    assert result["new_documents"] == 1
    mock_analyse.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_crawler.py::test_run_crawl_source_skips_analysis_on_non_article_page -v`
Expected: FAIL — `_is_article_content` is not imported in pipeline.py yet, analysis always runs

- [ ] **Step 3: Modify `run_crawl_source()` in pipeline.py**

In `backend/app/crawler/pipeline.py`:

Add to imports at top:
```python
from app.crawler.discovery import discover_and_crawl, _extract_internal_links, _is_article_content
```

Wrap the two `if analyse:` blocks (both the existing-document branch around line 101 and the new-document branch around line 134) with an article check. The key change: before calling `analyse_document`, check if the page is article content.

For the **existing document** branch (content changed), replace:
```python
            if analyse:
                from app.analyser.pipeline import analyse_document

                db.refresh(existing_by_url)
                emit({"type": "step", "source_id": source.id, "step": "analysing"})
                try:
                    analyse_document(existing_by_url, source.company_id, db)
                except Exception as e:
```
with:
```python
            if analyse and _is_article_content(fetch_result.html):
                from app.analyser.pipeline import analyse_document

                db.refresh(existing_by_url)
                emit({"type": "step", "source_id": source.id, "step": "analysing"})
                try:
                    analyse_document(existing_by_url, source.company_id, db)
                except Exception as e:
```

For the **new document** branch, replace:
```python
        if analyse:
            from app.analyser.pipeline import analyse_document

            db.refresh(doc)
            emit({"type": "step", "source_id": source.id, "step": "analysing"})
            try:
                analyse_document(doc, source.company_id, db)
            except Exception as e:
```
with:
```python
        if analyse and _is_article_content(fetch_result.html):
            from app.analyser.pipeline import analyse_document

            db.refresh(doc)
            emit({"type": "step", "source_id": source.id, "step": "analysing"})
            try:
                analyse_document(doc, source.company_id, db)
            except Exception as e:
```

Also update the Discovery call to pass `analyse=analyse` unchanged (it already uses `_is_article_content` internally for discovery pages, which is correct).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_crawler.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/pipeline.py backend/tests/test_crawler.py
git commit -m "feat: skip signal creation for non-article source pages"
```

---

### Task 3: Create dedup LLM prompt and merge logic

**Files:**
- Create: `backend/app/analyser/dedup.py`
- Test: `backend/tests/test_dedup.py`

- [ ] **Step 1: Write the tests**

Create `backend/tests/test_dedup.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.analyser.dedup import deduplicate_signals, build_dedup_prompt


def test_build_dedup_prompt_includes_signals():
    signals = [
        MagicMock(id="id1", title="AI Feature Launch", signal_type="ai_announcement", topic="AI", summary="Company launched AI.", relevance_score=0.9),
        MagicMock(id="id2", title="New AI Feature", signal_type="ai_announcement", topic="AI", summary="Similar AI launch.", relevance_score=0.7),
    ]
    prompt = build_dedup_prompt(signals)
    assert "id1" in prompt
    assert "id2" in prompt
    assert "AI Feature Launch" in prompt
    assert "New AI Feature" in prompt


def test_deduplicate_merges_duplicate_signals(db_session):
    company = Company(name="ATOSS", slug="atoss-dedup-merge", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/dedup-merge", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc1 = Document(source_id=source.id, url="https://atoss.com/dedup-merge/1", content_hash="hm1")
    doc2 = Document(source_id=source.id, url="https://atoss.com/dedup-merge/2", content_hash="hm2")
    db_session.add_all([doc1, doc2])
    db_session.commit()

    s1 = Signal(
        document_id=doc1.id,
        company_id=company.id,
        title="ATOSS launches AI scheduling",
        signal_type=SignalType.ai_announcement,
        topic="AI",
        summary="ATOSS released a new AI scheduling module for workforce management.",
        why_it_matters="Competes directly with our scheduling product.",
        relevance_score=0.9,
        confidence_score=0.85,
    )
    s2 = Signal(
        document_id=doc2.id,
        company_id=company.id,
        title="AI scheduling feature from ATOSS",
        signal_type=SignalType.ai_announcement,
        topic="AI",
        summary="ATOSS has introduced AI-powered scheduling capabilities.",
        why_it_matters="Threat to our market position in scheduling.",
        relevance_score=0.6,
        confidence_score=0.7,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    llm_response = f'{{"merge_groups": [["{s1.id}", "{s2.id}"]]}}'

    with patch("app.analyser.dedup.call_llm", return_value=llm_response):
        result = deduplicate_signals(db_session, company_id=company.id)

    assert result["merged_count"] == 1
    assert result["removed_ids"] == [s2.id]
    assert result["kept_signals"][0]["id"] == s1.id
    assert db_session.query(Signal).count() == 1
    kept = db_session.query(Signal).first()
    assert kept.title == "ATOSS launches AI scheduling"
    assert kept.relevance_score == 0.9


def test_deduplicate_no_duplicates_found(db_session):
    company = Company(name="ATOSS", slug="atoss-dedup-no", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/dedup-no", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/dedup-no/1", content_hash="hn1")
    db_session.add(doc)
    db_session.commit()

    s1 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="AI Feature",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    db_session.add(s1)
    db_session.commit()

    with patch("app.analyser.dedup.call_llm", return_value='{"merge_groups": []}'):
        result = deduplicate_signals(db_session, company_id=company.id)

    assert result["merged_count"] == 0
    assert result["removed_ids"] == []
    assert db_session.query(Signal).count() == 1


def test_deduplicate_keeps_better_summary_on_merge(db_session):
    company = Company(name="ATOSS", slug="atoss-dedup-sum", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/dedup-sum", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc1 = Document(source_id=source.id, url="https://atoss.com/dedup-sum/1", content_hash="hs1")
    doc2 = Document(source_id=source.id, url="https://atoss.com/dedup-sum/2", content_hash="hs2")
    db_session.add_all([doc1, doc2])
    db_session.commit()

    s1 = Signal(
        document_id=doc1.id,
        company_id=company.id,
        title="Partner Deal",
        signal_type=SignalType.partnership,
        summary="Short.",
        why_it_matters="Brief note.",
        relevance_score=0.9,
        confidence_score=0.8,
    )
    s2 = Signal(
        document_id=doc2.id,
        company_id=company.id,
        title="Partnership Announcement",
        signal_type=SignalType.partnership,
        summary="A very detailed and comprehensive summary of the partnership with specific details about the agreement and market impact.",
        why_it_matters="Detailed explanation of why this matters for competitive positioning and strategic direction.",
        relevance_score=0.6,
        confidence_score=0.7,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    llm_response = f'{{"merge_groups": [["{s1.id}", "{s2.id}"]]}}'

    with patch("app.analyser.dedup.call_llm", return_value=llm_response):
        result = deduplicate_signals(db_session, company_id=company.id)

    kept = db_session.query(Signal).first()
    assert kept.title == "Partner Deal"
    assert kept.relevance_score == 0.9
    assert len(kept.summary) > len("Short.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_dedup.py -v`
Expected: FAIL — `app.analyser.dedup` module doesn't exist

- [ ] **Step 3: Create `backend/app/analyser/dedup.py`**

```python
import json
import logging
import re
from typing import Dict, List
from sqlalchemy.orm import Session, selectinload
from app.models.signal import Signal
from app.analyser.client import call_llm

logger = logging.getLogger(__name__)


def build_dedup_prompt(signals: List[Signal]) -> str:
    lines = []
    for i, s in enumerate(signals, 1):
        lines.append(
            f'{i}. [{s.id}] "{s.title}" | {s.signal_type.value} | '
            f'topic: {s.topic or "N/A"} | summary: {s.summary or "N/A"} | '
            f'relevance: {s.relevance_score or 0:.2f}'
        )
    signal_list = "\n".join(lines)
    return f"""You are a market intelligence analyst reviewing signals for duplicates.

Two signals are duplicates if they refer to the same specific event, announcement, or change — even if worded differently.
Signals about similar but distinct events are NOT duplicates (e.g., two different product launches are not duplicates).

{signal_list}

Return ONLY a valid JSON object:
{{"merge_groups": [[signal_id_1, signal_id_2], [signal_id_3, signal_id_4, signal_id_5]]}}

Each group is a set of duplicate signals. If no duplicates exist, return {{"merge_groups": []}}.
No markdown fences, no extra text."""


def _parse_merge_groups(raw: str, valid_ids: set) -> List[List[str]]:
    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        data = json.loads(raw)
        groups = data.get("merge_groups", [])
        result = []
        for group in groups:
            clean = [gid for gid in group if gid in valid_ids]
            if len(clean) > 1:
                result.append(clean)
        return result
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse LLM dedup response: %s", raw[:200])
        return []


def deduplicate_signals(
    db: Session,
    company_id: str,
    max_age_days: int = 90,
) -> Dict:
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    signals = (
        db.query(Signal)
        .options(selectinload(Signal.document))
        .filter(
            Signal.company_id == company_id,
            Signal.created_at >= cutoff,
        )
        .order_by(Signal.relevance_score.desc())
        .all()
    )

    if not signals:
        return {"merged_count": 0, "removed_ids": [], "kept_signals": []}

    valid_ids = {s.id for s in signals}
    prompt = build_dedup_prompt(signals)
    raw_response = call_llm(prompt)
    merge_groups = _parse_merge_groups(raw_response, valid_ids)

    if not merge_groups:
        return {"merged_count": 0, "removed_ids": [], "kept_signals": []}

    removed_ids = []
    kept_signals_data = []

    for group_ids in merge_groups:
        group_signals = [s for s in signals if s.id in group_ids]
        group_signals.sort(key=lambda s: s.relevance_score or 0, reverse=True)
        primary = group_signals[0]
        others = group_signals[1:]

        for field in ("summary", "why_it_matters"):
            primary_val = getattr(primary, field) or ""
            for other in others:
                other_val = getattr(other, field) or ""
                if len(other_val) > len(primary_val):
                    setattr(primary, field, other_val)
                    primary_val = other_val

        for other in others:
            db.delete(other)
            removed_ids.append(other.id)

        db.commit()
        kept_signals_data.append({
            "id": primary.id,
            "title": primary.title,
            "relevance_score": primary.relevance_score,
        })

    return {
        "merged_count": len(merge_groups),
        "removed_ids": removed_ids,
        "kept_signals": kept_signals_data,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_dedup.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/analyser/dedup.py backend/tests/test_dedup.py
git commit -m "feat: add LLM-powered signal dedup logic with merge support"
```

---

### Task 4: Add deduplicate API endpoint

**Files:**
- Modify: `backend/app/routers/signals.py`
- Modify: `backend/app/schemas/signal.py`
- Test: `backend/tests/test_signals.py`

- [ ] **Step 1: Add the response schema**

Add to `backend/app/schemas/signal.py`:

```python
class DedupResult(BaseModel):
    merged_count: int
    removed_ids: list[str]
    kept_signals: list[dict]
```

- [ ] **Step 2: Add the endpoint to signals router**

Add to `backend/app/routers/signals.py` — import and new endpoint. Add these imports at top:

```python
from app.analyser.dedup import deduplicate_signals
from app.schemas.signal import DedupResult
```

Add this endpoint after the existing routes (before `@router.get("/{signal_id}")`):

```python
@router.post("/deduplicate", response_model=DedupResult)
def deduplicate(
    company_id: str,
    max_age_days: int = 90,
    db: Session = Depends(get_db),
):
    result = deduplicate_signals(db, company_id=company_id, max_age_days=max_age_days)
    return result
```

Important: this must come BEFORE the `@router.get("/{signal_id}")` route, otherwise FastAPI will try to match "deduplicate" as a signal_id.

- [ ] **Step 3: Write the test**

Add to `backend/tests/test_signals.py`:

```python
def test_deduplicate_endpoint(client, db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType

    company = Company(name="ATOSS", slug="atoss-dedup-ep", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/dedup-ep", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc1 = Document(source_id=source.id, url="https://atoss.com/dedup-ep/1", content_hash="hep1")
    doc2 = Document(source_id=source.id, url="https://atoss.com/dedup-ep/2", content_hash="hep2")
    db_session.add_all([doc1, doc2])
    db_session.commit()

    s1 = Signal(
        document_id=doc1.id,
        company_id=company.id,
        title="AI Feature",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    s2 = Signal(
        document_id=doc2.id,
        company_id=company.id,
        title="AI Feature Launch",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.6,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    with patch("app.analyser.dedup.call_llm") as mock_llm:
        mock_llm.return_value = f'{{"merge_groups": [["{s1.id}", "{s2.id}"]]}}'
        response = client.post(f"/api/signals/deduplicate?company_id={company.id}&max_age_days=90")

    assert response.status_code == 200
    data = response.json()
    assert data["merged_count"] == 1
    assert len(data["removed_ids"]) == 1
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_signals.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/signals.py backend/app/schemas/signal.py backend/tests/test_signals.py
git commit -m "feat: add POST /api/signals/deduplicate endpoint"
```

---

### Task 5: Run full test suite and verify

- [ ] **Step 1: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS (51+ existing tests + new ones)

- [ ] **Step 2: Fix any failures**

If any tests fail, debug and fix. Re-run until all pass.

- [ ] **Step 3: Run linter**

Run: `cd backend && python -m ruff check app/ tests/` (or whatever linter is configured)
Expected: No errors

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: resolve test failures from signal dedup feature"
```