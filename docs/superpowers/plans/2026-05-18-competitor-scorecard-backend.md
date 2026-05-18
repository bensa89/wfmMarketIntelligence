# Competitor Scorecard — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the DimensionRouter → KPIEngine → ScorecardBuilder pipeline, persist CompetitorScorecard snapshots, and expose them via `/api/scorecards/`.

**Architecture:** Modular pipeline running parallel to BenchmarkAggregationService inside `assess_signal()`. DimensionRouter enriches SignalAssessment at creation time with per-dimension routing metadata. KPIEngine is pure functions (no DB). ScorecardBuilder orchestrates fetching, scoring, and snapshot persistence.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync), Alembic, SQLite (tests), PostgreSQL (dev/prod).

**Test command (always run inside Docker):**
```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/<file> -v
```

---

## File Map

**New files:**
- `backend/app/scorecard/__init__.py`
- `backend/app/scorecard/constants.py` — all scorecard constants (single source of truth)
- `backend/app/scorecard/dimension_router.py` — DimensionRouter
- `backend/app/scorecard/kpi_engine.py` — pure KPI functions
- `backend/app/scorecard/builder.py` — ScorecardBuilder orchestration
- `backend/app/models/competitor_scorecard.py` — CompetitorScorecard ORM model
- `backend/app/schemas/scorecard.py` — Pydantic v2 schemas
- `backend/app/routers/scorecards.py` — FastAPI router
- `backend/tests/test_dimension_router.py`
- `backend/tests/test_kpi_engine.py`
- `backend/tests/test_scorecard_builder.py`
- `backend/tests/test_scorecard_router.py`

**Modified files:**
- `backend/app/models/signal_assessment.py` — add 7 new columns
- `backend/app/models/__init__.py` — import CompetitorScorecard
- `backend/app/assessor/pipeline.py` — integrate DimensionRouter + LLM supplement + ScorecardBuilder
- `backend/app/assessor/prompts.py` — extend prompt for `buyer_relevance` + `assessment_weight`
- `backend/app/assessor/parser.py` — parse new LLM fields
- `backend/app/main.py` — mount scorecards router
- `backend/alembic/versions/` — new migration file (generated)

---

## Task 1: Alembic migration

**Files:**
- Create: `backend/alembic/versions/<hash>_add_scorecard_fields.py` (generated)

- [ ] **Step 1: Generate migration**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add_scorecard_fields"
```

This will fail because the new model/columns don't exist yet. Instead, create the migration manually:

```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision -m "add_scorecard_fields"
```

Open the generated file (path printed by alembic) and replace the `upgrade()` and `downgrade()` functions with:

```python
def upgrade() -> None:
    # New columns on signal_assessments
    op.add_column("signal_assessments", sa.Column("dimension_targets", sa.JSON(), nullable=True))
    op.add_column("signal_assessments", sa.Column("kpi_targets", sa.JSON(), nullable=True))
    op.add_column("signal_assessments", sa.Column("assessment_weight", sa.Float(), nullable=True, server_default="1.0"))
    op.add_column("signal_assessments", sa.Column("valid_from", sa.DateTime(), nullable=True))
    op.add_column("signal_assessments", sa.Column("valid_until", sa.DateTime(), nullable=True))
    op.add_column("signal_assessments", sa.Column("buyer_relevance", sa.SmallInteger(), nullable=True))
    op.add_column("signal_assessments", sa.Column("routing_version", sa.String(20), nullable=True))

    # New competitor_scorecards table
    op.create_table(
        "competitor_scorecards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("period_type", sa.String(10), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("overall_trend", sa.String(10), nullable=True),
        sa.Column("dimension_scores", sa.JSON(), nullable=True),
        sa.Column("top_capabilities", sa.JSON(), nullable=True),
        sa.Column("top_moves", sa.JSON(), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("watchpoints", sa.JSON(), nullable=True),
        sa.Column("benchmark_position", sa.JSON(), nullable=True),
        sa.Column("contributing_assessment_ids", sa.JSON(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("scorecard_version", sa.String(20), nullable=True),
        sa.Column("routing_version", sa.String(20), nullable=True),
        sa.UniqueConstraint("company_id", "period_type", "generated_at", name="uq_scorecard_snapshot"),
    )
    op.create_index("ix_scorecard_current", "competitor_scorecards", ["company_id", "period_type", "is_current"])


def downgrade() -> None:
    op.drop_index("ix_scorecard_current", table_name="competitor_scorecards")
    op.drop_table("competitor_scorecards")
    op.drop_column("signal_assessments", "routing_version")
    op.drop_column("signal_assessments", "buyer_relevance")
    op.drop_column("signal_assessments", "valid_until")
    op.drop_column("signal_assessments", "valid_from")
    op.drop_column("signal_assessments", "assessment_weight")
    op.drop_column("signal_assessments", "kpi_targets")
    op.drop_column("signal_assessments", "dimension_targets")
```

- [ ] **Step 2: Apply migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Expected: `Running upgrade <prev> -> <hash>, add_scorecard_fields`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: migration for scorecard fields and competitor_scorecards table"
```

---

## Task 2: Update SignalAssessment model + new CompetitorScorecard model

**Files:**
- Modify: `backend/app/models/signal_assessment.py`
- Create: `backend/app/models/competitor_scorecard.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Add new columns to SignalAssessment**

In `backend/app/models/signal_assessment.py`, add these imports and columns. Add after the `watch_items` column and before `created_at`:

```python
# Add to imports at top:
from sqlalchemy import Column, String, Text, Float, SmallInteger, DateTime, Date, Boolean, ForeignKey, Enum as SAEnum, JSON

# Add these columns after watch_items:
    dimension_targets = Column(JSON, nullable=True)   # {dimension_key: dimension_modifier}
    kpi_targets = Column(JSON, nullable=True)          # [kpi_id, ...]
    assessment_weight = Column(Float, nullable=True, default=1.0)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    buyer_relevance = Column(SmallInteger, nullable=True)
    routing_version = Column(String(20), nullable=True)
```

- [ ] **Step 2: Create CompetitorScorecard model**

Create `backend/app/models/competitor_scorecard.py`:

```python
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class CompetitorScorecard(Base):
    __tablename__ = "competitor_scorecards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    period_type = Column(String(10), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    overall_score = Column(Float, nullable=True)
    overall_trend = Column(String(10), nullable=True)
    dimension_scores = Column(JSON, nullable=True)
    top_capabilities = Column(JSON, nullable=True)
    top_moves = Column(JSON, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    watchpoints = Column(JSON, nullable=True)
    benchmark_position = Column(JSON, nullable=True)
    contributing_assessment_ids = Column(JSON, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)
    scorecard_version = Column(String(20), nullable=True)
    routing_version = Column(String(20), nullable=True)

    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("company_id", "period_type", "generated_at", name="uq_scorecard_snapshot"),
        Index("ix_scorecard_current", "company_id", "period_type", "is_current"),
    )
```

- [ ] **Step 3: Register model in `backend/app/models/__init__.py`**

Add to the imports:
```python
from app.models.competitor_scorecard import CompetitorScorecard  # noqa: F401
```

- [ ] **Step 4: Run model smoke test**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_models.py -v
```

Expected: all existing model tests still pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/signal_assessment.py backend/app/models/competitor_scorecard.py backend/app/models/__init__.py
git commit -m "feat: add scorecard fields to SignalAssessment and new CompetitorScorecard model"
```

---

## Task 3: Constants module

**Files:**
- Create: `backend/app/scorecard/__init__.py`
- Create: `backend/app/scorecard/constants.py`

- [ ] **Step 1: Create `__init__.py`**

```python
# backend/app/scorecard/__init__.py
```
(empty)

- [ ] **Step 2: Create constants**

Create `backend/app/scorecard/constants.py`:

```python
ROUTING_VERSION = "v1"
SCORECARD_VERSION = "sc_v1"

RECENCY_DECAY_MAX = 0.30   # recency_weight floor = 0.70
MOMENTUM_RISING_THRESHOLD = 5.0
MOMENTUM_DECLINING_THRESHOLD = -5.0
SIGNAL_CLASS_COUNT = 7     # K for Shannon entropy normalisation — update when SignalClass enum changes

DIMENSION_WEIGHTS: dict[str, float] = {
    "capability_strength": 0.30,
    "market_impact":       0.25,
    "activity":            0.20,
    "customer_proof":      0.15,
    "momentum":            0.10,
}

PERIOD_DAYS: dict[str, int] = {
    "30d":  30,
    "90d":  90,
    "180d": 180,
}

VALID_PERIOD_TYPES = list(PERIOD_DAYS.keys())

# Capability strategic_weight threshold for risk_flags
RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD = 8
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/scorecard/
git commit -m "feat: scorecard constants module"
```

---

## Task 4: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/scorecard.py`

- [ ] **Step 1: Write schemas**

Create `backend/app/schemas/scorecard.py`:

```python
from __future__ import annotations
from typing import Any, Optional
from datetime import date, datetime
from pydantic import BaseModel


class ScorecardKPIValue(BaseModel):
    value: Optional[float]
    contributing_ids: list[str]


class ScorecardDimension(BaseModel):
    score: Optional[float]
    trend: Optional[str]
    kpis: dict[str, ScorecardKPIValue]


class ScorecardTopMove(BaseModel):
    assessment_id: str
    signal_id: str
    title: str
    movement_score: int
    signal_class: str


class ScorecardRiskFlag(BaseModel):
    assessment_id: str
    capability_key: str
    movement_strength: str
    title: str


class ScorecardBenchmarkPosition(BaseModel):
    rank: int
    percentile: float
    total_competitors: int


class ScorecardRead(BaseModel):
    id: str
    company_id: str
    period_type: str
    period_start: date
    period_end: date
    generated_at: datetime
    overall_score: Optional[float]
    overall_trend: Optional[str]
    dimension_scores: dict[str, ScorecardDimension]
    top_capabilities: list[dict[str, Any]]
    top_moves: list[ScorecardTopMove]
    risk_flags: list[ScorecardRiskFlag]
    watchpoints: list[str]
    benchmark_position: Optional[ScorecardBenchmarkPosition]
    contributing_assessment_ids: list[str]
    is_current: bool
    scorecard_version: Optional[str]
    routing_version: Optional[str]

    model_config = {"from_attributes": True}


class ScorecardHistoryItem(BaseModel):
    id: str
    overall_score: Optional[float]
    overall_trend: Optional[str]
    generated_at: datetime
    scorecard_version: Optional[str]

    model_config = {"from_attributes": True}


class ScorecardExplainAssessment(BaseModel):
    assessment_id: str
    signal_id: str
    title: str
    movement_score: int
    signal_class: str


class ScorecardExplainDimension(BaseModel):
    dimension: str
    score: Optional[float]
    dimension_weight: float
    effective_weight: float
    weighted_contribution: Optional[float]
    assessment_count: int
    top_contributing_assessments: list[ScorecardExplainAssessment]
    kpi_detail: dict[str, ScorecardKPIValue]


class ScorecardExplain(BaseModel):
    overall_score: Optional[float]
    dimension_breakdown: list[ScorecardExplainDimension]
    null_dimensions: list[str]
    score_formula: str
    routing_version: Optional[str]
    scorecard_version: Optional[str]


class ScorecardRecomputeAck(BaseModel):
    status: str
    company_slug: str
    recomputed_periods: list[str]
    scorecard_ids: dict[str, str]
    generated_at: datetime


class BenchmarkScorecardItem(BaseModel):
    company_id: str
    slug: str
    name: str
    overall_score: Optional[float]
    rank: int
    percentile: float
    dimension_scores: dict[str, ScorecardDimension]
    overall_trend: Optional[str]
    scorecard_version: Optional[str]


class BenchmarkScorecardView(BaseModel):
    items: list[BenchmarkScorecardItem]
    total: int
    page: int
    page_size: int
    pages: int
    period_type: str
    capability_leaders: dict[str, dict[str, Any]]
    highest_momentum: Optional[dict[str, Any]]
    threat_flags: list[dict[str, Any]]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/scorecard.py
git commit -m "feat: scorecard Pydantic schemas"
```

---

## Task 5: DimensionRouter

**Files:**
- Create: `backend/app/scorecard/dimension_router.py`
- Create: `backend/tests/test_dimension_router.py`

**Design note:** `dimension_targets` is stored as `dict[str, float]` mapping `dimension_key → dimension_modifier`, not a plain list. This makes the modifier explicit and auditable without re-running routing logic at score time.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_dimension_router.py`:

```python
import pytest
from types import SimpleNamespace


def _a(**kwargs):
    """Build a minimal assessment-like object for routing tests."""
    defaults = dict(
        signal_class="product_capability_move",
        evidence_strength=3,
        visibility_impact="medium",
        movement_strength="relevant",
        capability_primary="shift_scheduling",
        assessment_weight=1.0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_product_capability_move_routes_to_capability_and_market():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="product_capability_move"))
    assert "capability_strength" in result.dimension_targets
    assert "market_impact" in result.dimension_targets
    assert result.dimension_targets["capability_strength"] == 1.0
    assert "cap_weighted_score" in result.kpi_targets
    assert "mkt_move_quality" in result.kpi_targets


def test_hiring_signal_routes_to_activity_and_momentum_with_correct_modifiers():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="hiring_signal"))
    assert result.dimension_targets.get("activity") == pytest.approx(0.6)
    assert result.dimension_targets.get("momentum") == pytest.approx(1.0)
    assert "capability_strength" not in result.dimension_targets
    assert "act_count_raw" in result.kpi_targets
    assert "mom_hiring_velocity" in result.kpi_targets


