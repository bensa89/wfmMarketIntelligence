# Intelligence Briefing Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent, LLM-generated intelligence briefing to the Overview page that summarises changes since the last crawl, with strategic overview and actionable recommendations.

**Architecture:** New `IntelligenceBriefing` DB model + generator in `backend/app/assessor/intel_briefing.py` that queries recent Signals + SignalAssessments. Two new endpoints under `/api/intelligence/briefing/`. Frontend hook + component displayed at the top of `OverviewPage`.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), Alembic (migration), React 18/TypeScript/TanStack Query (frontend), existing `call_llm` + `MarkdownViewer`.

---

## File Map

**Create:**
- `backend/app/models/intelligence_briefing.py` — SQLAlchemy model
- `backend/app/schemas/intelligence_briefing.py` — Pydantic read schema
- `backend/app/assessor/intel_briefing.py` — LLM generator function
- `backend/app/routers/intelligence_briefing.py` — GET /latest + POST /generate
- `backend/alembic/versions/<hash>_add_intelligence_briefings.py` — migration
- `backend/tests/test_intelligence_briefing_router.py` — router tests
- `frontend/src/hooks/useIntelligenceBriefing.ts` — TanStack Query hooks
- `frontend/src/components/overview/IntelligenceBriefingPanel.tsx` — UI component

**Modify:**
- `backend/app/models/__init__.py` — add IntelligenceBriefing import/export
- `backend/app/main.py` — register new router
- `frontend/src/types/intelligence.ts` — add IntelligenceBriefing type
- `frontend/src/pages/OverviewPage.tsx` — mount panel at top

---

### Task 1: DB Model + Schema

**Files:**
- Create: `backend/app/models/intelligence_briefing.py`
- Create: `backend/app/schemas/intelligence_briefing.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the model**

```python
# backend/app/models/intelligence_briefing.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime
from app.database import Base


class IntelligenceBriefing(Base):
    __tablename__ = "intelligence_briefings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    signal_count = Column(Integer, nullable=False, default=0)
    assessment_count = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Create the schema**

```python
# backend/app/schemas/intelligence_briefing.py
from pydantic import BaseModel
from datetime import datetime


class IntelligenceBriefingRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    content: str
    signal_count: int
    assessment_count: int
    generated_at: datetime
```

- [ ] **Step 3: Register model in `__init__.py`**

Add after the `CrawlBriefing` line:
```python
from app.models.intelligence_briefing import IntelligenceBriefing
```

And add `"IntelligenceBriefing"` to `__all__`.

- [ ] **Step 4: Commit**

```bash
rtk git add backend/app/models/intelligence_briefing.py backend/app/schemas/intelligence_briefing.py backend/app/models/__init__.py
rtk git commit -m "feat: add IntelligenceBriefing model and schema"
```

---

### Task 2: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/<hash>_add_intelligence_briefings.py`

- [ ] **Step 1: Generate migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add_intelligence_briefings"
```

Expected output: `Generating .../versions/<hash>_add_intelligence_briefings.py`

- [ ] **Step 2: Verify generated migration**

Open the generated file and confirm it contains:
```python
op.create_table('intelligence_briefings',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('signal_count', sa.Integer(), nullable=False),
    sa.Column('assessment_count', sa.Integer(), nullable=False),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
)
```

- [ ] **Step 3: Apply migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Expected output ends with: `Running upgrade ... -> <hash>, add_intelligence_briefings`

- [ ] **Step 4: Commit**

```bash
rtk git add backend/alembic/versions/
rtk git commit -m "feat: migration for intelligence_briefings table"
```

---

### Task 3: Generator

**Files:**
- Create: `backend/app/assessor/intel_briefing.py`

- [ ] **Step 1: Create the generator**

```python
# backend/app/assessor/intel_briefing.py
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.analyser.client import call_llm
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.company import Company
from app.models.context import InternalCompanyContext


