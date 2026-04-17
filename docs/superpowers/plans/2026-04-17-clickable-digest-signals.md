# Clickable Digest Signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development ( recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make weekly digest signals clickable so users can navigate directly to the source article/page.

**Architecture:** Expand `DigestRead.key_signals` from `List[str]` (IDs only) to `List[DigestSignalRead]` (full objects with `source_url` and `company_name`). Add `source_url` to `SignalRead` via joined Document relation. Frontend `WeeklyDigest` page renders expanded signals with external links instead of resolving IDs client-side.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (sync), Pydantic v2, React 19, TypeScript, TanStack React Query, Tailwind, Lucide React

---

### Task 1: Add `DigestSignalRead` schema and update `DigestRead`

**Files:**
- Modify: `backend/app/schemas/digest.py`

- [ ] **Step 1: Add `DigestSignalRead` schema and update `DigestRead.key_signals` type**

Edit `backend/app/schemas/digest.py`:

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.signal import SignalType


class DigestSignalRead(BaseModel):
    id: str
    title: str
    signal_type: SignalType
    topic: Optional[str]
    summary: Optional[str]
    relevance_score: Optional[float]
    confidence_score: Optional[float]
    source_url: Optional[str]
    company_name: Optional[str]


class DigestRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    week_start: date
    week_end: date
    summary: Optional[str]
    key_signals: List[DigestSignalRead]
    generated_at: datetime
    is_published: bool
```

- [ ] **Step 2: Run existing digest tests to confirm they break (expected)**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_digests.py -v`
Expected: At least `test_get_digest_by_id` fails because `key_signals` format changed from `List[str]` to `List[DigestSignalRead]`

- [ ] **Step 3: Commit schema changes**

```bash
git add backend/app/schemas/digest.py && git commit -m "feat: add DigestSignalRead schema with source_url and company_name"
```

---

### Task 2: Add `source_url` to `SignalRead` schema

**Files:**
- Modify: `backend/app/schemas/signal.py`

- [ ] **Step 1: Add `source_url` field to `SignalRead`**

Edit `backend/app/schemas/signal.py`:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.signal import SignalType


class SignalRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    document_id: str
    company_id: str
    title: str
    signal_type: SignalType
    topic: Optional[str]
    summary: Optional[str]
    why_it_matters: Optional[str]
    relevance_score: Optional[float]
    confidence_score: Optional[float]
    source_url: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
```

- [ ] **Step 2: Run signal tests to confirm they break (expected)**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_signals.py -v`
Expected: Tests fail because `source_url` is not populated (returns `None` is fine, but the ORM model doesn't have `source_url` so Pydantic's `from_attributes` will fail)

- [ ] **Step 3: Commit schema changes**

```bash
git add backend/app/schemas/signal.py && git commit -m "feat: add source_url to SignalRead schema"
```

---

### Task 3: Update signal router to eager-load Document for `source_url`

**Files:**
- Modify: `backend/app/routers/signals.py`

- [ ] **Step 1: Add `selectinload` to signal queries and populate `source_url`**

Edit `backend/app/routers/signals.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from app.database import get_db
from app.models.signal import Signal, SignalType
from app.schemas.signal import SignalRead

router = APIRouter()


def _to_signal_read(signal: Signal) -> SignalRead:
    return SignalRead(
        id=signal.id,
        document_id=signal.document_id,
        company_id=signal.company_id,
        title=signal.title,
        signal_type=signal.signal_type,
        topic=signal.topic,
        summary=signal.summary,
        why_it_matters=signal.why_it_matters,
        relevance_score=signal.relevance_score,
        confidence_score=signal.confidence_score,
        source_url=signal.document.url if signal.document else None,
        published_at=signal.published_at,
        created_at=signal.created_at,
    )


@router.get("", response_model=List[SignalRead])
def list_signals(
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    min_relevance: Optional[float] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Signal).options(selectinload(Signal.document))
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_relevance is not None:
        query = query.filter(Signal.relevance_score >= min_relevance)
    signals = query.order_by(Signal.created_at.desc()).all()
    return [_to_signal_read(s) for s in signals]


@router.get("/{signal_id}", response_model=SignalRead)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = (
        db.query(Signal)
        .options(selectinload(Signal.document))
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _to_signal_read(signal)
```