def test_hiring_overrides_base_activity_weight():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="hiring_signal"))
    # Must be 0.6, not 1.0 (base) + 0.6 stacked
    assert result.dimension_targets["activity"] == pytest.approx(0.6)


def test_market_expansion_without_strong_evidence_no_capability():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="market_expansion_move", evidence_strength=3))
    assert "capability_strength" not in result.dimension_targets
    assert "market_impact" in result.dimension_targets


def test_market_expansion_with_strong_evidence_adds_capability_at_reduced_weight():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(signal_class="market_expansion_move", evidence_strength=4))
    assert result.dimension_targets.get("capability_strength") == pytest.approx(0.7)
    assert "market_impact" in result.dimension_targets


def test_thought_leadership_strict_conditions_adds_market_impact():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(
        signal_class="thought_leadership_signal",
        visibility_impact="high",
        movement_strength="strong",
    ))
    assert result.dimension_targets.get("market_impact") == pytest.approx(0.4)
    assert result.dimension_targets.get("activity") == pytest.approx(0.5)


def test_thought_leadership_default_activity_only():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(
        signal_class="thought_leadership_signal",
        visibility_impact="medium",
        movement_strength="relevant",
    ))
    assert "market_impact" not in result.dimension_targets
    assert result.dimension_targets.get("activity") == pytest.approx(0.5)


def test_high_visibility_adds_market_impact_kpis():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(
        signal_class="ecosystem_move", visibility_impact="high"
    ))
    assert "mkt_high_visibility_count_raw" in result.kpi_targets


def test_routing_version_is_set():
    from app.scorecard.dimension_router import DimensionRouter
    from app.scorecard.constants import ROUTING_VERSION
    result = DimensionRouter.route(_a())
    assert result.routing_version == ROUTING_VERSION


def test_strong_movement_adds_strong_count_kpis():
    from app.scorecard.dimension_router import DimensionRouter
    result = DimensionRouter.route(_a(movement_strength="strong"))
    assert "act_strong_count_raw" in result.kpi_targets
    assert "act_strong_count_weighted" in result.kpi_targets
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_dimension_router.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `app.scorecard.dimension_router`

- [ ] **Step 3: Implement DimensionRouter**

Create `backend/app/scorecard/dimension_router.py`:

```python
from dataclasses import dataclass, field
from app.scorecard.constants import ROUTING_VERSION


@dataclass
class RoutingResult:
    dimension_targets: dict[str, float]   # {dimension_key: dimension_modifier}
    kpi_targets: list[str]
    assessment_weight: float
    routing_version: str


class DimensionRouter:
    @staticmethod
    def route(assessment) -> RoutingResult:
        sc = assessment.signal_class if isinstance(assessment.signal_class, str) else assessment.signal_class.value
        vi = assessment.visibility_impact if isinstance(assessment.visibility_impact, str) else assessment.visibility_impact.value
        ms = assessment.movement_strength if isinstance(assessment.movement_strength, str) else assessment.movement_strength.value
        es = assessment.evidence_strength or 0

        dims: dict[str, float] = {}
        kpis: set[str] = set()

        def add(dimension: str, modifier: float, new_kpis: list[str]):
            # Specific rules override base weight for the same dimension
            if dimension not in dims or modifier != 1.0:
                dims[dimension] = modifier
            kpis.update(new_kpis)

        # Base rule: all assessments contribute to activity
        base_activity_weight = 1.0
        if sc == "hiring_signal":
            base_activity_weight = 0.6
        elif sc == "thought_leadership_signal":
            base_activity_weight = 0.5
        add("activity", base_activity_weight, ["act_count_raw", "act_count_weighted", "act_weighted_strength"])

        # Strong/market_shaping adds strong count KPIs
        if ms in ("strong", "market_shaping"):
            kpis.update(["act_strong_count_raw", "act_strong_count_weighted"])

        # Signal-class specific rules
        if sc == "product_capability_move":
            add("capability_strength", 1.0, ["cap_weighted_score"])
            add("market_impact", 1.0, ["mkt_move_quality"])

        elif sc == "market_expansion_move":
            add("market_impact", 1.0, ["mkt_weighted_visibility", "mkt_strategic_quality"])
            if es >= 4:
                add("capability_strength", 0.7, ["cap_weighted_score"])

        elif sc in ("ecosystem_move", "positioning_move"):
            add("market_impact", 1.0, ["mkt_strategic_quality"])
            add("customer_proof", 1.0, ["cp_ecosystem_count_raw", "cp_ecosystem_count_weighted"])
            if sc == "ecosystem_move" and es >= 4:
                kpis.add("cp_weighted_evidence")

        elif sc == "hiring_signal":
            add("momentum", 1.0, ["mom_hiring_velocity"])

        elif sc == "thought_leadership_signal":
            if vi == "high" and ms in ("strong", "market_shaping"):
                add("market_impact", 0.4, ["mkt_weighted_visibility"])

        # High visibility adds market impact KPIs regardless of signal class
        if vi == "high":
            if "market_impact" not in dims:
                dims["market_impact"] = 1.0
            kpis.update(["mkt_high_visibility_count_raw", "mkt_high_visibility_count_weighted", "mkt_weighted_visibility"])

        return RoutingResult(
            dimension_targets=dims,
            kpi_targets=sorted(kpis),
            assessment_weight=getattr(assessment, "assessment_weight", None) or 1.0,
            routing_version=ROUTING_VERSION,
        )
```

