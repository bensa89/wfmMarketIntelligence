# Signal Publication Date — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract publication dates from HTML metadata, skip signals from articles older than 1 year, and display `published_at` prominently in the frontend with a clear "Datum unbekannt" indicator when missing.

**Architecture:** The HTML extractor gains a `_extract_published_at` function that reads JSON-LD, Open Graph meta tags, and `<time>` elements. The crawler pipelines persist the date on `Document`. The analyser pipeline applies two age-filter checkpoints (before and after LLM). The frontend uses a shared `formatPublishedAt` util everywhere dates are shown.

**Tech Stack:** Python 3.12, BeautifulSoup4, SQLAlchemy (naive UTC datetimes), React 18 + TypeScript

---

## File Map

| File | Change |
|------|--------|
| `backend/app/crawler/extractor.py` | Add `_parse_date_str`, `_extract_published_at`; add `published_at` field to `ExtractionResult` |
| `backend/app/crawler/pipeline.py` | Set `doc.published_at` from `extraction.published_at` |
| `backend/app/crawler/discovery.py` | Set `doc.published_at` in `_save_and_analyse` |
| `backend/app/analyser/pipeline.py` | Two age-filter checkpoints |
| `backend/tests/test_crawler.py` | Tests for `_extract_published_at` |
| `backend/tests/test_analyser.py` | Tests for age-filter in `analyse_document` |
| `frontend/src/utils/dates.ts` | New: `formatPublishedAt` |
| `frontend/src/components/SignalCard.tsx` | Use `formatPublishedAt` |
| `frontend/src/components/dashboard/SignalFeedTable.tsx` | Use `formatPublishedAt` |
| `frontend/src/pages/Dashboard.tsx` | Update `SignalDocumentModal` |

---

## Task 1: HTML date extraction in extractor

**Files:**
- Modify: `backend/app/crawler/extractor.py`
- Test: `backend/tests/test_crawler.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_crawler.py`:

```python
from datetime import datetime
from app.crawler.extractor import extract_content, _extract_published_at
from bs4 import BeautifulSoup


def test_extract_published_at_from_json_ld():
    html = """<html><head>
    <script type="application/ld+json">
    {"@type": "Article", "datePublished": "2024-03-15T10:00:00+01:00"}
    </script>
    </head><body><p>content</p></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result == datetime(2024, 3, 15, 9, 0, 0)  # UTC, naive


def test_extract_published_at_from_og_meta():
    html = """<html><head>
    <meta property="article:published_time" content="2024-06-01T08:30:00Z"/>
    </head><body><p>content</p></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result == datetime(2024, 6, 1, 8, 30, 0)


def test_extract_published_at_from_time_element():
    html = """<html><body>
    <article><time datetime="2024-09-20">September 20</time><p>body text</p></article>
    </body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result == datetime(2024, 9, 20)


def test_extract_published_at_returns_none_when_no_date():
    html = "<html><body><p>No date here</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_published_at(soup)
    assert result is None


def test_extract_content_sets_published_at():
    html = """<html><head>
    <meta property="article:published_time" content="2025-01-10"/>
    <title>Test Article</title>
    </head><body><main><p>Article body text here</p></main></body></html>"""
    result = extract_content(html, url="https://example.com/article")
    assert result.published_at == datetime(2025, 1, 10)


def test_extract_content_published_at_none_when_missing():
    html = "<html><head><title>T</title></head><body><p>text</p></body></html>"
    result = extract_content(html)
    assert result.published_at is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_crawler.py::test_extract_published_at_from_json_ld tests/test_crawler.py::test_extract_content_sets_published_at -v
```

Expected: `ImportError` or `AttributeError` — `_extract_published_at` does not exist yet.

- [ ] **Step 3: Implement `_extract_published_at` and update `ExtractionResult`**

Replace the full content of `backend/app/crawler/extractor.py`:

```python
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup
from markdownify import markdownify


@dataclass
class ExtractionResult:
    title: Optional[str]
    markdown: str
    content_hash: str
    published_at: Optional[datetime] = None


def _parse_date_str(s: str) -> Optional[datetime]:
    """Parse an ISO-8601 date string into a naive UTC datetime."""
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _extract_published_at(soup: BeautifulSoup) -> Optional[datetime]:
    # 1. JSON-LD datePublished
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict):
                date_str = data.get("datePublished")
                if date_str:
                    dt = _parse_date_str(str(date_str))
                    if dt:
                        return dt
        except (json.JSONDecodeError, AttributeError):
            pass

    # 2. Open Graph article:published_time
    meta = soup.find("meta", attrs={"property": "article:published_time"})
    if meta and meta.get("content"):
        dt = _parse_date_str(meta["content"])
        if dt:
            return dt

    # 3. pubdate / date / DC.date meta
    for name in ("pubdate", "date", "DC.date"):
        meta = soup.find("meta", attrs={"name": name})
        if meta and meta.get("content"):
            dt = _parse_date_str(meta["content"])
            if dt:
                return dt

    # 4. First <time datetime="...">
    time_el = soup.find("time", attrs={"datetime": True})
    if time_el and time_el.get("datetime"):
        dt = _parse_date_str(time_el["datetime"])
        if dt:
            return dt

    return None


def extract_content(html: str, url: str = "") -> ExtractionResult:
    html = html.replace("\x00", "")
    soup = BeautifulSoup(html, "html.parser")

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    published_at = _extract_published_at(soup)

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("body") or soup

    markdown = markdownify(str(main), heading_style="ATX", strip=["a"]).strip()
    markdown = "\n".join(line for line in markdown.splitlines() if line.strip())

    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    return ExtractionResult(
        title=title,
        markdown=markdown,
        content_hash=content_hash,
        published_at=published_at,
    )
```

- [ ] **Step 4: Run all extractor tests**

```bash
cd backend && python -m pytest tests/test_crawler.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd backend && rtk git add app/crawler/extractor.py tests/test_crawler.py && rtk git commit -m "feat: extract published_at from HTML metadata in extractor"
```

---

## Task 2: Persist `published_at` in crawler pipeline

**Files:**
- Modify: `backend/app/crawler/pipeline.py`

- [ ] **Step 1: Update `run_crawl_source` — new document creation**

In `backend/app/crawler/pipeline.py`, find the `Document(...)` constructor in the `else` branch (~line 123) and add `published_at`:

```python
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=datetime.now(timezone.utc),
            published_at=extraction.published_at,
        )
```

- [ ] **Step 2: Update `run_crawl_source` — existing document update**

Find the block where `existing_by_url` is updated (~line 93) and add:

```python
            existing_by_url.title = extraction.title
            existing_by_url.content_markdown = extraction.markdown
            existing_by_url.content_raw_html = fetch_result.html.replace("\x00", "")
            existing_by_url.content_hash = extraction.content_hash
            existing_by_url.crawled_at = datetime.now(timezone.utc)
            existing_by_url.is_analysed = False
            if extraction.published_at and not existing_by_url.published_at:
                existing_by_url.published_at = extraction.published_at
```

- [ ] **Step 3: Run the full test suite to catch regressions**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
cd backend && rtk git add app/crawler/pipeline.py && rtk git commit -m "feat: persist published_at on Document in crawler pipeline"
```

---

## Task 3: Persist `published_at` in discovery pipeline

**Files:**
- Modify: `backend/app/crawler/discovery.py`

- [ ] **Step 1: Update `_save_and_analyse` for new documents**

In `backend/app/crawler/discovery.py`, find `_save_and_analyse` (~line 267). Update the `Document(...)` constructor in the `else` branch:

```python
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html.replace("\x00", ""),
            content_hash=extraction.content_hash,
            crawled_at=now,
            published_at=extraction.published_at,
        )