- [ ] **Step 2: Run signal tests to verify they pass**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_signals.py -v`
Expected: All tests pass. The `source_url` field appears in responses.

- [ ] **Step 3: Commit router changes**

```bash
git add backend/app/routers/signals.py && git commit -m "feat: populate source_url in signal responses via document relation"
```

---

### Task 4: Update digest router to expand `key_signals` with full signal data

**Files:**
- Modify: `backend/app/routers/digests.py`

- [ ] **Step 1: Update digest endpoints to expand signal IDs into `DigestSignalRead` objects**

Edit `backend/app/routers/digests.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from datetime import date, timedelta
from app.database import get_db
from app.models.digest import WeeklyDigest
from app.models.signal import Signal
from app.schemas.digest import DigestRead, DigestSignalRead

router = APIRouter()


def _expand_key_signals(digest: WeeklyDigest, db: Session) -> List[DigestSignalRead]:
    if not digest.key_signals:
        return []
    signals = (
        db.query(Signal)
        .options(selectinload(Signal.document), selectinload(Signal.company))
        .filter(Signal.id.in_(digest.key_signals))
        .all()
    )
    signal_map = {s.id: s for s in signals}
    result = []
    for sid in digest.key_signals:
        s = signal_map.get(sid)
        if s:
            result.append(
                DigestSignalRead(
                    id=s.id,
                    title=s.title,
                    signal_type=s.signal_type,
                    topic=s.topic,
                    summary=s.summary,
                    relevance_score=s.relevance_score,
                    confidence_score=s.confidence_score,
                    source_url=s.document.url if s.document else None,
                    company_name=s.company.name if s.company else None,
                )
            )
    return result


def _to_digest_read(digest: WeeklyDigest, db: Session) -> DigestRead:
    expanded = _expand_key_signals(digest, db)
    return DigestRead(
        id=digest.id,
        week_start=digest.week_start,
        week_end=digest.week_end,
        summary=digest.summary,
        key_signals=expanded,
        generated_at=digest.generated_at,
        is_published=digest.is_published,
    )


@router.get("", response_model=List[DigestRead])
def list_digests(db: Session = Depends(get_db)):
    digests = db.query(WeeklyDigest).order_by(WeeklyDigest.week_start.desc()).all()
    return [_to_digest_read(d, db) for d in digests]


