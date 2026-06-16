# Events Source Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `events` SourceType that splits a competitor's HTML events listing page into one Document per event section, so each gets its own Signal with a populated `event_date`.

**Architecture:** When `source.source_type == SourceType.events`, `run_crawl_source` calls a new `split_event_sections()` function instead of the normal single-document path. The splitter finds repeated HTML blocks containing a date pattern + heading and creates one document per block with a synthetic URL (`{source_url}#section-{i}`) and a parsed `published_at`. The existing `_save_event_documents` path (used for SPA API interception) remains unchanged.

**Tech Stack:** Python, BeautifulSoup4, SQLAlchemy, Alembic, PostgreSQL, React/TypeScript

---

## File Map

| File | Change |
|------|--------|
| `backend/app/models/source.py` | Add `events = "events"` to `SourceType` |
| `backend/alembic/versions/XXXX_add_events_source_type.py` | Migration: add enum value in Postgres |
| `backend/app/crawler/extractor.py` | Add `split_event_sections(html, base_url)` |
| `backend/app/crawler/pipeline.py` | Branch on `SourceType.events` in `run_crawl_source` |
| `backend/tests/test_crawler.py` | Tests for `split_event_sections` |
| `frontend/src/types/index.ts` | Add `'events'` to `SourceType` union |
| `frontend/src/pages/SourcesAdmin.tsx` | Add `'events'` to `sourceTypes` array |

---

## Task 1: Add `events` to SourceType enum

**Files:**
- Modify: `backend/app/models/source.py`

- [ ] **Step 1: Write the failing test** (in `backend/tests/test_crawler.py`)

```python
def test_source_type_events_exists():
    from app.models.source import SourceType
    assert SourceType.events == "events"
```

- [ ] **Step 2: Run to confirm it fails**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_crawler.py::test_source_type_events_exists -v
```
Expected: `FAILED — AttributeError: events`

- [ ] **Step 3: Add enum value**

In `backend/app/models/source.py`, extend the enum:

```python
class SourceType(str, enum.Enum):
    news = "news"
    blog = "blog"
    product = "product"
    press = "press"
    jobs = "jobs"
    events = "events"   # ← add this line
```

- [ ] **Step 4: Run test**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_crawler.py::test_source_type_events_exists -v
```
Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/source.py
git commit -m "feat: add events value to SourceType enum"
```

---

## Task 2: Alembic migration — add enum value to PostgreSQL

**Files:**
- Create: `backend/alembic/versions/XXXX_add_events_source_type.py`

PostgreSQL `ALTER TYPE … ADD VALUE` cannot run inside a transaction, so we must use `execute_if` with raw SQL outside the transaction block.

- [ ] **Step 1: Generate migration skeleton**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add_events_source_type"
```

Note the generated filename — it will look like `backend/alembic/versions/XXXX_add_events_source_type.py`.

- [ ] **Step 2: Replace generated body with manual enum migration**

Open the generated file and replace `upgrade()` and `downgrade()` with:

```python
from alembic import op


def upgrade() -> None:
    # ADD VALUE cannot run inside a transaction in PostgreSQL
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'events'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op
    pass
```

- [ ] **Step 3: Apply migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```
Expected: no errors, migration applies cleanly.

- [ ] **Step 4: Verify in DB**

```bash
docker compose -f docker-compose.dev.yml exec backend python -c "
from app.database import SessionLocal
from app.models.source import Source, SourceType
from app.models.company import Company, CompanyType
db = SessionLocal()
co = Company(name='_test_events', slug='_test-events-enum', type=CompanyType.competitor)
db.add(co)
db.commit()
src = Source(company_id=co.id, url='https://example.com/events/', source_type=SourceType.events)
db.add(src)
db.commit()
print('OK — events source created:', src.id)
db.delete(src); db.delete(co); db.commit()
db.close()
"
```
Expected: `OK — events source created: <uuid>`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: migrate postgres enum to include events source type"
```

---

## Task 3: HTML event-section splitter

**Files:**
- Modify: `backend/app/crawler/extractor.py`

