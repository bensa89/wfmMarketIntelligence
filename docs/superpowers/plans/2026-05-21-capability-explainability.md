# Capability Strength Explainability & Panel Consolidation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Relative Capability Strength panel on the Competitor Workspace understandable — with tooltips, a sub-score breakdown drawer, assessment traceability, and consolidation of the CapabilityActivity card.

**Architecture:** New backend endpoint exposes `SignalAssessment` records per capability+period. An adaptive `CapabilityExplainDrawer` (panel-mode and capability-mode) slides in from the right, reusing the existing `ScorecardSignalDrawer`/`SignalDetailDrawer` for signal drill-down. The `CapabilityRadar` (CapabilityActivity card) is removed and its data merged into the updated `RelativeCapabilityStrengthPanel` rows.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React 18 + TypeScript + TanStack Query (frontend), Lucide icons, Tailwind CSS.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/schemas/benchmark.py` | Modify | Add `CapabilityAssessmentItem`, `CapabilityAssessmentsResponse` schemas |
| `backend/app/benchmark/queries.py` | Modify | Add `get_capability_assessments` method to `BenchmarkQueryService` |
| `backend/app/routers/benchmark.py` | Modify | Add `GET /competitors/{slug}/capabilities/{cap_key}/assessments` endpoint |
| `backend/tests/test_benchmark_queries.py` | Create | Tests for the new query method + endpoint |
| `frontend/src/types/benchmark.ts` | Modify | Add `CapabilityAssessmentItem`, `CapabilityAssessmentsResponse` types |
| `frontend/src/api/benchmark.ts` | Modify | Add `fetchCapabilityAssessments` function |
| `frontend/src/hooks/useBenchmark.ts` | Modify | Add `useCapabilityAssessments` hook |
| `frontend/src/components/workspace/InfoTooltip.tsx` | Create | Reusable hover tooltip with info icon |
| `frontend/src/components/workspace/CapabilityExplainDrawer.tsx` | Create | Adaptive drawer: panel-mode (concept explanation) + capability-mode (sub-scores + assessments) |
| `frontend/src/components/workspace/RelativeCapabilityStrengthPanel.tsx` | Modify | Column headers + tooltips + momentum color + signal count + info button + row click |
| `frontend/src/components/workspace/CapabilityRadar.tsx` | Delete | Replaced by consolidated panel |
| `frontend/src/pages/CompetitorWorkspacePage.tsx` | Modify | Remove CapabilityRadar, add drawer state, pass new props |

---

## Task 1: Backend Schemas

**Files:**
- Modify: `backend/app/schemas/benchmark.py`

- [ ] **Step 1: Add two new Pydantic models at the bottom of the schemas file**

Open `backend/app/schemas/benchmark.py` and append after the existing `CapabilityLeaderboardResponse` class:

```python
class CapabilityAssessmentItem(BaseModel):
    assessment_id: str
    signal_id: str
    title: str
    movement_score: int
    signal_class: str
    created_at: datetime


class CapabilityAssessmentsResponse(BaseModel):
    capability_key: str
    label: str
    period_type: str
    assessments: list[CapabilityAssessmentItem]
    total_count: int
```

- [ ] **Step 2: Verify the file parses cleanly**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -c "from app.schemas.benchmark import CapabilityAssessmentsResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/benchmark.py
git commit -m "feat(benchmark): add CapabilityAssessmentsResponse schema"
```

---

## Task 2: Backend Query Method

**Files:**
- Modify: `backend/app/benchmark/queries.py`

- [ ] **Step 1: Add the new imports at the top of `queries.py`**

The file already imports `Company` and `CompetitorCapabilityBenchmark`. Add two imports:

```python
from datetime import datetime
from app.models.signal_assessment import SignalAssessment
from app.schemas.benchmark import (
    # existing imports stay ...
    CapabilityAssessmentItem,
    CapabilityAssessmentsResponse,
)
```