@router.get("/{digest_id}", response_model=DigestRead)
def get_digest(digest_id: str, db: Session = Depends(get_db)):
    digest = db.query(WeeklyDigest).filter(WeeklyDigest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return _to_digest_read(digest, db)


@router.post(
    "/generate", response_model=DigestRead, status_code=status.HTTP_201_CREATED
)
def generate_digest(db: Session = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    signals = (
        db.query(Signal)
        .options(selectinload(Signal.document), selectinload(Signal.company))
        .filter(Signal.created_at >= week_start)
        .order_by(Signal.relevance_score.desc())
        .limit(10)
        .all()
    )
    key_signal_ids = [s.id for s in signals]

    summary_parts = []
    for s in signals[:5]:
        summary_parts.append(
            f"- {s.title} ({s.signal_type.value}, relevance: {s.relevance_score:.1f})"
        )
    summary = (
        f"Week {week_start} – {week_end}. Top signals:\n" + "\n".join(summary_parts)
        if summary_parts
        else f"No signals for week {week_start}."
    )

    digest = WeeklyDigest(
        week_start=week_start,
        week_end=week_end,
        summary=summary,
        key_signals=key_signal_ids,
        is_published=False,
    )
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return _to_digest_read(digest, db)
```

- [ ] **Step 2: Run digest tests to see which ones need updating**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_digests.py -v`
Expected: Tests fail because `key_signals` is no longer a `List[str]`

- [ ] **Step 3: Commit router changes**

```bash
git add backend/app/routers/digests.py && git commit -m "feat: expand key_signals in digest responses with full signal data"
```

---

### Task 5: Fix digest tests for expanded `key_signals` format

**Files:**
- Modify: `backend/tests/test_digests.py`

- [ ] **Step 1: Update `seed_digest` fixture and test assertions**

Edit `backend/tests/test_digests.py`:

```python
import pytest
from datetime import date
from app.models.digest import WeeklyDigest
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType


@pytest.fixture
def seed_company_and_signals(db_session):
    company = Company(name="TestCo", slug="testco", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id,
        url="https://testco.com/news",
        source_type=SourceType.news,
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://testco.com/news/article-1",
        content_hash="hash1",
    )
    db_session.add(doc)
    db_session.commit()
    s1 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="AI Feature Launch",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    s2 = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="New Partnership",
        signal_type=SignalType.partnership,
        relevance_score=0.5,
    )
    db_session.add_all([s1, s2])
    db_session.commit()
    return company, doc, s1, s2


@pytest.fixture
def seed_digest(db_session, seed_company_and_signals):
    _, _, s1, s2 = seed_company_and_signals
    d = WeeklyDigest(
        week_start=date(2026, 4, 14),
        week_end=date(2026, 4, 20),
        summary="Big week in AI WFM.",
        key_signals=[s1.id, s2.id],
        is_published=True,
    )
    db_session.add(d)
    db_session.commit()
    return d


def test_list_digests(client, seed_digest):
    response = client.get("/api/digests")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_digest_by_id(client, seed_digest, seed_company_and_signals):
    _, _, s1, s2 = seed_company_and_signals
    response = client.get(f"/api/digests/{seed_digest.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Big week in AI WFM."
    assert len(data["key_signals"]) == 2
    assert data["key_signals"][0]["id"] == s1.id
    assert data["key_signals"][0]["title"] == "AI Feature Launch"
    assert data["key_signals"][0]["signal_type"] == "ai_announcement"
    assert data["key_signals"][0]["source_url"] == "https://testco.com/news/article-1"
    assert data["key_signals"][0]["company_name"] == "TestCo"


def test_digest_key_signals_have_source_url(client, seed_digest, seed_company_and_signals):
    response = client.get(f"/api/digests/{seed_digest.id}")
    data = response.json()
    for sig in data["key_signals"]:
        assert "source_url" in sig
        assert sig["source_url"] is not None


def test_generate_digest(client):
    response = client.post("/api/digests/generate")
    assert response.status_code == 201
    data = response.json()
    assert "week_start" in data
    assert "week_end" in data
    assert isinstance(data["key_signals"], list)
```

- [ ] **Step 2: Run digest tests and verify they pass**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_digests.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit test updates**

```bash
git add backend/tests/test_digests.py && git commit -m "test: update digest tests for expanded key_signals format"
```

---

### Task 6: Update signal tests for `source_url`

**Files:**
- Modify: `backend/tests/test_signals.py`

- [ ] **Step 1: Add assertion for `source_url` in signal responses**

Edit `backend/tests/test_signals.py`, add after the existing `test_get_signal_by_id` test:

```python
def test_signal_has_source_url(client, seed_signals):
    _, s1, _ = seed_signals
    response = client.get(f"/api/signals/{s1.id}")
    assert response.status_code == 200
    data = response.json()
    assert "source_url" in data
    assert data["source_url"] == "https://atoss.com/sigs/1"


def test_list_signals_have_source_url(client, seed_signals):
    response = client.get("/api/signals")
    assert response.status_code == 200
    for sig in response.json():
        assert "source_url" in sig
```

- [ ] **Step 2: Run signal tests and verify they pass**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/test_signals.py -v`
Expected: All tests pass including new ones

- [ ] **Step 3: Commit test updates**

```bash
git add backend/tests/test_signals.py && git commit -m "test: add source_url assertions to signal tests"
```

---

### Task 7: Run full test suite

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/ -v`
Expected: All 51+ tests pass (including new ones)

- [ ] **Step 2: Fix any failures if needed, then commit**

---

### Task 8: Update frontend TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add `DigestSignal` interface and update `Digest` interface**

Edit `frontend/src/types/index.ts`:

Add `DigestSignal` interface before the `Digest` interface (around line 91):

```typescript
export interface DigestSignal {
  id: string;
  title: string;
  signal_type: SignalType;
  topic: string | null;
  summary: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  source_url: string | null;
  company_name: string | null;
}
```

Change `Digest` interface's `key_signals` field:

```typescript
export interface Digest {
  id: string;
  week_start: string;
  week_end: string;
  summary: string | null;
  key_signals: DigestSignal[];
  generated_at: string;
  is_published: boolean;
}
```

Also add `source_url` to the `Signal` interface:

```typescript
export interface Signal {
  id: string;
  document_id: string;
  company_id: string;
  title: string;
  signal_type: SignalType;
  topic: string | null;
  summary: string | null;
  why_it_matters: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  source_url: string | null;
  published_at: string | null;
  created_at: string;
}
```

- [ ] **Step 2: Commit type changes**

```bash
git add frontend/src/types/index.ts && git commit -m "feat: add DigestSignal type, update Digest.key_signals and Signal.source_url"
```

---

### Task 9: Update `WeeklyDigest` page — remove `useSignals`, render clickable signals

**Files:**
- Modify: `frontend/src/pages/WeeklyDigest.tsx`

- [ ] **Step 1: Rewrite `WeeklyDigest.tsx` to use expanded signals with external links**

Edit `frontend/src/pages/WeeklyDigest.tsx`:

```tsx
import { useDigests, useGenerateDigest } from '../hooks/useDigests';
import RelevanceBadge from '../components/RelevanceBadge';
import SignalTypeIcon from '../components/SignalTypeIcon';
import { Calendar, RefreshCw, ExternalLink } from 'lucide-react';

export default function WeeklyDigest() {
  const { data: digests, isLoading } = useDigests();
  const generateDigest = useGenerateDigest();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Calendar size={24} /> Weekly Digest
        </h1>
        <button
          onClick={() => generateDigest.mutate()}
          disabled={generateDigest.isPending}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw size={16} className={generateDigest.isPending ? 'animate-spin' : ''} />
          {generateDigest.isPending ? 'Generating...' : 'Generate New Digest'}
        </button>
      </div>

      {generateDigest.isError && (
        <div className="mb-4 p-3 rounded bg-signal-low/10 text-signal-low text-sm">
          Failed to generate digest. Try again.
        </div>
      )}

      {isLoading ? (
        <p className="text-dark-muted">Loading digests...</p>
      ) : digests?.length === 0 ? (
        <div className="card text-center py-8">
          <Calendar size={48} className="mx-auto text-dark-muted mb-3" />
          <p className="text-dark-muted">No digests yet. Generate one to get started.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {digests?.map((digest) => (
            <div key={digest.id} className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">
                  {digest.week_start} — {digest.week_end}
                </h2>
                <span className={`text-xs px-2 py-0.5 rounded ${digest.is_published ? 'bg-signal-high/20 text-signal-high' : 'bg-dark-bg text-dark-muted'}`}>
                  {digest.is_published ? 'Published' : 'Draft'}
                </span>
              </div>
              {digest.summary && (
                <div className="text-sm text-dark-text whitespace-pre-line mb-4">
                  {digest.summary}
                </div>
              )}
              {digest.key_signals.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-dark-muted mb-2">Key Signals:</h3>
                  <div className="space-y-2">
                    {digest.key_signals.map((signal) => (
                      <div
                        key={signal.id}
                        className="flex items-center justify-between bg-dark-bg rounded p-2"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <SignalTypeIcon type={signal.signal_type} size={14} />
                          {signal.source_url ? (
                            <a
                              href={signal.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm hover:text-dark-accent transition-colors truncate flex items-center gap-1"
                            >
                              {signal.title}
                              <ExternalLink size={12} className="shrink-0 opacity-50" />
                            </a>
                          ) : (
                            <span className="text-sm truncate">{signal.title}</span>
                          )}
                          {signal.company_name && (
                            <span className="text-xs text-dark-muted shrink-0">({signal.company_name})</span>
                          )}
                        </div>
                        <RelevanceBadge score={signal.relevance_score} size="sm" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify the frontend builds without errors**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit`
Expected: No TypeScript errors

- [ ] **Step 3: Commit frontend changes**

```bash
git add frontend/src/pages/WeeklyDigest.tsx && git commit -m "feat: render clickable source links in weekly digest signals"
```

---

### Task 10: Final verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend typecheck**

Run: `cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Verify no other files reference the old `key_signals: string[]` type that need updating**

Search for any remaining references to `key_signals` as string array in frontend code and update if found.