The splitter finds candidate containers (`<article>`, `<section>`, `<li>`) whose text contains a date pattern AND a heading (`<h1>`–`<h4>`). Returns a list of dicts with `html`, `title`, `date_str`.

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_crawler.py`)

```python
def test_split_event_sections_finds_articles_with_dates():
    from app.crawler.extractor import split_event_sections
    html = """
    <html><body><main>
      <article>
        <h2>Brain Snacks</h2>
        <p>22. Januar 2026 – Workshop im TOPGOLF Oberhausen zum Thema Workforce Management.</p>
      </article>
      <article>
        <h2>HR Summit Berlin</h2>
        <p>15. März 2026 – Jahreskonferenz für HR-Entscheider in Berlin. Drei Tracks, 20 Speaker.</p>
      </article>
    </main></body></html>
    """
    sections = split_event_sections(html, "https://example.com/events/")
    assert len(sections) == 2
    assert sections[0]["title"] == "Brain Snacks"
    assert sections[0]["date_str"] is not None
    assert "Januar" in sections[0]["date_str"] or "2026" in sections[0]["date_str"]
    assert sections[1]["title"] == "HR Summit Berlin"


def test_split_event_sections_returns_empty_when_no_dates():
    from app.crawler.extractor import split_event_sections
    html = """
    <html><body><main>
      <article><h2>About us</h2><p>We are a software company.</p></article>
      <article><h2>Contact</h2><p>Reach us at info@example.com.</p></article>
    </main></body></html>
    """
    sections = split_event_sections(html, "https://example.com/")
    assert sections == []


def test_split_event_sections_falls_back_when_no_containers():
    from app.crawler.extractor import split_event_sections
    html = "<html><body><p>22. Januar 2026 – Just one paragraph with a date.</p></body></html>"
    sections = split_event_sections(html, "https://example.com/events/")
    # No repeated container structure → returns empty list so caller uses fallback
    assert sections == []
```

- [ ] **Step 2: Run to confirm they fail**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_crawler.py::test_split_event_sections_finds_articles_with_dates tests/test_crawler.py::test_split_event_sections_returns_empty_when_no_dates tests/test_crawler.py::test_split_event_sections_falls_back_when_no_containers -v
```
Expected: `ImportError: cannot import name 'split_event_sections'`

- [ ] **Step 3: Implement `split_event_sections` in `backend/app/crawler/extractor.py`**

Add these imports at the top of the file (after existing imports):

```python
import re
from typing import List
```

Add the function at the end of the file:

```python
_DATE_RE = re.compile(
    r"\b\d{1,2}\.\s*(?:januar|februar|märz|april|mai|juni|juli|august|"
    r"september|oktober|november|dezember|january|february|march|"
    r"april|may|june|july|august|september|october|november|december)"
    r"\s+\d{4}\b"
    r"|\b\d{1,2}\.\d{1,2}\.\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)

_MONTH_DE = {
    "januar": "01", "februar": "02", "märz": "03", "april": "04",
    "mai": "05", "juni": "06", "juli": "07", "august": "08",
    "september": "09", "oktober": "10", "november": "11", "dezember": "12",
}
_MONTH_EN = {
    "january": "01", "february": "02", "march": "03", "may": "05",
    "june": "06", "july": "07", "october": "10",
}
_MONTH_MAP = {**_MONTH_DE, **_MONTH_EN}


def _parse_date_from_text(text: str) -> Optional[datetime]:
    m = _DATE_RE.search(text)
    if not m:
        return None
    raw = m.group(0).strip()
    # ISO format
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        pass
    # DD.MM.YYYY
    try:
        return datetime.strptime(raw, "%d.%m.%Y")
    except ValueError:
        pass
    # "22. Januar 2026" or "22. january 2026"
    parts = re.split(r"[\.\s]+", raw.lower())
    parts = [p for p in parts if p]
    if len(parts) == 3:
        day, month_name, year = parts
        month_num = _MONTH_MAP.get(month_name)
        if month_num:
            try:
                return datetime.strptime(f"{day}.{month_num}.{year}", "%d.%m.%Y")
            except ValueError:
                pass
    return None


def split_event_sections(html: str, base_url: str) -> List[dict]:
    """
    Parse an HTML events listing page and return one dict per event section.
    Each dict has: html (str), title (str), date_str (str | None), parsed_date (datetime | None).
    Returns [] if fewer than 2 qualifying sections are found (caller should fall back).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove boilerplate
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    main = soup.find("main") or soup.find("body") or soup

    # Candidate container tags — try most specific first
    for tag_name in ("article", "section", "li"):
        containers = main.find_all(tag_name)
        qualifying = []
        for c in containers:
            text = c.get_text(" ", strip=True)
            if len(text.split()) < 10:
                continue
            if not _DATE_RE.search(text):
                continue
            heading = c.find(["h1", "h2", "h3", "h4"])
            if not heading:
                continue
            title = heading.get_text(" ", strip=True)
            date_match = _DATE_RE.search(text)
            date_str = date_match.group(0) if date_match else None
            parsed_date = _parse_date_from_text(text)
            qualifying.append({
                "html": f"<html><body><main>{c}</main></body></html>",
                "title": title,
                "date_str": date_str,
                "parsed_date": parsed_date,
            })
        if len(qualifying) >= 2:
            return qualifying

    return []
```