The full import block at the top of `queries.py` should become:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.capability_benchmark import CompetitorCapabilityBenchmark
from app.models.signal_assessment import SignalAssessment
from app.assessor.capabilities import CAPABILITIES, CAPABILITY_KEYS
from app.benchmark.period import get_period_bounds
from app.schemas.benchmark import (
    BenchmarkMatrixCell,
    BenchmarkOverviewResponse,
    BenchmarkSubScores,
    CapabilityAssessmentItem,
    CapabilityAssessmentsResponse,
    CapabilityLeaderboardResponse,
    CompetitorBenchmarkDetail,
    CompetitorBenchmarkResponse,
    CompetitorBrief,
    LeaderboardEntry,
)
```

- [ ] **Step 2: Add `get_capability_assessments` method to `BenchmarkQueryService`**

Append this method at the end of the `BenchmarkQueryService` class (after `get_capability_leaderboard`):

```python
def get_capability_assessments(
    self, slug: str, cap_key: str, period_type: str = "30d"
) -> CapabilityAssessmentsResponse:
    company = self.db.query(Company).filter_by(slug=slug).first()
    if company is None:
        raise ValueError(f"Company not found: {slug!r}")

    period_start, period_end = get_period_bounds(period_type)
    dt_start = datetime(period_start.year, period_start.month, period_start.day, 0, 0, 0)
    dt_end = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59)

    base_filter = [
        SignalAssessment.company_id == company.id,
        SignalAssessment.capability_primary == cap_key,
        SignalAssessment.created_at >= dt_start,
        SignalAssessment.created_at <= dt_end,
    ]

    total_count = (
        self.db.query(SignalAssessment).filter(*base_filter).count()
    )
    assessments = (
        self.db.query(SignalAssessment)
        .filter(*base_filter)
        .order_by(SignalAssessment.movement_score.desc())
        .limit(20)
        .all()
    )

    cap_meta = CAPABILITIES.get(cap_key, {})
    label = cap_meta.get("label", cap_key) if cap_meta else cap_key

    items = [
        CapabilityAssessmentItem(
            assessment_id=a.id,
            signal_id=a.signal_id,
            title=a.signal.title if a.signal else "—",
            movement_score=a.movement_score or 0,
            signal_class=a.signal_class.value if a.signal_class else "unknown",
            created_at=a.created_at,
        )
        for a in assessments
    ]

    return CapabilityAssessmentsResponse(
        capability_key=cap_key,
        label=label,
        period_type=period_type,
        assessments=items,
        total_count=total_count,
    )
```

- [ ] **Step 3: Verify the module imports cleanly**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -c "from app.benchmark.queries import BenchmarkQueryService; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/benchmark/queries.py
git commit -m "feat(benchmark): add get_capability_assessments query method"
```

---

## Task 3: Backend Router Endpoint

**Files:**
- Modify: `backend/app/routers/benchmark.py`

- [ ] **Step 1: Add the schema import to the router**

In `backend/app/routers/benchmark.py`, extend the existing import from `app.schemas.benchmark`:

```python
from app.schemas.benchmark import (
    BenchmarkOverviewResponse,
    CompetitorBenchmarkResponse,
    CapabilityLeaderboardResponse,
    CapabilityAssessmentsResponse,
)
```

- [ ] **Step 2: Add the new endpoint**

Append after the `get_competitor_strengths` endpoint:

```python
@router.get("/competitors/{slug}/capabilities/{cap_key}/assessments", response_model=CapabilityAssessmentsResponse)
def get_capability_assessments(
    slug: str,
    cap_key: str,
    period_type: str = "30d",
    db: Session = Depends(get_db),
):
    try:
        return BenchmarkQueryService(db).get_capability_assessments(slug, cap_key, period_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 3: Verify the app starts**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -c "from app.routers.benchmark import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/benchmark.py
git commit -m "feat(benchmark): add GET /competitors/{slug}/capabilities/{cap_key}/assessments endpoint"
```

---

## Task 4: Backend Tests

**Files:**
- Create: `backend/tests/test_benchmark_queries.py`

- [ ] **Step 1: Write the test file**

Create `backend/tests/test_benchmark_queries.py`:

```python
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models  # noqa: F401
from app.database import Base
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.signal_assessment import SignalAssessment, SignalClass
from app.benchmark.queries import BenchmarkQueryService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seeded_db(db):
    company = Company(id="comp-1", name="Acme WFM", slug="acme-wfm", type=CompanyType.competitor)
    db.add(company)
    source = Source(id="src-1", company_id="comp-1", url="https://acme.com", source_type=SourceType.blog)
    db.add(source)
    doc = Document(id="doc-1", source_id="src-1", url="https://acme.com/post")
    db.add(doc)
    sig = Signal(id="sig-1", document_id="doc-1", company_id="comp-1", title="Acme launches AI scheduling", signal_type=SignalType.product_update)
    db.add(sig)
    assessment = SignalAssessment(
        id="asmt-1",
        signal_id="sig-1",
        company_id="comp-1",
        capability_primary="ai_scheduling",
        signal_class=SignalClass.product_capability_move,
        movement_score=75,
        created_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.commit()
    return db


def test_get_capability_assessments_returns_matching_assessments(seeded_db):
    svc = BenchmarkQueryService(seeded_db)
    result = svc.get_capability_assessments("acme-wfm", "ai_scheduling", "30d")

    assert result.capability_key == "ai_scheduling"
    assert result.total_count == 1
    assert len(result.assessments) == 1
    item = result.assessments[0]
    assert item.assessment_id == "asmt-1"
    assert item.signal_id == "sig-1"
    assert item.title == "Acme launches AI scheduling"
    assert item.movement_score == 75
    assert item.signal_class == "product_capability_move"


def test_get_capability_assessments_wrong_capability_returns_empty(seeded_db):
    svc = BenchmarkQueryService(seeded_db)
    result = svc.get_capability_assessments("acme-wfm", "workforce_management", "30d")

    assert result.total_count == 0
    assert result.assessments == []


def test_get_capability_assessments_unknown_slug_raises(seeded_db):
    svc = BenchmarkQueryService(seeded_db)
    with pytest.raises(ValueError, match="Company not found"):
        svc.get_capability_assessments("does-not-exist", "ai_scheduling", "30d")


def test_get_capability_assessments_ordered_by_movement_score_desc(db):
    company = Company(id="comp-2", name="Beta", slug="beta", type=CompanyType.competitor)
    db.add(company)
    source = Source(id="src-2", company_id="comp-2", url="https://beta.com", source_type=SourceType.blog)
    db.add(source)
    doc = Document(id="doc-2", source_id="src-2", url="https://beta.com/p")
    db.add(doc)

    for i, score in enumerate([30, 90, 60]):
        sig = Signal(id=f"sig-{i}", document_id="doc-2", company_id="comp-2", title=f"Signal {i}", signal_type=SignalType.product_update)
        db.add(sig)
        asmt = SignalAssessment(
            id=f"asmt-{i}",
            signal_id=f"sig-{i}",
            company_id="comp-2",
            capability_primary="ai_scheduling",
            movement_score=score,
            created_at=datetime.now(timezone.utc),
        )
        db.add(asmt)
    db.commit()

    svc = BenchmarkQueryService(db)
    result = svc.get_capability_assessments("beta", "ai_scheduling", "30d")

    scores = [a.movement_score for a in result.assessments]
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run the tests inside Docker**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_benchmark_queries.py -v
```