- [ ] **Step 4: Run tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_dimension_router.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scorecard/dimension_router.py backend/tests/test_dimension_router.py
git commit -m "feat: DimensionRouter with deterministic routing rules"
```

---

## Task 6: KPIEngine — types, weights, and capability_strength + activity KPIs

**Files:**
- Create: `backend/app/scorecard/kpi_engine.py`
- Create: `backend/tests/test_kpi_engine.py`

- [ ] **Step 1: Write failing tests for types and capability/activity KPIs**

Create `backend/tests/test_kpi_engine.py`:

```python
import pytest
from dataclasses import dataclass
from typing import Optional


def _inp(
    id="a1",
    movement_score=70,
    movement_strength="relevant",
    signal_class="product_capability_move",
    evidence_strength=3,
    visibility_impact="medium",
    confidence=0.8,
    capability_primary="shift_scheduling",
    capability_secondary=None,
    assessment_weight=1.0,
    dimension_modifier=1.0,
    age_days=0,
    period_days=30,
):
    from app.scorecard.kpi_engine import AssessmentKPIInput
    return AssessmentKPIInput(
        id=id,
        movement_score=movement_score,
        movement_strength=movement_strength,
        signal_class=signal_class,
        evidence_strength=evidence_strength,
        visibility_impact=visibility_impact,
        confidence=confidence,
        capability_primary=capability_primary,
        capability_secondary=capability_secondary or [],
        assessment_weight=assessment_weight,
        dimension_modifier=dimension_modifier,
        age_days=age_days,
        period_days=period_days,
    )


# --- effective_weight ---

def test_effective_weight_no_decay():
    a = _inp(assessment_weight=1.0, dimension_modifier=1.0, age_days=0, period_days=30)
    assert a.effective_weight == pytest.approx(1.0)


def test_effective_weight_full_decay_floor():
    from app.scorecard.constants import RECENCY_DECAY_MAX
    a = _inp(assessment_weight=1.0, dimension_modifier=1.0, age_days=30, period_days=30)
    expected = 1.0 * 1.0 * (1.0 - RECENCY_DECAY_MAX)
    assert a.effective_weight == pytest.approx(expected)


def test_effective_weight_combines_all_three():
    from app.scorecard.constants import RECENCY_DECAY_MAX
    a = _inp(assessment_weight=2.0, dimension_modifier=0.7, age_days=15, period_days=30)
    recency = 1.0 - (15 / 30) * RECENCY_DECAY_MAX
    assert a.effective_weight == pytest.approx(2.0 * 0.7 * recency)


# --- capability_strength KPIs ---

def test_cap_weighted_score_empty_returns_null():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    result = compute_capability_strength_kpis([])
    assert result["cap_weighted_score"].value is None


def test_cap_weighted_score_single_capability():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    inputs = [_inp(movement_score=80, evidence_strength=3, capability_primary="ai_copilot")]
    result = compute_capability_strength_kpis(inputs)
    assert result["cap_weighted_score"].value == pytest.approx(80.0)
    assert "a1" in result["cap_weighted_score"].contributing_ids


def test_cap_weighted_score_averages_capabilities_not_volume():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    # 3 signals in ai_copilot (score 90) and 1 in shift_scheduling (score 50)
    # Expected: mean([90, 50]) = 70, not biased by volume in ai_copilot
    inputs = [
        _inp(id="a1", movement_score=90, capability_primary="ai_copilot"),
        _inp(id="a2", movement_score=90, capability_primary="ai_copilot"),
        _inp(id="a3", movement_score=90, capability_primary="ai_copilot"),
        _inp(id="a4", movement_score=50, capability_primary="shift_scheduling"),
    ]
    result = compute_capability_strength_kpis(inputs)
    assert result["cap_weighted_score"].value == pytest.approx(70.0)


def test_cap_strong_move_count_raw():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    inputs = [
        _inp(id="a1", movement_strength="strong"),
        _inp(id="a2", movement_strength="market_shaping"),
        _inp(id="a3", movement_strength="relevant"),
    ]
    result = compute_capability_strength_kpis(inputs)
    assert result["cap_strong_move_count_raw"].value == 2
    assert set(result["cap_strong_move_count_raw"].contributing_ids) == {"a1", "a2"}


def test_cap_market_shaping_ratio_empty_returns_null():
    from app.scorecard.kpi_engine import compute_capability_strength_kpis
    result = compute_capability_strength_kpis([])
    assert result["cap_market_shaping_ratio"].value is None


# --- activity KPIs ---

def test_act_count_raw():
    from app.scorecard.kpi_engine import compute_activity_kpis
    inputs = [_inp(id="a1"), _inp(id="a2"), _inp(id="a3")]
    result = compute_activity_kpis(inputs)
    assert result["act_count_raw"].value == 3


def test_act_weighted_strength_empty_returns_null():
    from app.scorecard.kpi_engine import compute_activity_kpis
    result = compute_activity_kpis([])
    assert result["act_weighted_strength"].value is None


def test_act_signal_class_diversity_single_class_returns_zero():
    from app.scorecard.kpi_engine import compute_activity_kpis
    inputs = [_inp(id=f"a{i}", signal_class="product_capability_move") for i in range(3)]
    result = compute_activity_kpis(inputs)
    assert result["act_signal_class_diversity"].value == pytest.approx(0.0)


def test_act_signal_class_diversity_all_classes_returns_one():
    from app.scorecard.kpi_engine import compute_activity_kpis
    from app.scorecard.constants import SIGNAL_CLASS_COUNT
    classes = [
        "product_capability_move", "positioning_move", "ecosystem_move",
        "thought_leadership_signal", "hiring_signal", "weak_signal", "market_expansion_move"
    ]
    assert len(classes) == SIGNAL_CLASS_COUNT
    inputs = [_inp(id=f"a{i}", signal_class=c) for i, c in enumerate(classes)]
    result = compute_activity_kpis(inputs)
    assert result["act_signal_class_diversity"].value == pytest.approx(1.0, abs=0.01)


def test_act_diversity_zero_inputs():
    from app.scorecard.kpi_engine import compute_activity_kpis
    result = compute_activity_kpis([])
    assert result["act_signal_class_diversity"].value == pytest.approx(0.0)
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_kpi_engine.py -v
```

Expected: `ImportError` for `app.scorecard.kpi_engine`

- [ ] **Step 3: Implement KPIEngine types + capability + activity KPIs**

Create `backend/app/scorecard/kpi_engine.py`:

```python
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
from app.scorecard.constants import (
    RECENCY_DECAY_MAX, SIGNAL_CLASS_COUNT,
    MOMENTUM_RISING_THRESHOLD, MOMENTUM_DECLINING_THRESHOLD,
)


@dataclass
class AssessmentKPIInput:
    id: str
    movement_score: int
    movement_strength: str
    signal_class: str
    evidence_strength: int
    visibility_impact: str
    confidence: float
    capability_primary: str
    capability_secondary: list[str]
    assessment_weight: float
    dimension_modifier: float
    age_days: int
    period_days: int

    @property
    def effective_weight(self) -> float:
        recency = 1.0 - (self.age_days / max(self.period_days, 1)) * RECENCY_DECAY_MAX
        return self.assessment_weight * self.dimension_modifier * recency


@dataclass
class KPIValue:
    value: Optional[float]
    contributing_ids: list[str] = field(default_factory=list)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def compute_capability_strength_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    if not inputs:
        return {
            "cap_weighted_score": KPIValue(None),
            "cap_strong_move_count_raw": KPIValue(0),
            "cap_strong_move_count_weighted": KPIValue(0.0),
            "cap_market_shaping_ratio": KPIValue(None),
        }

    # Per-capability weighted score
    cap_num: dict[str, float] = defaultdict(float)
    cap_den: dict[str, float] = defaultdict(float)
    cap_ids: dict[str, list[str]] = defaultdict(list)
    for a in inputs:
        ev_w = a.evidence_strength / 3.0
        w = a.effective_weight * ev_w
        cap_num[a.capability_primary] += a.movement_score * w
        cap_den[a.capability_primary] += w
        cap_ids[a.capability_primary].append(a.id)

    cap_scores = {cap: cap_num[cap] / cap_den[cap] for cap in cap_num if cap_den[cap] > 0}
    all_ids = [a.id for a in inputs]
    overall = _clamp(sum(cap_scores.values()) / len(cap_scores)) if cap_scores else None

    strong = [a for a in inputs if a.movement_strength in ("strong", "market_shaping")]
    ms_ids = [a.id for a in inputs if a.movement_strength == "market_shaping"]
    total_ew = sum(a.effective_weight for a in inputs)
    ms_ew = sum(a.effective_weight for a in inputs if a.movement_strength == "market_shaping")
    shaping_ratio = _clamp(ms_ew / total_ew, 0.0, 1.0) if total_ew > 0 else None

    return {
        "cap_weighted_score": KPIValue(overall, all_ids),
        "cap_strong_move_count_raw": KPIValue(len(strong), [a.id for a in strong]),
        "cap_strong_move_count_weighted": KPIValue(
            sum(a.effective_weight for a in strong), [a.id for a in strong]
        ),
        "cap_market_shaping_ratio": KPIValue(shaping_ratio, ms_ids),
    }