```

- [ ] **Step 2: Update `_save_and_analyse` for existing documents**

Find where `existing_doc` is updated and add:

```python
    if existing_doc:
        existing_doc.content_markdown = extraction.markdown
        existing_doc.content_hash = extraction.content_hash
        existing_doc.content_raw_html = fetch_result.html.replace("\x00", "")
        existing_doc.crawled_at = now
        existing_doc.is_analysed = False
        if extraction.published_at and not existing_doc.published_at:
            existing_doc.published_at = extraction.published_at
        db.commit()
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_discovery.py tests/test_crawler.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
cd backend && rtk git add app/crawler/discovery.py && rtk git commit -m "feat: persist published_at on Document in discovery pipeline"
```

---

## Task 4: Age filter in analyser pipeline

**Files:**
- Modify: `backend/app/analyser/pipeline.py`
- Test: `backend/tests/test_analyser.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_analyser.py`:

```python
def test_analyse_document_skips_if_published_at_older_than_1_year(db_session):
    from datetime import datetime, timedelta
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="OldCo", slug="oldco-age", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://oldco.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://oldco.com/blog/old-post",
        content_markdown="## Old Article\n" + "Some old content. " * 20,
        content_hash="h_old",
        published_at=datetime.utcnow() - timedelta(days=400),
    )
    db_session.add(doc)
    db_session.commit()

    with patch("app.analyser.pipeline.call_llm") as mock_llm:
        analyse_document(doc, company.id, db_session)
        mock_llm.assert_not_called()

    assert db_session.query(Signal).count() == 0
    assert doc.is_analysed is True


def test_analyse_document_skips_if_llm_published_at_older_than_1_year(db_session):
    from datetime import datetime, timedelta
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="OldCo2", slug="oldco-llm", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://oldco2.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://oldco2.com/blog/mystery-post",
        content_markdown="## Undated Article\n" + "Content without HTML date. " * 20,
        content_hash="h_mystery",
        published_at=None,  # no date from HTML
    )
    db_session.add(doc)
    db_session.commit()

    old_date = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
    llm_response = (
        f'{{"title":"Old News","signal_type":"other","topic":"Old","summary":"Old.",'
        f'"why_it_matters":"Stale.","relevance_score":0.5,"confidence_score":0.5,'
        f'"published_at":"{old_date}"}}'
    )

    with patch("app.analyser.pipeline.call_llm", return_value=llm_response):
        analyse_document(doc, company.id, db_session)

    assert db_session.query(Signal).count() == 0
    assert doc.is_analysed is True


def test_analyse_document_proceeds_if_published_at_recent(db_session):
    from datetime import datetime, timedelta
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="NewCo", slug="newco-age", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://newco.com/blog",
        source_type=SourceType.blog,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://newco.com/blog/new-post",
        content_markdown="## Fresh Article\n" + "Recent content here. " * 20,
        content_hash="h_new_age",
        published_at=datetime.utcnow() - timedelta(days=30),
    )
    db_session.add(doc)
    db_session.commit()

    llm_response = '{"title":"Fresh News","signal_type":"other","topic":"Fresh","summary":"New.","why_it_matters":"Relevant.","relevance_score":0.6,"confidence_score":0.7}'

    with patch("app.analyser.pipeline.call_llm", return_value=llm_response):
        analyse_document(doc, company.id, db_session)

    assert db_session.query(Signal).count() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_analyser.py::test_analyse_document_skips_if_published_at_older_than_1_year tests/test_analyser.py::test_analyse_document_skips_if_llm_published_at_older_than_1_year -v
```

Expected: FAIL — age filter does not exist yet.

- [ ] **Step 3: Implement age filter in `analyse_document`**

Replace the content of `backend/app/analyser/pipeline.py` with:

```python
from datetime import datetime, timezone, timedelta
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