- [ ] **Step 4: Run tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_crawler.py::test_split_event_sections_finds_articles_with_dates tests/test_crawler.py::test_split_event_sections_returns_empty_when_no_dates tests/test_crawler.py::test_split_event_sections_falls_back_when_no_containers -v
```
Expected: all 3 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/extractor.py backend/tests/test_crawler.py
git commit -m "feat: add split_event_sections HTML event-block parser"
```

---

## Task 4: Wire events source type into `run_crawl_source`

**Files:**
- Modify: `backend/app/crawler/pipeline.py`

When `source.source_type == SourceType.events`, call `split_event_sections`. If sections are found, create one Document per section (same pattern as `_save_event_documents`). If sections come back empty, fall through to normal single-document flow so nothing breaks.

- [ ] **Step 1: Add import at top of `backend/app/crawler/pipeline.py`**

The file already imports `from app.models.source import Source, CrawlStatus, AnalysisStatus`. Add `SourceType` to that import:

```python
from app.models.source import Source, CrawlStatus, AnalysisStatus, SourceType
```

- [ ] **Step 2: Add `_save_html_event_sections` function** (after `_save_event_documents`, before `run_crawl_source`)

```python
def _save_html_event_sections(source: Source, fetch_result, sections: list, db: Session) -> int:
    """Create or update one Document per HTML event section. Returns count of new/changed docs."""
    new = 0
    changed = 0
    now = datetime.now(timezone.utc)

    for i, section in enumerate(sections):
        section_url = f"{fetch_result.final_url}#section-{i}"
        extraction = extract_content(section["html"], url=section_url)

        if len(extraction.markdown.split()) < _MIN_CONTENT_WORDS:
            logger.debug("Skipping HTML event section %d: too short", i)
            continue

        title = section["title"] or extraction.title or "Event"
        published_at = section.get("parsed_date")

        try:
            existing = db.query(Document).filter(Document.url == section_url).first()
            if existing:
                if existing.content_hash == extraction.content_hash:
                    logger.debug("HTML event section unchanged: %s", title)
                    continue
                existing.title = title
                existing.content_markdown = extraction.markdown
                existing.content_raw_html = section["html"]
                existing.content_hash = extraction.content_hash
                existing.crawled_at = now
                existing.is_analysed = False
                if published_at and not existing.published_at:
                    existing.published_at = published_at
                db.commit()
                changed += 1
                logger.info("Updated HTML event section: %s", title)
            else:
                doc = Document(
                    source_id=source.id,
                    url=section_url,
                    title=title,
                    content_markdown=extraction.markdown,
                    content_raw_html=section["html"],
                    content_hash=extraction.content_hash,
                    crawled_at=now,
                    published_at=published_at,
                )
                db.add(doc)
                db.commit()
                new += 1
                logger.info(
                    "New HTML event section: %s (date=%s)",
                    title,
                    published_at.date() if published_at else "unknown",
                )
        except Exception:
            db.rollback()
            logger.exception("Failed to save HTML event section %d for %s", i, section_url)

    logger.info(
        "HTML event sections for %s: %d new, %d changed out of %d sections",
        source.url, new, changed, len(sections),
    )
    return new + changed
```