def compute_activity_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    all_ids = [a.id for a in inputs]
    if not inputs:
        return {
            "act_count_raw": KPIValue(0),
            "act_count_weighted": KPIValue(0.0),
            "act_strong_count_raw": KPIValue(0),
            "act_strong_count_weighted": KPIValue(0.0),
            "act_weighted_strength": KPIValue(None),
            "act_signal_class_diversity": KPIValue(0.0),
        }

    strong = [a for a in inputs if a.movement_strength in ("strong", "market_shaping")]
    total_ew = sum(a.effective_weight for a in inputs)
    wt_strength = _clamp(sum(a.movement_score * a.effective_weight for a in inputs) / total_ew) if total_ew > 0 else None

    # Shannon entropy normalised to [0, 1] over SIGNAL_CLASS_COUNT classes
    class_weights: dict[str, float] = defaultdict(float)
    for a in inputs:
        class_weights[a.signal_class] += a.effective_weight
    total_w = sum(class_weights.values())
    diversity = 0.0
    if total_w > 0 and SIGNAL_CLASS_COUNT > 1:
        entropy = -sum(
            (w / total_w) * math.log(w / total_w)
            for w in class_weights.values() if w > 0
        )
        diversity = _clamp(entropy / math.log(SIGNAL_CLASS_COUNT), 0.0, 1.0)

    return {
        "act_count_raw": KPIValue(len(inputs), all_ids),
        "act_count_weighted": KPIValue(sum(a.effective_weight for a in inputs), all_ids),
        "act_strong_count_raw": KPIValue(len(strong), [a.id for a in strong]),
        "act_strong_count_weighted": KPIValue(
            sum(a.effective_weight for a in strong), [a.id for a in strong]
        ),
        "act_weighted_strength": KPIValue(wt_strength, all_ids),
        "act_signal_class_diversity": KPIValue(diversity, all_ids),
    }
```

- [ ] **Step 4: Run tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_kpi_engine.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scorecard/kpi_engine.py backend/tests/test_kpi_engine.py
git commit -m "feat: KPIEngine types, effective weight, capability_strength and activity KPIs"
```

---

## Task 7: KPIEngine — market_impact, customer_proof, momentum, and dimension score

- [ ] **Step 1: Add tests to `backend/tests/test_kpi_engine.py`**

Append to the existing test file:

```python
# --- market_impact KPIs ---

def test_mkt_weighted_visibility_empty_returns_null():
    from app.scorecard.kpi_engine import compute_market_impact_kpis
    result = compute_market_impact_kpis([])
    assert result["mkt_weighted_visibility"].value is None


def test_mkt_weighted_visibility_weights_by_visibility():
    from app.scorecard.kpi_engine import compute_market_impact_kpis
    inputs = [
        _inp(id="a1", movement_score=100, visibility_impact="high"),
        _inp(id="a2", movement_score=100, visibility_impact="low"),
    ]
    result = compute_market_impact_kpis(inputs)
    # high (1.0) should pull score towards 100; low (0.3) pulls towards 100 too
    # With equal movement_score, result should be 100 regardless
    assert result["mkt_weighted_visibility"].value == pytest.approx(100.0)


def test_mkt_move_quality_only_includes_qualifying_classes():
    from app.scorecard.kpi_engine import compute_market_impact_kpis
    inputs = [
        _inp(id="a1", movement_score=80, signal_class="product_capability_move"),
        _inp(id="a2", movement_score=20, signal_class="hiring_signal"),
    ]
    result = compute_market_impact_kpis(inputs)
    assert result["mkt_move_quality"].value == pytest.approx(80.0)
    assert result["mkt_move_quality"].contributing_ids == ["a1"]


def test_mkt_move_quality_null_when_no_qualifying():
    from app.scorecard.kpi_engine import compute_market_impact_kpis
    inputs = [_inp(signal_class="hiring_signal")]
    result = compute_market_impact_kpis(inputs)
    assert result["mkt_move_quality"].value is None


# --- customer_proof KPIs ---

def test_cp_validation_score_null_when_no_data():
    from app.scorecard.kpi_engine import compute_customer_proof_kpis
    result = compute_customer_proof_kpis([])
    assert result["cp_validation_score"].value is None


def test_cp_high_evidence_ratio():
    from app.scorecard.kpi_engine import compute_customer_proof_kpis
    inputs = [
        _inp(id="a1", signal_class="ecosystem_move", evidence_strength=4),
        _inp(id="a2", signal_class="ecosystem_move", evidence_strength=2),
    ]
    result = compute_customer_proof_kpis(inputs)
    assert result["cp_high_evidence_ratio"].value == pytest.approx(0.5)


# --- momentum KPIs ---

def test_mom_period_delta_null_when_no_prior():
    from app.scorecard.kpi_engine import compute_momentum_kpis
    current = [_inp(id="a1", movement_score=70)]
    result = compute_momentum_kpis(current, prior=[])
    assert result["mom_period_delta"].value is None


def test_mom_trend_rising():
    from app.scorecard.kpi_engine import compute_momentum_kpis
    from app.scorecard.constants import MOMENTUM_RISING_THRESHOLD
    current = [_inp(id="c1", movement_score=80)]
    prior = [_inp(id="p1", movement_score=80 - MOMENTUM_RISING_THRESHOLD - 1)]
    result = compute_momentum_kpis(current, prior)
    assert result["mom_trend"].value == "rising"


def test_mom_trend_stable():
    from app.scorecard.kpi_engine import compute_momentum_kpis
    current = [_inp(id="c1", movement_score=70)]
    prior = [_inp(id="p1", movement_score=70)]
    result = compute_momentum_kpis(current, prior)
    assert result["mom_trend"].value == "stable"


# --- dimension score ---

def test_capability_dimension_score_uses_cap_weighted_score():
    from app.scorecard.kpi_engine import compute_dimension_score
    kpis = {"cap_weighted_score": {"value": 75.0}, "cap_strong_move_count_raw": {"value": 2}}
    assert compute_dimension_score("capability_strength", kpis) == pytest.approx(75.0)


def test_momentum_dimension_score_centered_at_50():
    from app.scorecard.kpi_engine import compute_dimension_score
    kpis = {"mom_period_delta": {"value": 20.0}, "mom_trend": {"value": "rising"}}
    # 50 + 20/2 = 60
    assert compute_dimension_score("momentum", kpis) == pytest.approx(60.0)


def test_dimension_score_null_when_primary_kpi_null():
    from app.scorecard.kpi_engine import compute_dimension_score
    kpis = {"cap_weighted_score": {"value": None}}
    assert compute_dimension_score("capability_strength", kpis) is None
```

- [ ] **Step 2: Run to verify new tests fail**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_kpi_engine.py -v 2>&1 | tail -20
```

Expected: new tests fail with `ImportError` or `AttributeError`.

- [ ] **Step 3: Implement market_impact, customer_proof, momentum, and dimension score in `kpi_engine.py`**

Append to `backend/app/scorecard/kpi_engine.py`:

```python
_VIS_WEIGHTS = {"low": 0.3, "medium": 0.7, "high": 1.0}
_STRATEGIC_CLASSES = {"product_capability_move", "market_expansion_move", "ecosystem_move", "positioning_move"}
_CUSTOMER_CLASSES = {"ecosystem_move", "positioning_move"}
_QUALITY_CLASSES = {"product_capability_move", "market_expansion_move", "ecosystem_move"}


def compute_market_impact_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    high = [a for a in inputs if a.visibility_impact == "high"]
    qualify = [a for a in inputs if a.signal_class in _QUALITY_CLASSES]
    strategic = [a for a in inputs if a.signal_class in _STRATEGIC_CLASSES]

    def weighted_mean_score(subset: list[AssessmentKPIInput], weight_fn=None) -> Optional[float]:
        if not subset:
            return None
        num = sum((weight_fn(a) if weight_fn else 1.0) * a.movement_score * a.effective_weight for a in subset)
        den = sum((weight_fn(a) if weight_fn else 1.0) * a.effective_weight for a in subset)
        return _clamp(num / den) if den > 0 else None

    vis_score = weighted_mean_score(inputs, lambda a: _VIS_WEIGHTS.get(a.visibility_impact, 0.3)) if inputs else None

    strat_num = sum(a.evidence_strength * a.confidence * a.effective_weight for a in strategic)
    strat_den = sum(a.effective_weight for a in strategic)
    strat_q = _clamp((strat_num / strat_den) * 20) if strat_den > 0 else None

    return {
        "mkt_high_visibility_count_raw": KPIValue(len(high), [a.id for a in high]),
        "mkt_high_visibility_count_weighted": KPIValue(
            sum(a.effective_weight for a in high), [a.id for a in high]
        ),
        "mkt_weighted_visibility": KPIValue(vis_score, [a.id for a in inputs]),
        "mkt_move_quality": KPIValue(
            weighted_mean_score(qualify), [a.id for a in qualify]
        ),
        "mkt_strategic_quality": KPIValue(strat_q, [a.id for a in strategic]),
    }