def _build_prompt(signals: list, assessments: list, context: dict) -> str:
    company_names = sorted({s["company"] for s in signals})
    strong = [a for a in assessments if a["movement_strength"] in ("market_shaping", "strong")]
    strong.sort(key=lambda a: a["movement_score"] or 0, reverse=True)

    cap_counts: dict[str, int] = {}
    for a in assessments:
        if a["capability_primary"]:
            cap_counts[a["capability_primary"]] = cap_counts.get(a["capability_primary"], 0) + 1
    top_caps = sorted(cap_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    lines = [
        "Du bist ein strategischer Market Intelligence Analyst für ein WFM-Softwareunternehmen.",
        "Analysiere die folgenden Wettbewerbsbewegungen seit dem letzten Crawl und erstelle ein strukturiertes Briefing.",
        "",
        f"Zeitraum: letzte 24 Stunden",
        f"Neue Signale: {len(signals)}",
        f"Bewertete Signale: {len(assessments)}",
        f"Beteiligte Unternehmen: {', '.join(company_names)}",
        "",
    ]

    if context.get("core_capabilities"):
        lines += [
            f"Unsere Kernkompetenzen: {', '.join(context['core_capabilities'])}",
            f"Strategische Prioritäten: {', '.join(context.get('strategic_priorities', []))}",
            "",
        ]

    if strong:
        lines += ["Starke / marktprägende Bewegungen:"]
        for a in strong[:8]:
            lines.append(f"  [{a['company']}] {a['title']}")
            lines.append(f"    Stärke: {a['movement_strength']} | Score: {a['movement_score']} | Capability: {a['capability_primary']}")
            if a["assessment_summary"]:
                lines.append(f"    Assessment: {a['assessment_summary']}")
            if a["implication_for_us"]:
                lines.append(f"    → Für uns: {a['implication_for_us']}")
        lines.append("")

    if top_caps:
        lines += ["Aktivste Capability-Bereiche:"]
        for cap, count in top_caps:
            lines.append(f"  - {cap}: {count} Signale")
        lines.append("")

    lines += [
        "Erstelle exakt dieses Markdown-Dokument (kein Prosa außerhalb der Abschnitte):",
        "",
        "## Strategischer Überblick",
        "[2–3 Sätze: Welche Wettbewerber bewegen sich wie? Was ist die übergeordnete Stoßrichtung?]",
        "",
        "## Handlungsempfehlungen",
        "| Priorität | Signal | Unternehmen | Empfehlung |",
        "|-----------|--------|-------------|------------|",
        "| #1 | ... | ... | ... |",
        "| #2 | ... | ... | ... |",
        "| #3 | ... | ... | ... |",
        "",
        "Maximal 3 Handlungsempfehlungen. Fokus auf konkrete, umsetzbare Maßnahmen für unser Produkt- oder GTM-Team.",
    ]
    return "\n".join(lines)


def generate_intelligence_briefing(db: Session) -> tuple[str, int, int]:
    """Returns (content, signal_count, assessment_count)."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    signals_rows = (
        db.query(Signal, Company.name)
        .join(Company, Company.id == Signal.company_id)
        .filter(Signal.created_at >= since)
        .order_by(Signal.created_at.desc())
        .all()
    )

    signal_ids = [s.id for s, _ in signals_rows]
    assessments_rows = (
        db.query(SignalAssessment, Signal.title, Company.name)
        .join(Signal, Signal.id == SignalAssessment.signal_id)
        .join(Company, Company.id == SignalAssessment.company_id)
        .filter(SignalAssessment.signal_id.in_(signal_ids))
        .order_by(SignalAssessment.movement_score.desc().nullslast())
        .all()
    ) if signal_ids else []

    signals_data = [
        {"company": name, "title": s.title}
        for s, name in signals_rows
    ]
    assessments_data = [
        {
            "company": cname,
            "title": title,
            "movement_strength": a.movement_strength.value if a.movement_strength else None,
            "movement_score": a.movement_score,
            "capability_primary": a.capability_primary,
            "assessment_summary": a.assessment_summary,
            "implication_for_us": a.implication_for_us,
        }
        for a, title, cname in assessments_rows
    ]

    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
            "core_capabilities": ctx_record.core_capabilities or [],
            "strategic_priorities": ctx_record.strategic_priorities or [],
        }

    prompt = _build_prompt(signals_data, assessments_data, context)
    content = call_llm(prompt, max_tokens=2048)
    return content, len(signals_data), len(assessments_data)
```

- [ ] **Step 2: Commit**

```bash
rtk git add backend/app/assessor/intel_briefing.py
rtk git commit -m "feat: add intelligence briefing generator"
```

---

### Task 4: Router + main.py registration

**Files:**
- Create: `backend/app/routers/intelligence_briefing.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

```python
# backend/app/routers/intelligence_briefing.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intelligence_briefing import IntelligenceBriefing
from app.schemas.intelligence_briefing import IntelligenceBriefingRead
from app.assessor.intel_briefing import generate_intelligence_briefing

router = APIRouter()


@router.get("/latest", response_model=IntelligenceBriefingRead)
def get_latest(db: Session = Depends(get_db)):
    briefing = (
        db.query(IntelligenceBriefing)
        .order_by(IntelligenceBriefing.generated_at.desc())
        .first()
    )
    if not briefing:
        raise HTTPException(status_code=404, detail="No intelligence briefing found")
    return briefing


@router.post("/generate", response_model=IntelligenceBriefingRead)
def generate(db: Session = Depends(get_db)):
    content, signal_count, assessment_count = generate_intelligence_briefing(db)
    briefing = IntelligenceBriefing(
        content=content,
        signal_count=signal_count,
        assessment_count=assessment_count,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing
```

- [ ] **Step 2: Register in `main.py`**

In the imports block, add after the `briefings` import:
```python
from app.routers import (
    ...
    briefings,
    intelligence,
    intelligence_briefing,   # add this
)
```

After the existing `briefings` router line, add:
```python
app.include_router(intelligence_briefing.router, prefix="/api/intelligence/briefing", tags=["intelligence-briefing"])
```

- [ ] **Step 3: Commit**

```bash
rtk git add backend/app/routers/intelligence_briefing.py backend/app/main.py
rtk git commit -m "feat: add intelligence briefing router and register in main"
```

---

### Task 5: Router Tests

**Files:**
- Create: `backend/tests/test_intelligence_briefing_router.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_intelligence_briefing_router.py
from unittest.mock import patch
from datetime import datetime, timezone
from app.models.intelligence_briefing import IntelligenceBriefing


def test_get_latest_404_when_none(client):
    response = client.get("/api/intelligence/briefing/latest")
    assert response.status_code == 404


def test_get_latest_returns_most_recent(client, db_session):
    older = IntelligenceBriefing(
        content="old briefing",
        signal_count=5,
        assessment_count=3,
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = IntelligenceBriefing(
        content="new briefing",
        signal_count=10,
        assessment_count=8,
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get("/api/intelligence/briefing/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "new briefing"
    assert data["signal_count"] == 10
    assert data["assessment_count"] == 8


def test_generate_creates_and_returns_briefing(client):
    with patch(
        "app.routers.intelligence_briefing.generate_intelligence_briefing",
        return_value=("## Strategischer Überblick\nTest.", 12, 9),
    ):
        response = client.post("/api/intelligence/briefing/generate")

    assert response.status_code == 200
    data = response.json()
    assert "Strategischer Überblick" in data["content"]
    assert data["signal_count"] == 12
    assert data["assessment_count"] == 9
    assert data["id"] is not None
    assert data["generated_at"] is not None


def test_generate_persists_briefing(client, db_session):
    with patch(
        "app.routers.intelligence_briefing.generate_intelligence_briefing",
        return_value=("Briefing content", 3, 2),
    ):
        client.post("/api/intelligence/briefing/generate")

    stored = db_session.query(IntelligenceBriefing).first()
    assert stored is not None
    assert stored.content == "Briefing content"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_intelligence_briefing_router.py -v
```

Expected: 4 failures (router not yet registered / model missing from test DB)

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all pre-existing tests pass, 4 new tests fail.

- [ ] **Step 4: Run tests again — should pass now**

With model, migration, router, and main.py already done in Tasks 1–4:

```bash
cd backend && python -m pytest tests/test_intelligence_briefing_router.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
rtk git add backend/tests/test_intelligence_briefing_router.py
rtk git commit -m "test: add intelligence briefing router tests"
```

---

### Task 6: Frontend Type + Hook

**Files:**
- Modify: `frontend/src/types/intelligence.ts`
- Create: `frontend/src/hooks/useIntelligenceBriefing.ts`

- [ ] **Step 1: Add type to `intelligence.ts`**

Append to end of `frontend/src/types/intelligence.ts`:

```typescript
export interface IntelligenceBriefing {
  id: string;
  content: string;
  signal_count: number;
  assessment_count: number;
  generated_at: string;
}
```

- [ ] **Step 2: Create the hook**

```typescript
// frontend/src/hooks/useIntelligenceBriefing.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, ApiError } from '../api/client';
import type { IntelligenceBriefing } from '../types/intelligence';

export function useLatestIntelligenceBriefing() {
  return useQuery<IntelligenceBriefing | null>({
    queryKey: ['intelligence', 'briefing', 'latest'],
    queryFn: async () => {
      try {
        return await apiGet<IntelligenceBriefing>('/intelligence/briefing/latest');
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
}

export function useGenerateIntelligenceBriefing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<IntelligenceBriefing>('/intelligence/briefing/generate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'briefing', 'latest'] });
    },
  });
}
```

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/types/intelligence.ts frontend/src/hooks/useIntelligenceBriefing.ts
rtk git commit -m "feat: add IntelligenceBriefing type and hook"
```

---

### Task 7: Frontend Component

**Files:**
- Create: `frontend/src/components/overview/IntelligenceBriefingPanel.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/overview/IntelligenceBriefingPanel.tsx
import { RefreshCw } from 'lucide-react';
import { useLatestIntelligenceBriefing, useGenerateIntelligenceBriefing } from '../../hooks/useIntelligenceBriefing';
import MarkdownViewer from '../MarkdownViewer';
import { ApiError } from '../../api/client';

function formatTimeAgo(isoString: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (seconds < 60) return 'gerade eben';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `vor ${minutes} Min.`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `vor ${hours} Std.`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'gestern';
  return `vor ${days} Tagen`;
}

export default function IntelligenceBriefingPanel() {
  const { data: briefing, isLoading } = useLatestIntelligenceBriefing();
  const generate = useGenerateIntelligenceBriefing();

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider inline">
            Intelligence Briefing
          </p>
          {briefing && (
            <span className="text-[10px] font-normal normal-case tracking-normal text-slate-400 ml-2">
              {formatTimeAgo(briefing.generated_at)} ·{' '}
              {new Date(briefing.generated_at).toLocaleString('de-DE', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
              {' · '}
              {briefing.signal_count} Signale · {briefing.assessment_count} Assessments
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={11} className={generate.isPending ? 'animate-spin' : ''} />
            {generate.isPending ? 'Generiere...' : 'Neu generieren'}
          </button>
          {generate.isError && (
            <span className="text-[11px] text-red-500">
              {generate.error instanceof ApiError ? generate.error.message : 'Generierung fehlgeschlagen'}
            </span>
          )}
        </div>
      </div>

      {isLoading ? (
        <p className="text-[12px] text-slate-400">Lade Briefing...</p>
      ) : briefing ? (
        <div className="text-[12px] text-slate-700 leading-relaxed">
          <MarkdownViewer content={briefing.content} />
        </div>
      ) : (
        <p className="text-[12px] text-slate-400">
          Noch kein Intelligence Briefing vorhanden. Klicke auf "Neu generieren".
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/src/components/overview/IntelligenceBriefingPanel.tsx
rtk git commit -m "feat: add IntelligenceBriefingPanel component"
```

---

### Task 8: Wire into OverviewPage

**Files:**
- Modify: `frontend/src/pages/OverviewPage.tsx`

- [ ] **Step 1: Add import and mount panel**

In `frontend/src/pages/OverviewPage.tsx`, add the import after the existing imports:
```typescript
import IntelligenceBriefingPanel from '../components/overview/IntelligenceBriefingPanel';
```

Inside the scrollable `<div className="flex-1 overflow-auto px-6 py-5">`, add `<IntelligenceBriefingPanel />` as the very first child, before `<OverviewKPIBar data={data} />`:

```tsx
<div className="flex-1 overflow-auto px-6 py-5">
  <IntelligenceBriefingPanel />
  <OverviewKPIBar data={data} />
  ...
```

- [ ] **Step 2: Verify in browser**

Open `http://localhost:5173` → Overview page. Confirm:
- Panel appears at the top with "Noch kein Intelligence Briefing vorhanden"
- Clicking "Neu generieren" triggers spinner, then shows Markdown content
- Re-opening the page shows the persisted briefing with timestamp

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/pages/OverviewPage.tsx
rtk git commit -m "feat: mount IntelligenceBriefingPanel on Overview page"
```