- [ ] **Step 3: Branch in `run_crawl_source`**

In `run_crawl_source`, the current block starts with `if fetch_result.events:`. Add an `elif` branch immediately after that block (before the `else:` that handles normal documents):

```python
    elif source.source_type == SourceType.events:
        from app.crawler.extractor import split_event_sections
        sections = split_event_sections(fetch_result.html, fetch_result.final_url)
        if sections:
            logger.info(
                "Events source %s: found %d HTML sections — creating per-section documents",
                source.url, len(sections),
            )
            n = _save_html_event_sections(source, fetch_result, sections, db)
            result["new_documents"] += n
            if n > 0:
                source.crawl_status = CrawlStatus.new
                source.analysis_status = AnalysisStatus.pending
            else:
                source.crawl_status = CrawlStatus.known
            db.commit()
        else:
            logger.info(
                "Events source %s: no splittable sections found — falling back to single document",
                source.url,
            )
            # fall through to normal single-document extraction
            word_count = len(extraction.markdown.split())
            if word_count < _MIN_CONTENT_WORDS:
                logger.info(
                    "Skipping document for %s: only %d words after extraction",
                    fetch_result.final_url, word_count,
                )
                result["skipped"] += 1
            else:
                existing_by_url = db.query(Document).filter(Document.url == fetch_result.final_url).first()
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
                        if extraction.published_at and not existing_by_url.published_at:
                            existing_by_url.published_at = extraction.published_at
                        source.crawl_status = CrawlStatus.changed
                        source.content_hash = extraction.content_hash
                        source.last_changed_at = datetime.now(timezone.utc)
                        source.analysis_status = AnalysisStatus.pending
                        db.commit()
                        result["new_documents"] += 1
                else:
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
                    db.add(doc)
                    source.crawl_status = CrawlStatus.new
                    source.content_hash = extraction.content_hash
                    source.analysis_status = AnalysisStatus.pending
                    db.commit()
                    result["new_documents"] += 1
```

- [ ] **Step 4: Manual smoke test** — add plano-wfm as an `events` source and trigger a crawl. Check logs for:

```
Events source https://plano-wfm.com/de-de/events/: found N HTML sections — creating per-section documents
New HTML event section: Brain Snacks (date=2026-01-22)
Signal created — type=event_or_thought_leadership title='Brain Snacks' relevance=... event_date=2026-01-22
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/pipeline.py
git commit -m "feat: split HTML events listing pages into per-section documents when source_type=events"
```

---

## Task 5: Frontend — add `events` to SourceType

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/pages/SourcesAdmin.tsx`

- [ ] **Step 1: Update type union in `frontend/src/types/index.ts` line 28**

```typescript
export type SourceType = 'news' | 'blog' | 'product' | 'press' | 'jobs' | 'events';
```

- [ ] **Step 2: Add `'events'` to `sourceTypes` array in `frontend/src/pages/SourcesAdmin.tsx` line 14**

```typescript
const sourceTypes: SourceType[] = ['news', 'blog', 'product', 'press', 'jobs', 'events'];
```

- [ ] **Step 3: Verify no TypeScript errors**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/pages/SourcesAdmin.tsx
git commit -m "feat: add events option to SourceType in frontend"
```

---

## Self-Review

**Spec coverage:**
- ✅ `events` SourceType in backend enum
- ✅ Postgres migration (ADD VALUE IF NOT EXISTS, outside transaction)
- ✅ `split_event_sections` with German + English date regex, heading detection
- ✅ `_save_html_event_sections` with dedup by URL+hash
- ✅ `run_crawl_source` branches on `SourceType.events`, falls back gracefully
- ✅ Frontend type + dropdown updated
- ✅ Tests for splitter (positive, no-date, no-container)

**No placeholders:** all code blocks complete.

**Type consistency:** `split_event_sections` returns `List[dict]` with keys `html`, `title`, `date_str`, `parsed_date` — used consistently in `_save_html_event_sections`.