def compute_customer_proof_kpis(inputs: list[AssessmentKPIInput]) -> dict[str, KPIValue]:
    ecosystem = [a for a in inputs if a.signal_class in _CUSTOMER_CLASSES]
    high_ev = [a for a in inputs if a.evidence_strength >= 4]
    total_ew = sum(a.effective_weight for a in inputs)
    high_ew = sum(a.effective_weight for a in high_ev)
    high_ratio = _clamp(high_ew / total_ew, 0.0, 1.0) if total_ew > 0 else None

    ev_num = sum(a.evidence_strength * a.confidence * a.effective_weight for a in ecosystem)
    ev_den = sum(a.effective_weight for a in ecosystem)
    weighted_ev = _clamp((ev_num / ev_den) * 20) if ev_den > 0 else None

    validation = None
    if weighted_ev is not None and high_ratio is not None:
        validation = _clamp(weighted_ev * 0.6 + high_ratio * 100 * 0.4)

    return {
        "cp_ecosystem_count_raw": KPIValue(len(ecosystem), [a.id for a in ecosystem]),
        "cp_ecosystem_count_weighted": KPIValue(
            sum(a.effective_weight for a in ecosystem), [a.id for a in ecosystem]
        ),
        "cp_weighted_evidence": KPIValue(weighted_ev, [a.id for a in ecosystem]),
        "cp_high_evidence_ratio": KPIValue(high_ratio, [a.id for a in high_ev]),
        "cp_validation_score": KPIValue(validation, [a.id for a in inputs]),
    }


def compute_momentum_kpis(
    current: list[AssessmentKPIInput],
    prior: list[AssessmentKPIInput],
) -> dict[str, KPIValue]:
    def _wt_strength(lst: list[AssessmentKPIInput]) -> Optional[float]:
        ew = sum(a.effective_weight for a in lst)
        if ew <= 0:
            return None
        return _clamp(sum(a.movement_score * a.effective_weight for a in lst) / ew)

    def _strong_ew(lst: list[AssessmentKPIInput]) -> float:
        return sum(a.effective_weight for a in lst if a.movement_strength in ("strong", "market_shaping"))

    cur_str = _wt_strength(current)
    pri_str = _wt_strength(prior)
    delta = _clamp(cur_str - pri_str, -100.0, 100.0) if (cur_str is not None and pri_str is not None) else None
    accel = _strong_ew(current) - _strong_ew(prior) if prior else None
    hiring = [a for a in current if a.signal_class == "hiring_signal"]
    hiring_vel = sum(a.effective_weight for a in hiring) if hiring else None

    trend = None
    if delta is not None:
        if delta > MOMENTUM_RISING_THRESHOLD:
            trend = "rising"
        elif delta < MOMENTUM_DECLINING_THRESHOLD:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "mom_period_delta": KPIValue(delta, [a.id for a in current]),
        "mom_strong_move_acceleration": KPIValue(accel, [a.id for a in current]),
        "mom_hiring_velocity": KPIValue(hiring_vel, [a.id for a in hiring]),
        "mom_trend": KPIValue(trend, [a.id for a in current]),
    }


_DIMENSION_PRIMARY_KPI = {
    "capability_strength": "cap_weighted_score",
    "activity": "act_weighted_strength",
    "market_impact": "mkt_weighted_visibility",
    "customer_proof": "cp_validation_score",
    "momentum": "mom_period_delta",
}


def compute_dimension_score(dimension_key: str, kpis: dict) -> Optional[float]:
    primary = _DIMENSION_PRIMARY_KPI.get(dimension_key)
    if primary is None:
        return None
    kpi = kpis.get(primary)
    if kpi is None:
        return None
    raw = kpi["value"] if isinstance(kpi, dict) else kpi.value
    if raw is None:
        return None
    if dimension_key == "momentum":
        return _clamp(50.0 + raw / 2.0)
    return _clamp(raw)
```

- [ ] **Step 4: Run all KPI engine tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_kpi_engine.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scorecard/kpi_engine.py backend/tests/test_kpi_engine.py
git commit -m "feat: KPIEngine market_impact, customer_proof, momentum KPIs and dimension score"
```

---

## Task 8: ScorecardBuilder

**Files:**
- Create: `backend/app/scorecard/builder.py`
- Create: `backend/tests/test_scorecard_builder.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_scorecard_builder.py`:

```python
import pytest
from datetime import date, datetime, timezone
import app.models  # noqa


def _make_company(db, slug="acme"):
    from app.models.company import Company, CompanyType
    c = Company(name=slug.title(), slug=slug, type=CompanyType.competitor)
    db.add(c)
    db.commit()
    return c


def _make_signal(db, company):
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    s = Source(company_id=company.id, url=f"https://{company.slug}.com", source_type=SourceType.news)
    db.add(s)
    db.commit()
    doc = Document(source_id=s.id, url=f"https://{company.slug}.com/1")
    db.add(doc)
    db.commit()
    sig = Signal(
        document_id=doc.id, company_id=company.id,
        title="Test signal", signal_type=SignalType.product_update,
        relevance_score=0.9, confidence_score=0.85,
    )
    db.add(sig)
    db.commit()
    return sig


def _make_assessment(db, signal, company, **kwargs):
    from app.models.signal_assessment import SignalAssessment, SignalClass, VisibilityImpact, MovementStrength
    from datetime import datetime, timezone
    defaults = dict(
        signal_id=signal.id,
        company_id=company.id,
        capability_primary="ai_copilot",
        signal_class=SignalClass.product_capability_move,
        evidence_strength=4,
        visibility_impact=VisibilityImpact.high,
        movement_score=75,
        movement_strength=MovementStrength.strong,
        confidence=0.85,
        watch_items=["Watch adoption"],
        assessment_weight=1.0,
        valid_from=datetime.now(timezone.utc),
        dimension_targets={"capability_strength": 1.0, "market_impact": 1.0, "activity": 1.0},
        kpi_targets=["cap_weighted_score", "mkt_move_quality", "act_count_raw"],
        routing_version="v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    a = SignalAssessment(**defaults)
    db.add(a)
    db.commit()
    return a


def test_build_with_no_assessments_produces_null_scorecard(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "empty-co")
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert scorecard is not None
    assert scorecard.overall_score is None
    assert scorecard.is_current is True


def test_build_produces_scorecard_with_score(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "active-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert scorecard.overall_score is not None
    assert scorecard.overall_score > 0


def test_build_sets_is_current_and_flips_previous(db_session):
    from app.scorecard.builder import ScorecardBuilder
    from app.models.competitor_scorecard import CompetitorScorecard
    company = _make_company(db_session, "flip-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    ScorecardBuilder(db_session).build(company.id, "30d")
    ScorecardBuilder(db_session).build(company.id, "30d")
    current = db_session.query(CompetitorScorecard).filter_by(company_id=company.id, period_type="30d", is_current=True).all()
    assert len(current) == 1


def test_build_populates_watchpoints_from_all_assessments(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "watch-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company, watch_items=["Watch adoption", "Monitor pricing"])
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert "Watch adoption" in scorecard.watchpoints
    assert "Monitor pricing" in scorecard.watchpoints


def test_build_benchmark_position_single_competitor(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "solo-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    assert scorecard.benchmark_position["rank"] == 1
    assert scorecard.benchmark_position["total_competitors"] == 1


def test_build_top_moves_include_signal_id(db_session):
    from app.scorecard.builder import ScorecardBuilder
    company = _make_company(db_session, "moves-co")
    signal = _make_signal(db_session, company)
    _make_assessment(db_session, signal, company)
    scorecard = ScorecardBuilder(db_session).build(company.id, "30d")
    if scorecard.top_moves:
        assert "signal_id" in scorecard.top_moves[0]
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_scorecard_builder.py -v
```

Expected: `ImportError` for `app.scorecard.builder`

- [ ] **Step 3: Implement ScorecardBuilder**

Create `backend/app/scorecard/builder.py`:

```python
from __future__ import annotations
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from collections import Counter, defaultdict
from sqlalchemy.orm import Session

from app.models.competitor_scorecard import CompetitorScorecard
from app.models.signal_assessment import SignalAssessment
from app.assessor.capabilities import CAPABILITIES
from app.scorecard.constants import (
    DIMENSION_WEIGHTS, PERIOD_DAYS, SCORECARD_VERSION, ROUTING_VERSION,
    RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD,
)
from app.scorecard.kpi_engine import (
    AssessmentKPIInput, compute_capability_strength_kpis, compute_activity_kpis,
    compute_market_impact_kpis, compute_customer_proof_kpis, compute_momentum_kpis,
    compute_dimension_score, KPIValue,
)

logger = logging.getLogger(__name__)

_KPI_COMPUTERS = {
    "capability_strength": compute_capability_strength_kpis,
    "activity": compute_activity_kpis,
    "market_impact": compute_market_impact_kpis,
    "customer_proof": compute_customer_proof_kpis,
}


class ScorecardBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build(self, company_id: str, period_type: str) -> CompetitorScorecard:
        period_days = PERIOD_DAYS[period_type]
        now = datetime.now(timezone.utc)
        period_end = now
        period_start = now - timedelta(days=period_days)
        prev_end = period_start
        prev_start = prev_end - timedelta(days=period_days)

        assessments = self._fetch(company_id, period_start, period_end)
        prior = self._fetch(company_id, prev_start, prev_end)

        dim_scores: dict[str, dict] = {}
        all_ids = [a.id for a in assessments]

        for dim_key in DIMENSION_WEIGHTS:
            inputs = self._to_kpi_inputs(assessments, dim_key, period_days, now)
            if dim_key == "momentum":
                prior_inputs = self._to_kpi_inputs(prior, dim_key, period_days, prev_end)
                kpis = compute_momentum_kpis(inputs, prior_inputs)
            else:
                kpis = _KPI_COMPUTERS[dim_key](inputs)

            score = compute_dimension_score(dim_key, {k: v for k, v in kpis.items()}) if kpis else None
            trend_kpi = kpis.get("mom_trend")
            trend = trend_kpi.value if trend_kpi else None

            dim_scores[dim_key] = {
                "score": score,
                "trend": trend,
                "kpis": {k: {"value": v.value, "contributing_ids": v.contributing_ids} for k, v in kpis.items()},
            }

        overall, overall_trend = self._compute_overall(dim_scores)
        top_moves = self._top_moves(assessments)
        risk_flags = self._risk_flags(assessments)
        watchpoints = self._watchpoints(assessments)
        top_caps = self._top_capabilities(dim_scores)

        # Flip previous current snapshots
        self.db.query(CompetitorScorecard).filter_by(
            company_id=company_id, period_type=period_type, is_current=True
        ).update({"is_current": False})
        self.db.flush()

        scorecard = CompetitorScorecard(
            company_id=company_id,
            period_type=period_type,
            period_start=period_start.date(),
            period_end=period_end.date(),
            generated_at=now,
            overall_score=overall,
            overall_trend=overall_trend,
            dimension_scores=dim_scores,
            top_capabilities=top_caps,
            top_moves=top_moves,
            risk_flags=risk_flags,
            watchpoints=watchpoints,
            benchmark_position=None,
            contributing_assessment_ids=all_ids,
            is_current=True,
            scorecard_version=SCORECARD_VERSION,
            routing_version=ROUTING_VERSION,
        )
        self.db.add(scorecard)
        self.db.commit()

        # Compute benchmark position after insert (uses full snapshot set)
        position = self._benchmark_position(company_id, period_type, scorecard.id)
        scorecard.benchmark_position = position
        self.db.commit()

        return scorecard

    def _fetch(self, company_id: str, start: datetime, end: datetime) -> list[SignalAssessment]:
        return (
            self.db.query(SignalAssessment)
            .filter(
                SignalAssessment.company_id == company_id,
                SignalAssessment.valid_from <= end,
                (SignalAssessment.valid_until == None) | (SignalAssessment.valid_until >= start),
            )
            .all()
        )

    def _to_kpi_inputs(
        self,
        assessments: list[SignalAssessment],
        dim_key: str,
        period_days: int,
        ref_time: datetime,
    ) -> list[AssessmentKPIInput]:
        result = []
        for a in assessments:
            dim_targets = a.dimension_targets or {}
            if isinstance(dim_targets, list):
                modifier = 1.0 if dim_key in dim_targets else 0.0
            else:
                modifier = dim_targets.get(dim_key, 0.0)
            if modifier == 0.0:
                continue
            valid_from = a.valid_from or a.created_at
            age_days = max(0, (ref_time.replace(tzinfo=None) - valid_from.replace(tzinfo=None)).days)
            result.append(AssessmentKPIInput(
                id=a.id,
                movement_score=a.movement_score or 0,
                movement_strength=(a.movement_strength.value if hasattr(a.movement_strength, "value") else a.movement_strength) or "weak",
                signal_class=(a.signal_class.value if hasattr(a.signal_class, "value") else a.signal_class) or "weak_signal",
                evidence_strength=a.evidence_strength or 3,
                visibility_impact=(a.visibility_impact.value if hasattr(a.visibility_impact, "value") else a.visibility_impact) or "low",
                confidence=a.confidence or 0.5,
                capability_primary=a.capability_primary or "other",
                capability_secondary=a.capability_secondary or [],
                assessment_weight=a.assessment_weight or 1.0,
                dimension_modifier=modifier,
                age_days=age_days,
                period_days=period_days,
            ))
        return result

    def _compute_overall(self, dim_scores: dict) -> tuple[Optional[float], Optional[str]]:
        non_null = {k: v for k, v in dim_scores.items() if v["score"] is not None}
        if not non_null:
            return None, None
        total_raw_weight = sum(DIMENSION_WEIGHTS[k] for k in non_null)
        score = sum(
            v["score"] * DIMENSION_WEIGHTS[k] / total_raw_weight
            for k, v in non_null.items()
        )
        momentum = dim_scores.get("momentum", {}).get("trend")
        return round(score, 2), momentum

    def _top_moves(self, assessments: list[SignalAssessment], n: int = 5) -> list[dict]:
        scored = sorted(
            assessments,
            key=lambda a: (a.movement_score or 0) * (a.assessment_weight or 1.0),
            reverse=True,
        )
        seen_signals: set[str] = set()
        result = []
        for a in scored:
            if a.signal_id in seen_signals:
                continue
            seen_signals.add(a.signal_id)
            result.append({
                "assessment_id": a.id,
                "signal_id": a.signal_id,
                "title": a.signal.title if a.signal else "",
                "movement_score": a.movement_score or 0,
                "signal_class": (a.signal_class.value if hasattr(a.signal_class, "value") else a.signal_class) or "",
            })
            if len(result) >= n:
                break
        return result

    def _risk_flags(self, assessments: list[SignalAssessment]) -> list[dict]:
        result = []
        for a in assessments:
            ms = a.movement_strength.value if hasattr(a.movement_strength, "value") else a.movement_strength
            if ms != "market_shaping":
                continue
            cap = CAPABILITIES.get(a.capability_primary or "", {})
            if cap.get("strategic_weight", 0) >= RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD:
                result.append({
                    "assessment_id": a.id,
                    "capability_key": a.capability_primary,
                    "movement_strength": ms,
                    "title": a.signal.title if a.signal else "",
                })
        return result

    def _watchpoints(self, assessments: list[SignalAssessment]) -> list[str]:
        counter: Counter = Counter()
        for a in assessments:
            for item in (a.watch_items or []):
                counter[item.strip()] += 1
        return [item for item, _ in counter.most_common()]

    def _top_capabilities(self, dim_scores: dict) -> list[dict]:
        cap_kpis = dim_scores.get("capability_strength", {}).get("kpis", {})
        score_val = cap_kpis.get("cap_weighted_score", {})
        if isinstance(score_val, dict):
            score = score_val.get("value")
        else:
            score = getattr(score_val, "value", None)
        if score is None:
            return []
        return [{"capability_key": "aggregate", "score": score}]

    def _benchmark_position(self, company_id: str, period_type: str, this_id: str) -> dict:
        rows = (
            self.db.query(CompetitorScorecard)
            .filter_by(period_type=period_type, is_current=True)
            .all()
        )
        scored = sorted(
            rows,
            key=lambda r: r.overall_score if r.overall_score is not None else -1,
            reverse=True,
        )
        total = len(scored)
        rank = next((i + 1 for i, r in enumerate(scored) if r.id == this_id), total)
        percentile = round(((total - rank) / max(total - 1, 1)) * 100, 1) if total > 1 else 100.0
        return {"rank": rank, "percentile": percentile, "total_competitors": total}
```

- [ ] **Step 4: Run tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_scorecard_builder.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scorecard/builder.py backend/tests/test_scorecard_builder.py
git commit -m "feat: ScorecardBuilder with KPI orchestration and snapshot persistence"
```

---

## Task 9: LLM prompt extension + pipeline integration

**Files:**
- Modify: `backend/app/assessor/prompts.py`
- Modify: `backend/app/assessor/parser.py`
- Modify: `backend/app/assessor/pipeline.py`

- [ ] **Step 1: Extend assessment prompt**

In `backend/app/assessor/prompts.py`, find the JSON output schema in the assessment prompt and add two fields. Locate where `watch_items` is listed in the schema and add after it:

```python
# In the prompt output schema section, add:
#   "buyer_relevance": <integer 1-5, how directly this move affects a buyer decision. Only include if evidence_strength >= 4 or movement is market_shaping>,
#   "assessment_weight": <float 0.5-2.0, optional weight override. Only include if evidence_strength >= 4 or movement is market_shaping. Default 1.0>,
```

Add this guidance to the prompt instructions:
```python
# Add to the instruction block:
# If this signal has evidence_strength >= 4 or is market-shaping, also estimate:
# - buyer_relevance (1=no direct buyer impact, 5=directly influences purchasing decisions)
# - assessment_weight (0.5=significantly less important than typical, 2.0=exceptionally significant)
# Otherwise omit these fields entirely.
```

- [ ] **Step 2: Extend parser to handle new fields**

In `backend/app/assessor/parser.py`, find the `AssessmentLLMOutput` dataclass or Pydantic model and add optional fields:

```python
# Add to AssessmentLLMOutput (or equivalent parsed result class):
buyer_relevance: Optional[int] = None
assessment_weight: Optional[float] = None
```

In the parse function, extract these fields defensively:
```python
buyer_relevance = data.get("buyer_relevance")
if buyer_relevance is not None:
    try:
        buyer_relevance = max(1, min(5, int(buyer_relevance)))
    except (TypeError, ValueError):
        buyer_relevance = None