Expected: 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_benchmark_queries.py
git commit -m "test(benchmark): add tests for get_capability_assessments query"
```

---

## Task 5: Frontend Types

**Files:**
- Modify: `frontend/src/types/benchmark.ts`

- [ ] **Step 1: Add two new interfaces at the bottom of `types/benchmark.ts`**

```typescript
export interface CapabilityAssessmentItem {
  assessment_id: string;
  signal_id: string;
  title: string;
  movement_score: number;
  signal_class: string;
  created_at: string;
}

export interface CapabilityAssessmentsResponse {
  capability_key: string;
  label: string;
  period_type: string;
  assessments: CapabilityAssessmentItem[];
  total_count: number;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/benchmark.ts
git commit -m "feat(frontend): add CapabilityAssessmentsResponse types"
```

---

## Task 6: Frontend API Function + Hook

**Files:**
- Modify: `frontend/src/api/benchmark.ts`
- Modify: `frontend/src/hooks/useBenchmark.ts`

- [ ] **Step 1: Add `fetchCapabilityAssessments` to `api/benchmark.ts`**

Add the import at the top of the existing import block in `api/benchmark.ts`:

```typescript
import type {
  BenchmarkOverviewResponse,
  CompetitorBenchmarkResponse,
  CapabilityLeaderboardResponse,
  CapabilityAssessmentsResponse,
  BenchmarkPeriodType,
} from '../types/benchmark';
```

Then append the new function at the bottom of the file:

```typescript
export function fetchCapabilityAssessments(
  slug: string,
  capKey: string,
  periodType: BenchmarkPeriodType = '30d',
) {
  return apiGet<CapabilityAssessmentsResponse>(
    `/benchmark/competitors/${slug}/capabilities/${capKey}/assessments`,
    { period_type: periodType },
  );
}
```

- [ ] **Step 2: Add `useCapabilityAssessments` to `hooks/useBenchmark.ts`**

Add the import at the top of the existing import block in `hooks/useBenchmark.ts`:

```typescript
import {
  fetchBenchmarkOverview,
  fetchCompetitorBenchmark,
  fetchCapabilityLeaderboard,
  fetchCapabilityAssessments,
  recomputeAllBenchmarks,
  recomputeCompanyBenchmark,
} from '../api/benchmark';
import type { BenchmarkPeriodType, CapabilityAssessmentsResponse } from '../types/benchmark';
```

Then append the new hook at the bottom of the file:

```typescript
export function useCapabilityAssessments(
  slug: string,
  capKey: string | null,
  periodType: BenchmarkPeriodType,
  enabled: boolean,
) {
  return useQuery<CapabilityAssessmentsResponse>({
    queryKey: ['benchmark', 'capability-assessments', slug, capKey, periodType],
    queryFn: () => fetchCapabilityAssessments(slug, capKey!, periodType),
    enabled: enabled && Boolean(slug) && Boolean(capKey),
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/benchmark.ts frontend/src/hooks/useBenchmark.ts
git commit -m "feat(frontend): add fetchCapabilityAssessments API + useCapabilityAssessments hook"
```

---

## Task 7: InfoTooltip Component

**Files:**
- Create: `frontend/src/components/workspace/InfoTooltip.tsx`

- [ ] **Step 1: Create the component**

```typescript
import { useState } from 'react';
import { Info } from 'lucide-react';

interface Props {
  text: string;
}

export function InfoTooltip({ text }: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <span className="relative inline-flex items-center">
      <Info
        className="w-3 h-3 text-slate-400 cursor-help flex-shrink-0"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
      />
      {visible && (
        <span className="absolute z-50 bottom-full mb-1.5 left-1/2 -translate-x-1/2 w-60 bg-slate-900 text-white text-[11px] rounded-lg px-3 py-2 shadow-xl pointer-events-none leading-snug whitespace-normal">
          {text}
        </span>
      )}
    </span>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/workspace/InfoTooltip.tsx
git commit -m "feat(frontend): add reusable InfoTooltip component"
```

---

## Task 8: CapabilityExplainDrawer

**Files:**
- Create: `frontend/src/components/workspace/CapabilityExplainDrawer.tsx`

- [ ] **Step 1: Create the full component**

```typescript
import { X } from 'lucide-react';
import type { CompetitorBenchmarkDetail, BenchmarkPeriodType } from '../../types/benchmark';
import { TierBadge } from '../benchmark/TierBadge';
import { InfoTooltip } from './InfoTooltip';
import { useCapabilityAssessments } from '../../hooks/useBenchmark';

// ─── Momentum helpers ────────────────────────────────────────────────────────

function getMomentumColor(score: number): string {
  if (score >= 80) return '#f97316';
  if (score >= 60) return '#8b5cf6';
  if (score >= 30) return '#3b82f6';
  return '#64748b';
}

function getMomentumLabel(score: number): string {
  if (score >= 80) return 'Sehr hoch (≥80)';
  if (score >= 60) return 'Hoch (≥60)';
  if (score >= 30) return 'Mittel (≥30)';
  return 'Gering (<30)';
}

// ─── Sub-score metadata ───────────────────────────────────────────────────────

const SUB_SCORE_META = [
  {
    key: 'capability_depth' as const,
    label: 'Capability Depth',
    weight: '35%',
    tooltip:
      'Qualität und Substanz der Signale: Wie stark deuten Produkt-Moves, Positionierung und Evidenzstärke auf echte Capability-Tiefe hin?',
  },
  {
    key: 'execution_momentum' as const,
    label: 'Execution Momentum',
    weight: '25%',
    tooltip:
      'Signal-Dichte + durchschnittlicher Bewegungsscore + Anteil starker Moves. Wie aktiv und kraftvoll agiert der Wettbewerber?',
  },
  {
    key: 'market_proof' as const,
    label: 'Market Proof',
    weight: '20%',
    tooltip:
      'Externe Belege: Ecosystem-Moves, Kunden-Referenzen, hoher Visibility-Impact. Wie sichtbar ist die Capability am Markt?',
  },
  {
    key: 'strategic_focus' as const,
    label: 'Strategic Focus',
    weight: '10%',
    tooltip:
      'Anteil aller Assessments, der auf diese Capability entfällt + Positionierungs-Moves. Wie stark priorisiert der Wettbewerber diese Fähigkeit?',
  },
  {
    key: 'evidence_coverage' as const,
    label: 'Evidence Coverage',
    weight: '10%',
    tooltip:
      'Kombination aus Quellen-Diversität, Confidence der Assessments und Aktualität (Freshness). Wie verlässlich ist die Datenbasis?',
  },
];

// ─── Sub-score bar ────────────────────────────────────────────────────────────

function SubScoreBar({ label, value, weight, tooltip }: { label: string; value: number; weight: string; tooltip: string }) {
  const color = value >= 4 ? 'bg-emerald-500' : value >= 2 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-3">
      <div className="w-40 shrink-0 flex items-center gap-1.5">
        <span className="text-xs text-slate-700 truncate">{label}</span>
        <InfoTooltip text={tooltip} />
        <span className="text-[10px] text-slate-400 ml-auto">{weight}</span>
      </div>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${(value / 5) * 100}%` }}
        />
      </div>
      <span className="w-8 text-right text-xs font-mono text-slate-600 shrink-0">{value}/5</span>
    </div>
  );
}

// ─── Momentum legend ──────────────────────────────────────────────────────────

function MomentumLegend() {
  const levels = [
    { score: 80, label: '≥80 — Sehr hohe Aktivitätsintensität', color: '#f97316' },
    { score: 60, label: '≥60 — Hohe Intensität', color: '#8b5cf6' },
    { score: 30, label: '≥30 — Mittlere Intensität', color: '#3b82f6' },
    { score: 0,  label: '<30 — Geringe Intensität', color: '#64748b' },
  ];
  return (
    <div className="space-y-1.5">
      {levels.map(({ label, color }) => (
        <div key={label} className="flex items-center gap-2 text-xs text-slate-600">
          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
          {label}
        </div>
      ))}
    </div>
  );
}

// ─── Panel mode content ───────────────────────────────────────────────────────

function PanelModeContent() {
  return (
    <div className="space-y-6 text-sm">
      <div>
        <h3 className="font-semibold text-slate-800 mb-1">Was ist der Relative Capability Score?</h3>
        <p className="text-slate-600 text-xs leading-relaxed">
          Der Score (0–100) misst, wie stark ein Wettbewerber in einer bestimmten Capability aktiv und belegt ist — relativ zu seinen eigenen Signalen im gewählten Zeitraum. Er ist kein absoluter Marktvergleich, sondern ein gewichtetes Qualitäts- und Aktivitätsmaß.
        </p>
      </div>

      <div>
        <h3 className="font-semibold text-slate-800 mb-2">Score-Formel</h3>
        <div className="space-y-1.5">
          {SUB_SCORE_META.map(({ label, weight, tooltip }) => (
            <div key={label} className="flex items-center gap-2 text-xs text-slate-600">
              <InfoTooltip text={tooltip} />
              <span className="flex-1">{label}</span>
              <span className="font-medium text-slate-800">{weight}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="font-semibold text-slate-800 mb-2">Tier-Definitionen</h3>
        <div className="space-y-1.5 text-xs">
          {[
            { label: 'Leader', range: '≥75', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
            { label: 'Strong', range: '≥55', color: 'text-blue-700 bg-blue-50 border-blue-200' },
            { label: 'Emerging', range: '≥30', color: 'text-amber-700 bg-amber-50 border-amber-200' },
            { label: 'Weakly Evidenced', range: '<30 oder zu wenig Belege', color: 'text-slate-500 bg-slate-50 border-slate-200' },
          ].map(({ label, range, color }) => (
            <div key={label} className={`flex items-center justify-between px-3 py-1.5 rounded border ${color}`}>
              <span className="font-medium">{label}</span>
              <span>{range}</span>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-slate-400 mt-1.5">Bei niedriger Confidence wird das Tier um eine Stufe reduziert.</p>
      </div>

      <div>
        <h3 className="font-semibold text-slate-800 mb-2">Momentum-Farblegende</h3>
        <p className="text-xs text-slate-500 mb-2">Farbe des Stärkebalkens = durchschnittlicher Movement Score aller Assessments dieser Capability.</p>
        <MomentumLegend />
      </div>
    </div>
  );
}

// ─── Capability mode content ──────────────────────────────────────────────────

interface CapabilityModeContentProps {
  detail: CompetitorBenchmarkDetail;
  slug: string;
  periodType: BenchmarkPeriodType;
  avgMovementScore?: number;
  periodLabel: string;
  onSelectSignal: (signalId: string) => void;
}

function CapabilityModeContent({
  detail,
  slug,
  periodType,
  avgMovementScore,
  periodLabel,
  onSelectSignal,
}: CapabilityModeContentProps) {
  const { data, isLoading } = useCapabilityAssessments(slug, detail.capability_key, periodType, true);

  return (
    <div className="space-y-6">
      {/* Sub-score breakdown */}
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Sub-Score Breakdown</h3>
        <div className="space-y-3">
          {SUB_SCORE_META.map(({ key, label, weight, tooltip }) => (
            <SubScoreBar
              key={key}
              label={label}
              value={detail.sub_scores[key]}
              weight={weight}
              tooltip={tooltip}
            />
          ))}
        </div>
        <p className="text-[11px] text-slate-400 mt-3">
          Gesamtscore: <strong className="text-slate-700">{detail.relative_strength_score}/100</strong>
          {' '}(Σ gewichteter Sub-Scores × 20)
        </p>
      </div>

      {/* Activity */}
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Activity</h3>
        <div className="flex gap-4 text-xs text-slate-600">
          <div>
            <span className="text-slate-400">Assessments</span>
            <p className="font-semibold text-slate-800 text-base">{detail.source_signal_count}</p>
            <p className="text-slate-400">{periodLabel}</p>
          </div>
          {avgMovementScore !== undefined && (
            <div>
              <span className="text-slate-400">Avg. Movement Score</span>
              <p className="font-semibold text-base" style={{ color: getMomentumColor(avgMovementScore) }}>
                {avgMovementScore}
              </p>
              <p className="text-slate-400">{getMomentumLabel(avgMovementScore)}</p>
            </div>
          )}
        </div>
        {avgMovementScore !== undefined && (
          <div className="mt-3">
            <MomentumLegend />
          </div>
        )}
      </div>

      {/* Contributing assessments */}
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Contributing Assessments</h3>
        {isLoading && (
          <div className="space-y-2 animate-pulse">
            {[1, 2, 3].map((i) => <div key={i} className="h-8 bg-slate-100 rounded" />)}
          </div>
        )}
        {!isLoading && data && data.assessments.length === 0 && (
          <p className="text-xs text-slate-400 italic">Keine Assessments für diesen Zeitraum.</p>
        )}
        {!isLoading && data && data.assessments.length > 0 && (
          <>
            <ul className="space-y-1.5">
              {data.assessments.map((a) => (
                <li
                  key={a.assessment_id}
                  onClick={() => onSelectSignal(a.signal_id)}
                  className="flex items-center justify-between gap-3 text-xs p-2 rounded-lg hover:bg-slate-50 cursor-pointer group"
                >
                  <span className="text-slate-700 truncate group-hover:text-slate-900">{a.title}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-slate-400">{a.signal_class.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-indigo-600">{a.movement_score}</span>
                  </div>
                </li>
              ))}
            </ul>
            {data.total_count > 20 && (
              <p className="text-[11px] text-slate-400 italic mt-2">
                … und {data.total_count - 20} weitere Assessments
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main drawer ──────────────────────────────────────────────────────────────

interface CapabilityExplainDrawerProps {
  open: boolean;
  onClose: () => void;
  mode: 'panel' | 'capability';
  slug?: string;
  detail?: CompetitorBenchmarkDetail;
  periodType?: BenchmarkPeriodType;
  avgMovementScore?: number;
  onSelectSignal?: (signalId: string) => void;
}

const PERIOD_LABELS: Record<string, string> = {
  '30d': 'Letzten 30 Tage',
  '90d': 'Letzten 90 Tage',
  '180d': 'Letzten 180 Tage',
};

export function CapabilityExplainDrawer({
  open,
  onClose,
  mode,
  slug,
  detail,
  periodType = '30d',
  avgMovementScore,
  onSelectSignal,
}: CapabilityExplainDrawerProps) {
  if (!open) return null;

  const title = mode === 'panel'
    ? 'Was bedeutet das?'
    : detail?.label ?? 'Capability';

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-gray-800">{title}</h2>
            {mode === 'capability' && detail && (
              <TierBadge tier={detail.tier as any} size="sm" />
            )}
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {mode === 'panel' && <PanelModeContent />}
          {mode === 'capability' && detail && slug && (
            <CapabilityModeContent
              detail={detail}
              slug={slug}
              periodType={periodType}
              avgMovementScore={avgMovementScore}
              periodLabel={PERIOD_LABELS[periodType] ?? periodType}
              onSelectSignal={onSelectSignal ?? (() => {})}
            />
          )}
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles (run in frontend container or locally)**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors related to `CapabilityExplainDrawer`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workspace/CapabilityExplainDrawer.tsx
git commit -m "feat(frontend): add CapabilityExplainDrawer (panel + capability mode)"
```

---

## Task 9: Update RelativeCapabilityStrengthPanel

**Files:**
- Modify: `frontend/src/components/workspace/RelativeCapabilityStrengthPanel.tsx`

- [ ] **Step 1: Replace the entire file with the updated version**

```typescript
import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { useCompetitorBenchmark } from '../../hooks/useBenchmark';
import type { BenchmarkPeriodType, CompetitorBenchmarkDetail } from '../../types/benchmark';
import type { CapabilityCount } from '../../types/intelligence';
import { TierBadge } from '../benchmark/TierBadge';
import { ConfidenceIndicator } from '../benchmark/ConfidenceIndicator';
import { StrengthDeltaIndicator } from '../benchmark/StrengthDeltaIndicator';
import { InfoTooltip } from './InfoTooltip';

interface RelativeCapabilityStrengthPanelProps {
  slug: string;
  capabilityDistribution?: CapabilityCount[];
  onCapabilityClick?: (detail: CompetitorBenchmarkDetail) => void;
  onInfoClick?: () => void;
}

const PERIOD_OPTIONS: { value: BenchmarkPeriodType; label: string }[] = [
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
  { value: '180d', label: '180d' },
];

const COLUMN_TOOLTIPS = {
  score: 'Score 0–100. Gewichteter Durchschnitt aus 5 Sub-Scores: Capability Depth (35%), Execution Momentum (25%), Market Proof (20%), Strategic Focus (10%), Evidence Coverage (10%).',
  tier: 'Leader (≥75), Strong (≥55), Emerging (≥30), Weakly Evidenced (<30 oder zu wenig Belege). Wird bei niedriger Confidence um eine Stufe reduziert.',
  rank: 'Position im Vergleich zu allen Wettbewerbern für diese Capability im gewählten Zeitraum.',
  delta: 'Veränderung des Scores zur Vorperiode (positiv = gestärkt, negativ = geschwächt).',
  conf: 'Confidence-Score 0–1: basiert auf Anzahl der Assessments, Evidence Coverage und durchschnittlichem Konfidenzwert.',
  signals: 'Anzahl der Assessments, die in diesem Zeitraum dieser Capability zugeordnet wurden.',
};

const MOMENTUM_BAR_TOOLTIP =
  'Balkenfarbe = durchschnittlicher Movement Score aller Assessments:\n🟠 ≥80 sehr hoch · 🟣 ≥60 hoch · 🔵 ≥30 mittel · ⚫ <30 gering';

function getMomentumColor(score?: number): string {
  if (score === undefined) return '#3b82f6';
  if (score >= 80) return '#f97316';
  if (score >= 60) return '#8b5cf6';
  if (score >= 30) return '#3b82f6';
  return '#64748b';
}

function StrengthBar({ score, momentumColor }: { score: number; momentumColor: string }) {
  return (
    <div className="relative flex-1 group/bar">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, backgroundColor: momentumColor }}
        />
      </div>
      {/* Momentum bar tooltip */}
      <span className="absolute z-50 bottom-full mb-1.5 left-1/2 -translate-x-1/2 w-64 bg-slate-900 text-white text-[10px] rounded-lg px-2.5 py-1.5 shadow-xl pointer-events-none leading-snug whitespace-pre-line hidden group-hover/bar:block">
        {MOMENTUM_BAR_TOOLTIP}
      </span>
    </div>
  );
}

function ColumnHeaders() {
  return (
    <div className="flex items-center gap-3 pb-1.5 border-b border-slate-100 mb-1">
      <div className="w-32 shrink-0" />
      <div className="flex-1 flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Score <InfoTooltip text={COLUMN_TOOLTIPS.score} />
      </div>
      <div className="w-8 shrink-0" />
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Tier <InfoTooltip text={COLUMN_TOOLTIPS.tier} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        # <InfoTooltip text={COLUMN_TOOLTIPS.rank} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Δ <InfoTooltip text={COLUMN_TOOLTIPS.delta} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Conf <InfoTooltip text={COLUMN_TOOLTIPS.conf} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Signals <InfoTooltip text={COLUMN_TOOLTIPS.signals} />
      </div>
    </div>
  );
}

function CapabilityRow({
  detail,
  momentumColor,
  onClick,
}: {
  detail: CompetitorBenchmarkDetail;
  momentumColor: string;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0 cursor-pointer hover:bg-slate-50 rounded -mx-1 px-1 transition-colors"
    >
      <div className="w-32 shrink-0">
        <span className="text-xs text-slate-700 font-medium truncate block">{detail.label}</span>
      </div>
      <StrengthBar score={detail.relative_strength_score} momentumColor={momentumColor} />
      <span className="w-8 text-right text-xs font-mono text-slate-600 shrink-0">
        {detail.relative_strength_score}
      </span>
      <TierBadge tier={detail.tier} size="sm" />
      {detail.peer_rank ? (
        <span className="text-xs text-slate-400 shrink-0 w-5 text-right">#{detail.peer_rank}</span>
      ) : (
        <span className="w-5" />
      )}
      <StrengthDeltaIndicator delta={detail.strength_delta} />
      <ConfidenceIndicator confidence={detail.confidence} />
      <span className="text-[11px] text-slate-400 shrink-0 w-12 text-right">
        {detail.source_signal_count > 0 ? `${detail.source_signal_count}` : '—'}
      </span>
    </div>
  );
}

export function RelativeCapabilityStrengthPanel({
  slug,
  capabilityDistribution,
  onCapabilityClick,
  onInfoClick,
}: RelativeCapabilityStrengthPanelProps) {
  const [period, setPeriod] = useState<BenchmarkPeriodType>('30d');
  const { data, isLoading } = useCompetitorBenchmark(slug, period);

  const distLookup = new Map(
    (capabilityDistribution ?? []).map((d) => [d.capability_key, d.avg_movement_score])
  );

  const evidenced = data?.capabilities.filter(c => c.tier !== 'weakly_evidenced') ?? [];
  const weakly = data?.capabilities.filter(c => c.tier === 'weakly_evidenced') ?? [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-1.5">
          <h3 className="text-sm font-semibold text-slate-900">Relative Capability Strength</h3>
          <button
            onClick={onInfoClick}
            className="p-0.5 rounded hover:bg-slate-100 transition-colors"
            title="Was bedeutet das?"
          >
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
          </button>
        </div>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                period === opt.value
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-sm text-slate-400">Loading benchmark data…</p>}

      {data && (
        <>
          <ColumnHeaders />
          {evidenced.length > 0 && (
            <div className="mb-4">
              {evidenced
                .sort((a, b) => b.relative_strength_score - a.relative_strength_score)
                .map(d => (
                  <CapabilityRow
                    key={d.capability_key}
                    detail={d}
                    momentumColor={getMomentumColor(distLookup.get(d.capability_key))}
                    onClick={() => onCapabilityClick?.(d)}
                  />
                ))}
            </div>
          )}
          {weakly.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-slate-400 cursor-pointer select-none">
                {weakly.length} capability{weakly.length > 1 ? 'ies' : 'y'} with insufficient evidence
              </summary>
              <div className="mt-2 opacity-60">
                {weakly.map(d => (
                  <CapabilityRow
                    key={d.capability_key}
                    detail={d}
                    momentumColor={getMomentumColor(distLookup.get(d.capability_key))}
                    onClick={() => onCapabilityClick?.(d)}
                  />
                ))}
              </div>
            </details>
          )}
          {evidenced.length === 0 && weakly.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-6">
              No benchmark data yet. Run a recompute to generate scores.
            </p>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Check TypeScript**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workspace/RelativeCapabilityStrengthPanel.tsx
git commit -m "feat(frontend): update RelativeCapabilityStrengthPanel with tooltips, momentum color, signal count, explainability"
```

---

## Task 10: Page Wiring + Remove CapabilityRadar

**Files:**
- Modify: `frontend/src/pages/CompetitorWorkspacePage.tsx`
- Delete: `frontend/src/components/workspace/CapabilityRadar.tsx`

- [ ] **Step 1: Delete the CapabilityRadar file**

```bash
rm /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend/src/components/workspace/CapabilityRadar.tsx
```

- [ ] **Step 2: Update the imports in `CompetitorWorkspacePage.tsx`**

Remove:
```typescript
import CapabilityRadar from '../components/workspace/CapabilityRadar';
```

Add:
```typescript
import { CapabilityExplainDrawer } from '../components/scorecard/../workspace/CapabilityExplainDrawer';
import type { CompetitorBenchmarkDetail, BenchmarkPeriodType as BenchmarkPT } from '../types/benchmark';
```

The full import block at the top becomes (replacing the relevant lines):

```typescript
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ExternalLink, RefreshCw, HelpCircle } from 'lucide-react';
import { useCompetitorWorkspace } from '../hooks/useCompetitorWorkspace';
import { useSummarizeCompetitor } from '../hooks/useSummarizeCompetitor';
import { ApiError } from '../api/client';
import StrategicPostureCard from '../components/workspace/StrategicPostureCard';
import CapabilityRadar from '../components/workspace/CapabilityRadar';  // REMOVE THIS LINE
import { RelativeCapabilityStrengthPanel } from '../components/workspace/RelativeCapabilityStrengthPanel';
import RecentMovesTimeline from '../components/workspace/RecentMovesTimeline';
import RisksOpportunitiesCards from '../components/workspace/RisksOpportunitiesCards';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import type { SignalFeedItem } from '../types/intelligence';
import { useScorecard, useScorecardExplain, useRecomputeScorecard } from '../hooks/useScorecard';
import { DimensionScoreGrid } from '../components/scorecard/DimensionScoreGrid';
import { TopMovesTimeline } from '../components/scorecard/TopMovesTimeline';
import { ExplainabilityDrawer } from '../components/scorecard/ExplainabilityDrawer';
import { ScorecardSignalDrawer } from '../components/scorecard/ScorecardSignalDrawer';
import { CapabilityExplainDrawer } from '../components/workspace/CapabilityExplainDrawer';
import type { CompetitorBenchmarkDetail } from '../types/benchmark';
```

- [ ] **Step 3: Add new state in `CompetitorWorkspacePage`**

After the existing state declarations (`selectedSignal`, `selectedScorecardSignalId`, `explainOpen`), add:

```typescript
const [capabilityExplainMode, setCapabilityExplainMode] = useState<'panel' | 'capability' | null>(null);
const [selectedCapabilityDetail, setSelectedCapabilityDetail] = useState<CompetitorBenchmarkDetail | null>(null);
```

- [ ] **Step 4: Remove `<CapabilityRadar>` usage**

Find where `<CapabilityRadar distribution={...} />` is rendered in the JSX and remove it entirely.

- [ ] **Step 5: Update `<RelativeCapabilityStrengthPanel>` props**

Find the existing `<RelativeCapabilityStrengthPanel slug={slug ?? ''} />` and replace with:

```tsx
<RelativeCapabilityStrengthPanel
  slug={slug ?? ''}
  capabilityDistribution={activeSummary?.capability_distribution ?? []}
  onInfoClick={() => setCapabilityExplainMode('panel')}
  onCapabilityClick={(detail) => {
    setSelectedCapabilityDetail(detail);
    setCapabilityExplainMode('capability');
  }}
/>
```

- [ ] **Step 6: Add `<CapabilityExplainDrawer>` to the JSX**

Add the drawer alongside the existing `<ScorecardSignalDrawer>` (after it, at the end of the return):

```tsx
<CapabilityExplainDrawer
  open={capabilityExplainMode !== null}
  onClose={() => { setCapabilityExplainMode(null); setSelectedCapabilityDetail(null); }}
  mode={capabilityExplainMode ?? 'panel'}
  slug={slug ?? ''}
  detail={selectedCapabilityDetail ?? undefined}
  periodType={activePeriod as any}
  avgMovementScore={
    selectedCapabilityDetail
      ? (activeSummary?.capability_distribution ?? []).find(
          d => d.capability_key === selectedCapabilityDetail.capability_key
        )?.avg_movement_score
      : undefined
  }
  onSelectSignal={setSelectedScorecardSignalId}
/>
```

- [ ] **Step 7: Verify TypeScript**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit 2>&1 | head -40
```

Expected: no errors

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/CompetitorWorkspacePage.tsx
git rm frontend/src/components/workspace/CapabilityRadar.tsx
git commit -m "feat(frontend): wire CapabilityExplainDrawer into workspace page, remove CapabilityRadar"
```

---

## Task 11: Run All Backend Tests

- [ ] **Step 1: Run the full backend test suite inside Docker**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: all existing tests pass + 4 new benchmark query tests pass. No regressions.

- [ ] **Step 2: If tests fail, investigate and fix before proceeding**

Common issues:
- Import errors in the new schema → check `CapabilityAssessmentItem` is exported from `schemas/benchmark.py`
- SQLite compatibility → the `datetime` filter works the same as in existing `test_benchmark_aggregation.py`

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix(benchmark): address test failures from capability assessments endpoint"
```