def analyse_document(doc: Document, company_id: str, db: Session) -> None:
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

    # Checkpoint 1: skip if published_at from HTML is older than _MAX_AGE_DAYS
    age_threshold = datetime.utcnow() - timedelta(days=_MAX_AGE_DAYS)
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

    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
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

    prompt = build_analysis_prompt(doc.content_markdown, context)
    raw_response = call_llm(prompt)
    signal_data = parse_llm_response(raw_response)

    if signal_data is None:
        logger.info(
            "Skipping signal creation for doc %s: LLM unable to analyze content",
            doc.id,
        )
        return

    # Checkpoint 2: skip if LLM-detected published_at is older than _MAX_AGE_DAYS
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
```

- [ ] **Step 4: Run all analyser tests**

```bash
cd backend && python -m pytest tests/test_analyser.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd backend && rtk git add app/analyser/pipeline.py tests/test_analyser.py && rtk git commit -m "feat: skip signals from articles older than 1 year"
```

---

## Task 5: Frontend — `formatPublishedAt` util + update date display

**Files:**
- Create: `frontend/src/utils/dates.ts`
- Modify: `frontend/src/components/SignalCard.tsx`
- Modify: `frontend/src/components/dashboard/SignalFeedTable.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx` (`SignalDocumentModal`)

- [ ] **Step 1: Create `frontend/src/utils/dates.ts`**

```typescript
export function formatPublishedAt(publishedAt: string | null): {
  label: string;
  isUnknown: boolean;
} {
  if (!publishedAt) return { label: 'Datum unbekannt', isUnknown: true };
  return {
    label: new Date(publishedAt).toLocaleDateString('de-DE'),
    isUnknown: false,
  };
}
```

- [ ] **Step 2: Update `SignalCard.tsx`**

Replace the `dateStr` line and the date span at the bottom of `frontend/src/components/SignalCard.tsx`:

```tsx
import { formatPublishedAt } from '../utils/dates';
// (add this import at the top alongside existing imports)
```

Replace:
```tsx
  const dateStr = signal.published_at
    ? new Date(signal.published_at).toLocaleDateString('de-DE')
    : new Date(signal.created_at).toLocaleDateString('de-DE');
```

With:
```tsx
  const { label: dateLabel, isUnknown: dateUnknown } = formatPublishedAt(signal.published_at);
```

Replace the date span:
```tsx
        <span>{dateStr}</span>
```

With:
```tsx
        <span className={dateUnknown ? 'italic text-ink-muted/60' : ''}>
          {dateLabel}
        </span>
```

- [ ] **Step 3: Update `SignalFeedTable.tsx`**

Add import at the top of `frontend/src/components/dashboard/SignalFeedTable.tsx`:
```tsx
import { formatPublishedAt } from '../../utils/dates';
```

Replace inside the `signals.map(...)`:
```tsx
        const dateStr = signal.published_at
          ? new Date(signal.published_at).toLocaleDateString('de-DE')
          : new Date(signal.created_at).toLocaleDateString('de-DE');
```

With:
```tsx
        const { label: dateLabel, isUnknown: dateUnknown } = formatPublishedAt(signal.published_at);
```

Replace:
```tsx
            <span className="text-[11px] text-slate-500">{dateStr}</span>
```

With:
```tsx
            <span className={`text-[11px] ${dateUnknown ? 'text-slate-300 italic' : 'text-slate-500'}`}>
              {dateLabel}
            </span>
```

- [ ] **Step 4: Update `SignalDocumentModal` in `Dashboard.tsx`**

Add import at the top of `frontend/src/pages/Dashboard.tsx`:
```tsx
import { formatPublishedAt } from '../utils/dates';
```

Inside `SignalDocumentModal`, replace the `<p>` with the date:
```tsx
            <p className="text-xs text-slate-500 mt-0.5">
              {signal.published_at
                ? new Date(signal.published_at).toLocaleDateString('de-DE')
                : new Date(signal.created_at).toLocaleDateString('de-DE')}
              {signal.source_url && (
                <> · <a href={signal.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Quelle</a></>
              )}
            </p>
```

With:
```tsx
            <p className="text-xs text-slate-500 mt-0.5">
              {(() => {
                const { label, isUnknown } = formatPublishedAt(signal.published_at);
                return (
                  <span className={isUnknown ? 'italic text-slate-300' : ''}>{label}</span>
                );
              })()}
              {signal.source_url && (
                <> · <a href={signal.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Quelle</a></>
              )}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">
              Erfasst: {new Date(signal.created_at).toLocaleDateString('de-DE')}
            </p>
```

- [ ] **Step 5: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd frontend && rtk git add src/utils/dates.ts src/components/SignalCard.tsx src/components/dashboard/SignalFeedTable.tsx src/pages/Dashboard.tsx && rtk git commit -m "feat: show published_at prominently, indicate unknown dates in UI"
```