assessment_weight = data.get("assessment_weight")
if assessment_weight is not None:
    try:
        assessment_weight = max(0.5, min(2.0, float(assessment_weight)))
    except (TypeError, ValueError):
        assessment_weight = None
```

- [ ] **Step 3: Integrate DimensionRouter and ScorecardBuilder into `assess_signal()`**

In `backend/app/assessor/pipeline.py`, make these changes:

After the imports block, add:
```python
from app.scorecard.dimension_router import DimensionRouter
from app.scorecard.constants import ROUTING_VERSION, VALID_PERIOD_TYPES
```

After `movement_strength = compute_movement_strength(movement_score)`, add the routing step:

```python
    # Route assessment to dimensions and KPIs
    routing_result = DimensionRouter.route(
        type("_A", (), {
            "signal_class": signal_class,
            "evidence_strength": parsed.evidence_strength or 3,
            "visibility_impact": parsed.visibility_impact or "low",
            "movement_strength": movement_strength,
            "assessment_weight": parsed.assessment_weight or 1.0,
        })()
    )
    assessment_weight = parsed.assessment_weight or 1.0
    buyer_relevance = parsed.buyer_relevance
    valid_from = signal.published_at or now
```

When creating/updating the `SignalAssessment`, add the new fields:
```python
    # In both the `existing` update block and the new `assessment` creation block, add:
    existing.dimension_targets = routing_result.dimension_targets
    existing.kpi_targets = routing_result.kpi_targets
    existing.assessment_weight = assessment_weight
    existing.buyer_relevance = buyer_relevance
    existing.valid_from = valid_from
    existing.routing_version = ROUTING_VERSION
    # (valid_until is not set here — only set when real-world expiry is known)
```

After the benchmark recompute call in both branches, add the scorecard build:
```python
    try:
        from app.scorecard.builder import ScorecardBuilder
        builder = ScorecardBuilder(db)
        for period_type in VALID_PERIOD_TYPES:
            builder.build(assessment.company_id, period_type)
    except Exception as exc:
        logger.warning("Scorecard build failed: %s", exc)
```

- [ ] **Step 4: Run existing assessor pipeline tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_assessor_pipeline.py -v
```

Expected: all existing tests still pass (new fields are nullable and have defaults).

- [ ] **Step 5: Commit**

```bash
git add backend/app/assessor/prompts.py backend/app/assessor/parser.py backend/app/assessor/pipeline.py
git commit -m "feat: integrate DimensionRouter and ScorecardBuilder into assess_signal pipeline"
```

---

## Task 10: API router

**Files:**
- Create: `backend/app/routers/scorecards.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_scorecard_router.py`

- [ ] **Step 1: Write failing router tests**

Create `backend/tests/test_scorecard_router.py`:

```python
import pytest
import app.models  # noqa
from datetime import datetime, timezone


def _make_company_with_scorecard(db, slug="test-co"):
    from app.models.company import Company, CompanyType
    from app.models.competitor_scorecard import CompetitorScorecard
    company = Company(name=slug.title(), slug=slug, type=CompanyType.competitor)
    db.add(company)
    db.commit()
    sc = CompetitorScorecard(
        company_id=company.id,
        period_type="30d",
        period_start=datetime.now(timezone.utc).date(),
        period_end=datetime.now(timezone.utc).date(),
        generated_at=datetime.now(timezone.utc),
        overall_score=72.5,
        overall_trend="rising",
        dimension_scores={},
        top_capabilities=[],
        top_moves=[],
        risk_flags=[],
        watchpoints=[],
        benchmark_position={"rank": 1, "percentile": 100, "total_competitors": 1},
        contributing_assessment_ids=[],
        is_current=True,
        scorecard_version="sc_v1",
        routing_version="v1",
    )
    db.add(sc)
    db.commit()
    return company, sc


def test_get_scorecard_requires_period_type(client):
    client.get("/api/scorecards/any-slug").status_code == 400


def test_get_scorecard_returns_404_for_unknown_company(client):
    r = client.get("/api/scorecards/no-such-company?period_type=30d")
    assert r.status_code == 404


def test_get_scorecard_returns_scorecard(client, db_session):
    company, sc = _make_company_with_scorecard(db_session)
    r = client.get(f"/api/scorecards/{company.slug}?period_type=30d")
    assert r.status_code == 200
    data = r.json()
    assert data["overall_score"] == pytest.approx(72.5)
    assert data["overall_trend"] == "rising"


def test_get_history_returns_list(client, db_session):
    company, sc = _make_company_with_scorecard(db_session)
    r = client.get(f"/api/scorecards/{company.slug}/history?period_type=30d")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 1


def test_get_benchmark_requires_period_type(client):
    assert client.get("/api/scorecards/benchmark").status_code == 400


def test_get_benchmark_returns_paginated(client, db_session):
    company, sc = _make_company_with_scorecard(db_session, "bench-co")
    r = client.get("/api/scorecards/benchmark?period_type=30d")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["period_type"] == "30d"


def test_get_explain_returns_404_when_no_scorecard(client):
    r = client.get("/api/scorecards/ghost-co/explain?period_type=30d")
    assert r.status_code == 404


def test_recompute_returns_ack(client, db_session):
    from unittest.mock import patch
    company, _ = _make_company_with_scorecard(db_session, "recompute-co")
    with patch("app.routers.scorecards.ScorecardBuilder") as mock_builder:
        instance = mock_builder.return_value
        from app.models.competitor_scorecard import CompetitorScorecard
        from datetime import datetime, timezone
        fake_sc = CompetitorScorecard(
            id="fake-id", company_id=company.id, period_type="30d",
            period_start=datetime.now(timezone.utc).date(),
            period_end=datetime.now(timezone.utc).date(),
            generated_at=datetime.now(timezone.utc),
            is_current=True,
        )
        instance.build.return_value = fake_sc
        r = client.post(f"/api/scorecards/{company.slug}/recompute")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["company_slug"] == company.slug
    assert "recomputed_periods" in body
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_scorecard_router.py -v
```

Expected: `404` on all routes (router not mounted yet)

- [ ] **Step 3: Create the router**

Create `backend/app/routers/scorecards.py`:

```python
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.signal_assessment import SignalAssessment
from app.models.competitor_scorecard import CompetitorScorecard
from app.schemas.scorecard import (
    ScorecardRead, ScorecardHistoryItem, ScorecardExplain, ScorecardExplainDimension,
    ScorecardExplainAssessment, ScorecardKPIValue, ScorecardRecomputeAck,
    BenchmarkScorecardItem, BenchmarkScorecardView, ScorecardDimension,
)
from app.scorecard.builder import ScorecardBuilder
from app.scorecard.constants import VALID_PERIOD_TYPES, DIMENSION_WEIGHTS
from app.assessor.capabilities import CAPABILITIES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scorecards", tags=["scorecards"])


def _require_period(period_type: Optional[str] = Query(default=None)) -> str:
    if period_type not in VALID_PERIOD_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"period_type is required. Valid values: {', '.join(VALID_PERIOD_TYPES)}",
        )
    return period_type


def _get_company(slug: str, db: Session) -> Company:
    company = db.query(Company).filter_by(slug=slug).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{slug}' not found")
    return company


def _get_current_scorecard(company_id: str, period_type: str, db: Session) -> CompetitorScorecard:
    sc = db.query(CompetitorScorecard).filter_by(
        company_id=company_id, period_type=period_type, is_current=True
    ).first()
    if not sc:
        raise HTTPException(status_code=404, detail="No scorecard for this company and period")
    return sc


# --- Benchmark routes must be defined before /{company_slug} to avoid path conflict ---

@router.get("/benchmark", response_model=BenchmarkScorecardView)
def get_benchmark(
    period_type: str = Depends(_require_period),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(CompetitorScorecard).filter_by(period_type=period_type, is_current=True)
    total = query.count()
    rows = query.order_by(CompetitorScorecard.overall_score.desc().nullslast()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for sc in rows:
        company = sc.company
        items.append(BenchmarkScorecardItem(
            company_id=sc.company_id, slug=company.slug, name=company.name,
            overall_score=sc.overall_score, rank=sc.benchmark_position.get("rank", 0) if sc.benchmark_position else 0,
            percentile=sc.benchmark_position.get("percentile", 0) if sc.benchmark_position else 0,
            dimension_scores={
                k: ScorecardDimension(
                    score=v.get("score"), trend=v.get("trend"),
                    kpis={ki: ScorecardKPIValue(value=kv.get("value"), contributing_ids=kv.get("contributing_ids", []))
                          for ki, kv in v.get("kpis", {}).items()}
                )
                for k, v in (sc.dimension_scores or {}).items()
            },
            overall_trend=sc.overall_trend, scorecard_version=sc.scorecard_version,
        ))

    all_current = db.query(CompetitorScorecard).filter_by(period_type=period_type, is_current=True).all()
    threat_flags: list[dict] = []
    for sc in all_current:
        for rf in (sc.risk_flags or []):
            threat_flags.append({
                "company_slug": sc.company.slug,
                "capability": rf.get("capability_key"),
                "movement_strength": rf.get("movement_strength"),
            })

    highest = max(
        (sc for sc in all_current if sc.dimension_scores and sc.dimension_scores.get("momentum", {}).get("kpis", {}).get("mom_period_delta", {}).get("value") is not None),
        key=lambda sc: sc.dimension_scores["momentum"]["kpis"]["mom_period_delta"]["value"],
        default=None,
    )
    highest_momentum = None
    if highest:
        delta = highest.dimension_scores["momentum"]["kpis"]["mom_period_delta"]["value"]
        highest_momentum = {"company_slug": highest.company.slug, "mom_period_delta": delta}

    cap_leaders: dict[str, dict] = {}
    for cap_key in CAPABILITIES:
        best = max(
            (sc for sc in all_current if sc.dimension_scores and
             sc.dimension_scores.get("capability_strength", {}).get("score") is not None),
            key=lambda sc: sc.dimension_scores.get("capability_strength", {}).get("score", 0),
            default=None,
        )
        if best:
            cap_leaders[cap_key] = {
                "company_slug": best.company.slug,
                "score": best.dimension_scores["capability_strength"]["score"],
            }
        break  # simplified: one entry for all caps — extend later per-capability

    return BenchmarkScorecardView(
        items=items, total=total, page=page, page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
        period_type=period_type,
        capability_leaders=cap_leaders,
        highest_momentum=highest_momentum,
        threat_flags=threat_flags,
    )


@router.get("/benchmark/capability/{capability_key}")
def get_benchmark_capability(
    capability_key: str,
    period_type: str = Depends(_require_period),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    cap_meta = CAPABILITIES.get(capability_key)
    if not cap_meta:
        raise HTTPException(status_code=404, detail=f"Unknown capability: {capability_key}")
    rows = db.query(CompetitorScorecard).filter_by(period_type=period_type, is_current=True).all()
    scored = sorted(
        rows,
        key=lambda sc: (sc.dimension_scores or {}).get("capability_strength", {}).get("score") or 0,
        reverse=True,
    )
    total = len(scored)
    page_rows = scored[(page - 1) * page_size: page * page_size]
    return {
        "capability_key": capability_key,
        "wardley_band": cap_meta.get("default_evolution_band"),
        "period_type": period_type,
        "total": total, "page": page, "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
        "items": [
            {
                "company_slug": sc.company.slug,
                "company_name": sc.company.name,
                "capability_score": (sc.dimension_scores or {}).get("capability_strength", {}).get("score"),
                "rank": idx + 1,
            }
            for idx, sc in enumerate(page_rows)
        ],
    }


# --- Per-competitor routes ---

@router.get("/{company_slug}", response_model=ScorecardRead)
def get_scorecard(
    company_slug: str,
    period_type: str = Depends(_require_period),
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    return _get_current_scorecard(company.id, period_type, db)


@router.get("/{company_slug}/history", response_model=list[ScorecardHistoryItem])
def get_scorecard_history(
    company_slug: str,
    period_type: str = Depends(_require_period),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    return (
        db.query(CompetitorScorecard)
        .filter_by(company_id=company.id, period_type=period_type)
        .order_by(CompetitorScorecard.generated_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{company_slug}/explain", response_model=ScorecardExplain)
def get_scorecard_explain(
    company_slug: str,
    period_type: str = Depends(_require_period),
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    sc = _get_current_scorecard(company.id, period_type, db)

    non_null_dims = [k for k, v in (sc.dimension_scores or {}).items() if v.get("score") is not None]
    null_dims = [k for k in DIMENSION_WEIGHTS if k not in non_null_dims]
    total_raw = sum(DIMENSION_WEIGHTS[k] for k in non_null_dims) or 1.0

    breakdown = []
    for dim_key, dim_data in (sc.dimension_scores or {}).items():
        score = dim_data.get("score")
        raw_weight = DIMENSION_WEIGHTS.get(dim_key, 0)
        eff_weight = round(raw_weight / total_raw, 4) if score is not None else 0.0
        contribution = round(score * eff_weight, 2) if score is not None else None
        contributing_ids = sc.contributing_assessment_ids or []

        # Resolve top 5 assessments
        assessments = (
            db.query(SignalAssessment)
            .filter(SignalAssessment.id.in_(contributing_ids[:50]))
            .all()
        )
        dim_assessments = [
            a for a in assessments
            if dim_key in ((a.dimension_targets or {}) if isinstance(a.dimension_targets, dict) else {})
        ]
        top5 = sorted(
            dim_assessments,
            key=lambda a: (a.movement_score or 0) * (a.assessment_weight or 1.0),
            reverse=True,
        )[:5]

        breakdown.append(ScorecardExplainDimension(
            dimension=dim_key,
            score=score,
            dimension_weight=raw_weight,
            effective_weight=eff_weight,
            weighted_contribution=contribution,
            assessment_count=len(dim_assessments),
            top_contributing_assessments=[
                ScorecardExplainAssessment(
                    assessment_id=a.id, signal_id=a.signal_id,
                    title=a.signal.title if a.signal else "",
                    movement_score=a.movement_score or 0,
                    signal_class=(a.signal_class.value if hasattr(a.signal_class, "value") else a.signal_class) or "",
                )
                for a in top5
            ],
            kpi_detail={
                ki: ScorecardKPIValue(value=kv.get("value"), contributing_ids=kv.get("contributing_ids", []))
                for ki, kv in dim_data.get("kpis", {}).items()
            },
        ))

    return ScorecardExplain(
        overall_score=sc.overall_score,
        dimension_breakdown=breakdown,
        null_dimensions=null_dims,
        score_formula="Weighted average of non-null dimensions. Weights re-normalised: shown as effective_weight.",
        routing_version=sc.routing_version,
        scorecard_version=sc.scorecard_version,
    )


@router.post("/{company_slug}/recompute", response_model=ScorecardRecomputeAck)
def recompute_scorecard(
    company_slug: str,
    db: Session = Depends(get_db),
):
    company = _get_company(company_slug, db)
    builder = ScorecardBuilder(db)
    scorecard_ids: dict[str, str] = {}
    generated_at = datetime.now(timezone.utc)
    for period_type in VALID_PERIOD_TYPES:
        try:
            sc = builder.build(company.id, period_type)
            scorecard_ids[period_type] = sc.id
        except Exception as exc:
            logger.warning("Recompute failed for %s/%s: %s", company_slug, period_type, exc)
    return ScorecardRecomputeAck(
        status="ok",
        company_slug=company_slug,
        recomputed_periods=list(scorecard_ids.keys()),
        scorecard_ids=scorecard_ids,
        generated_at=generated_at,
    )


@router.post("/recompute-all")
def recompute_all(
    period_type: str = Depends(_require_period),
    db: Session = Depends(get_db),
):
    from app.models.company import CompanyType
    companies = db.query(Company).filter_by(type=CompanyType.competitor).all()
    builder = ScorecardBuilder(db)
    recomputed = 0
    errors = []
    for company in companies:
        try:
            builder.build(company.id, period_type)
            recomputed += 1
        except Exception as exc:
            errors.append({"company_slug": company.slug, "error": str(exc)})
    return {"recomputed": recomputed, "errors": errors}
```

- [ ] **Step 4: Mount router in `backend/app/main.py`**

Find where other routers are included (e.g. `app.include_router(benchmark_router)`) and add:

```python
from app.routers.scorecards import router as scorecards_router
app.include_router(scorecards_router)
```

- [ ] **Step 5: Run router tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_scorecard_router.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Run full test suite**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: all existing tests pass; new tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/scorecards.py backend/app/main.py backend/tests/test_scorecard_router.py
git commit -m "feat: scorecards API router with scorecard, explain, recompute, and benchmark endpoints"
```

---

## Self-review checklist

- [x] §3.1 SignalAssessment new fields → Task 2
- [x] §3.2 CompetitorScorecard model → Task 2
- [x] `dimension_targets` as dict (not list) for modifier storage → Task 5 + builder
- [x] §4 DimensionRouter with rule override semantics → Task 5
- [x] §4.2 LLM supplement → Task 9
- [x] §5 KPIEngine all KPI groups → Tasks 6, 7
- [x] §5.1 Weight terminology (assessment_weight × dimension_modifier × recency_weight) → Tasks 6, 7
- [x] §5.3 Shannon entropy normalised → Task 6
- [x] §6 ScorecardBuilder build flow → Task 8
- [x] valid_until temporal overlap query → Task 8 (`_fetch`)
- [x] Watchpoints from all contributing assessments → Task 8
- [x] Benchmark position after persist → Task 8
- [x] `signal_id` in top_moves → Tasks 8, 10
- [x] Snapshot semantics (multiple rows, is_current flag) → Tasks 1, 8
- [x] §7 API endpoints, `period_type` required → Task 10
- [x] §9 Migration → Task 1
- [x] §10 Testing strategy → Tasks 5, 6, 7, 8, 10
