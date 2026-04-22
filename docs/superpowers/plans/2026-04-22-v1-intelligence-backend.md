# V1 Intelligence Layer — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SignalAssessment + CompetitorSummary models, assessor module, and five new intelligence API endpoints to the existing FastAPI backend.

**Architecture:** New `backend/app/assessor/` module (analogous to `analyser/`) handles per-signal assessment via rules + LLM. A post-step hook in `analyser/pipeline.py` triggers assessment automatically when `relevance_score >= ASSESSMENT_THRESHOLD`. A new `routers/intelligence.py` exposes Overview, Competitor Workspace, Signals Feed, and trigger endpoints. No existing endpoints are modified.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync), Alembic, PostgreSQL, Pydantic v2, Anthropic SDK

---

## File Map

**Create:**
- `backend/app/models/signal_assessment.py` — SignalAssessment ORM model
- `backend/app/models/competitor_summary.py` — CompetitorSummary ORM model
- `backend/app/schemas/signal_assessment.py` — Pydantic read schema
- `backend/app/schemas/competitor_summary.py` — Pydantic read schema
- `backend/app/assessor/__init__.py` — empty
- `backend/app/assessor/capabilities.py` — 16 WFM capability definitions
- `backend/app/assessor/rules.py` — movement_score formula + signal_class mapping
- `backend/app/assessor/prompts.py` — LLM prompt templates
- `backend/app/assessor/parser.py` — Pydantic v2 schema + retry parsing
- `backend/app/assessor/pipeline.py` — `assess_signal(signal, db)`
- `backend/app/assessor/summarizer.py` — `generate_competitor_summary(company, period_type, db)`
- `backend/app/routers/intelligence.py` — 5 API endpoints
- `backend/scripts/backfill_assessments.py` — one-time backfill script
- `backend/alembic/versions/a1b2c3d4e5f6_add_intelligence_layer.py` — migration
- `backend/tests/test_assessor_rules.py` — unit tests for scoring
- `backend/tests/test_assessor_pipeline.py` — integration tests
- `backend/tests/test_intelligence_router.py` — API endpoint tests

**Modify:**
- `backend/app/models/__init__.py` — import new models
- `backend/app/config.py` — add `assessment_threshold`
- `backend/app/analyser/pipeline.py` — add post-step hook
- `backend/app/routers/crawl.py` — add post-crawl summary trigger
- `backend/app/main.py` — register intelligence router

---

## Task 1: ORM Models

**Files:**
- Create: `backend/app/models/signal_assessment.py`
- Create: `backend/app/models/competitor_summary.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py — add at the bottom of the existing file
def test_signal_assessment_model_exists():
    from app.models.signal_assessment import SignalAssessment
    assert SignalAssessment.__tablename__ == "signal_assessments"

def test_competitor_summary_model_exists():
    from app.models.competitor_summary import CompetitorSummary
    assert CompetitorSummary.__tablename__ == "competitor_summaries"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_models.py::test_signal_assessment_model_exists tests/test_models.py::test_competitor_summary_model_exists -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create signal_assessment.py**

```python
# backend/app/models/signal_assessment.py
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, SmallInteger, DateTime, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class SignalClass(str, enum.Enum):
    product_capability_move = "product_capability_move"
    positioning_move = "positioning_move"
    ecosystem_move = "ecosystem_move"
    thought_leadership_signal = "thought_leadership_signal"
    hiring_signal = "hiring_signal"
    weak_signal = "weak_signal"
    market_expansion_move = "market_expansion_move"


class VisibilityImpact(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class MovementStrength(str, enum.Enum):
    weak = "weak"
    relevant = "relevant"
    strong = "strong"
    market_shaping = "market_shaping"


class SignalAssessment(Base):
    __tablename__ = "signal_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id = Column(String(36), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    capability_primary = Column(String(100), nullable=True)
    capability_secondary = Column(JSON, nullable=True)
    signal_class = Column(SAEnum(SignalClass), nullable=True)
    evidence_strength = Column(SmallInteger, nullable=True)
    visibility_impact = Column(SAEnum(VisibilityImpact), nullable=True)
    strategic_weight = Column(SmallInteger, nullable=True)
    movement_score = Column(SmallInteger, nullable=True)
    movement_strength = Column(SAEnum(MovementStrength), nullable=True)
    confidence = Column(Float, nullable=True)
    strategic_intent_guess = Column(Text, nullable=True)
    gameplay_tags = Column(JSON, nullable=True)
    assessment_summary = Column(Text, nullable=True)
    implication_for_us = Column(Text, nullable=True)
    watch_items = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    signal = relationship("Signal", backref="assessment", uselist=False)
    company = relationship("Company")
```

- [ ] **Step 4: Create competitor_summary.py**

```python
# backend/app/models/competitor_summary.py
import uuid
import enum
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Text, Float, Integer, Date, DateTime, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class PeriodType(str, enum.Enum):
    seven_days = "7d"
    thirty_days = "30d"
    ninety_days = "90d"
    quarter = "quarter"


class CompetitorSummary(Base):
    __tablename__ = "competitor_summaries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    period_type = Column(SAEnum(PeriodType), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    strategic_posture = Column(String(200), nullable=True)
    positioning_summary = Column(Text, nullable=True)
    top_capabilities = Column(JSON, nullable=True)
    capability_assessment = Column(JSON, nullable=True)
    top_risks = Column(JSON, nullable=True)
    top_opportunities = Column(JSON, nullable=True)
    watchpoints = Column(JSON, nullable=True)
    avg_movement_score = Column(Float, nullable=True)
    signal_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company")
```

- [ ] **Step 5: Update models/__init__.py**

```python
# backend/app/models/__init__.py — add to imports
from app.models.signal_assessment import SignalAssessment, SignalClass, VisibilityImpact, MovementStrength
from app.models.competitor_summary import CompetitorSummary, PeriodType

# add to __all__
"SignalAssessment", "SignalClass", "VisibilityImpact", "MovementStrength",
"CompetitorSummary", "PeriodType",
```

Full `__init__.py` after edit:
```python
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.digest import WeeklyDigest
from app.models.context import InternalCompanyContext
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus
from app.models.search_query import SearchQuery
from app.models.search_run import SearchRun, SearchRunStatus
from app.models.search_result import SearchResult, SearchResultStatus
from app.models.source_candidate import SourceCandidate, SourceCandidateStatus
from app.models.crawl_run import (
    CrawlRun,
    CrawlRunStatus,
    CrawlRunSource,
    CrawlRunSourceStatus,
    CrawlRunStep,
)
from app.models.crawl_briefing import CrawlBriefing
from app.models.signal_assessment import SignalAssessment, SignalClass, VisibilityImpact, MovementStrength
from app.models.competitor_summary import CompetitorSummary, PeriodType

__all__ = [
    "Company", "CompanyType",
    "Source", "SourceType",
    "Document",
    "Signal", "SignalType",
    "WeeklyDigest",
    "InternalCompanyContext",
    "DiscoveredPage", "DiscoveredPageStatus",
    "SearchQuery",
    "SearchRun", "SearchRunStatus",
    "SearchResult", "SearchResultStatus",
    "SourceCandidate", "SourceCandidateStatus",
    "CrawlRun", "CrawlRunStatus", "CrawlRunSource", "CrawlRunSourceStatus", "CrawlRunStep",
    "CrawlBriefing",
    "SignalAssessment", "SignalClass", "VisibilityImpact", "MovementStrength",
    "CompetitorSummary", "PeriodType",
]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_models.py::test_signal_assessment_model_exists tests/test_models.py::test_competitor_summary_model_exists -v
```
Expected: 2 PASSED

- [ ] **Step 7: Commit**

```bash
rtk git add backend/app/models/signal_assessment.py backend/app/models/competitor_summary.py backend/app/models/__init__.py
rtk git commit -m "feat: add SignalAssessment and CompetitorSummary ORM models"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/a1b2c3d4e5f6_add_intelligence_layer.py`

- [ ] **Step 1: Generate migration (auto)**

```bash
cd backend && alembic revision --autogenerate -m "add_intelligence_layer"
```

This generates a file in `alembic/versions/`. Open it and verify it contains `create_table("signal_assessments", ...)` and `create_table("competitor_summaries", ...)`. If the auto-generated migration looks correct, proceed. If the project is not connected to a live DB, create the migration manually:

- [ ] **Step 2: Verify or create migration manually**

If auto-generate is unavailable, create `backend/alembic/versions/a1b2c3d4e5f6_add_intelligence_layer.py`:

```python
"""add_intelligence_layer

Revision ID: a1b2c3d4e5f6
Revises: c85a4338b763
Create Date: 2026-04-22 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c85a4338b763"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signal_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signal_id", sa.String(36), sa.ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("capability_primary", sa.String(100), nullable=True),
        sa.Column("capability_secondary", sa.JSON, nullable=True),
        sa.Column("signal_class", sa.String(50), nullable=True),
        sa.Column("evidence_strength", sa.SmallInteger, nullable=True),
        sa.Column("visibility_impact", sa.String(20), nullable=True),
        sa.Column("strategic_weight", sa.SmallInteger, nullable=True),
        sa.Column("movement_score", sa.SmallInteger, nullable=True),
        sa.Column("movement_strength", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("strategic_intent_guess", sa.Text, nullable=True),
        sa.Column("gameplay_tags", sa.JSON, nullable=True),
        sa.Column("assessment_summary", sa.Text, nullable=True),
        sa.Column("implication_for_us", sa.Text, nullable=True),
        sa.Column("watch_items", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "competitor_summaries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("strategic_posture", sa.String(200), nullable=True),
        sa.Column("positioning_summary", sa.Text, nullable=True),
        sa.Column("top_capabilities", sa.JSON, nullable=True),
        sa.Column("capability_assessment", sa.JSON, nullable=True),
        sa.Column("top_risks", sa.JSON, nullable=True),
        sa.Column("top_opportunities", sa.JSON, nullable=True),
        sa.Column("watchpoints", sa.JSON, nullable=True),
        sa.Column("avg_movement_score", sa.Float, nullable=True),
        sa.Column("signal_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("signal_assessments")
    op.drop_table("competitor_summaries")
```

- [ ] **Step 3: Run migration**

```bash
cd backend && docker compose -f ../docker-compose.dev.yml exec backend alembic upgrade head
```

Or if running locally: `cd backend && alembic upgrade head`

- [ ] **Step 4: Commit**

```bash
rtk git add backend/alembic/versions/
rtk git commit -m "feat: migration for signal_assessments and competitor_summaries tables"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/signal_assessment.py`
- Create: `backend/app/schemas/competitor_summary.py`

- [ ] **Step 1: Create signal_assessment schema**

```python
# backend/app/schemas/signal_assessment.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class SignalAssessmentRead(BaseModel):
    id: str
    signal_id: str
    company_id: str
    capability_primary: Optional[str] = None
    capability_secondary: List[str] = []
    signal_class: Optional[str] = None
    evidence_strength: Optional[int] = None
    visibility_impact: Optional[str] = None
    strategic_weight: Optional[int] = None
    movement_score: Optional[int] = None
    movement_strength: Optional[str] = None
    confidence: Optional[float] = None
    strategic_intent_guess: Optional[str] = None
    gameplay_tags: List[str] = []
    assessment_summary: Optional[str] = None
    implication_for_us: Optional[str] = None
    watch_items: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create competitor_summary schema**

```python
# backend/app/schemas/competitor_summary.py
from typing import Optional, List, Any
from datetime import datetime, date
from pydantic import BaseModel


class CompetitorSummaryRead(BaseModel):
    id: str
    company_id: str
    period_type: str
    period_start: date
    period_end: date
    strategic_posture: Optional[str] = None
    positioning_summary: Optional[str] = None
    top_capabilities: List[str] = []
    capability_assessment: List[Any] = []
    top_risks: List[str] = []
    top_opportunities: List[str] = []
    watchpoints: List[str] = []
    avg_movement_score: Optional[float] = None
    signal_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Verify schemas import cleanly**

```bash
cd backend && python -c "from app.schemas.signal_assessment import SignalAssessmentRead; from app.schemas.competitor_summary import CompetitorSummaryRead; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
rtk git add backend/app/schemas/signal_assessment.py backend/app/schemas/competitor_summary.py
rtk git commit -m "feat: add Pydantic schemas for SignalAssessment and CompetitorSummary"
```

---

## Task 4: Capabilities Dict + Config

**Files:**
- Create: `backend/app/assessor/__init__.py`
- Create: `backend/app/assessor/capabilities.py`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Create assessor package**

```python
# backend/app/assessor/__init__.py
# (empty)
```

- [ ] **Step 2: Create capabilities.py**

```python
# backend/app/assessor/capabilities.py
from typing import TypedDict


class CapabilityMeta(TypedDict):
    key: str
    label: str
    visibility_to_user: bool
    strategic_weight: int  # 1-10
    default_evolution_band: str
    description: str


CAPABILITIES: dict[str, CapabilityMeta] = {
    "demand_forecasting": {
        "key": "demand_forecasting",
        "label": "Demand Forecasting",
        "visibility_to_user": True,
        "strategic_weight": 9,
        "default_evolution_band": "product",
        "description": "Predicting staffing demand based on historical data and external signals",
    },
    "shift_scheduling": {
        "key": "shift_scheduling",
        "label": "Shift Scheduling",
        "visibility_to_user": True,
        "strategic_weight": 10,
        "default_evolution_band": "product",
        "description": "Creating and optimizing shift plans for frontline workers",
    },
    "intraday_management": {
        "key": "intraday_management",
        "label": "Intraday Management",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Real-time adjustment of staffing to match live demand",
    },
    "time_attendance": {
        "key": "time_attendance",
        "label": "Time & Attendance",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Tracking worked hours, absences and compliance",
    },
    "compliance_rules": {
        "key": "compliance_rules",
        "label": "Compliance & Labor Rules",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Enforcing labor law, union rules and company policies in scheduling",
    },
    "employee_self_service": {
        "key": "employee_self_service",
        "label": "Employee Self-Service",
        "visibility_to_user": True,
        "strategic_weight": 6,
        "default_evolution_band": "product",
        "description": "Employee-facing tools for availability, shift swaps and requests",
    },
    "manager_experience": {
        "key": "manager_experience",
        "label": "Manager Experience",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Tooling and UX specifically designed for frontline managers",
    },
    "mobile_experience": {
        "key": "mobile_experience",
        "label": "Mobile Experience",
        "visibility_to_user": True,
        "strategic_weight": 6,
        "default_evolution_band": "product",
        "description": "Mobile apps and responsiveness for deskless worker access",
    },
    "analytics_insights": {
        "key": "analytics_insights",
        "label": "Analytics & Insights",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Reporting dashboards and workforce analytics capabilities",
    },
    "ai_copilot": {
        "key": "ai_copilot",
        "label": "AI Copilot",
        "visibility_to_user": True,
        "strategic_weight": 9,
        "default_evolution_band": "genesis",
        "description": "AI-assisted scheduling, recommendations and conversational interfaces",
    },
    "workflow_automation": {
        "key": "workflow_automation",
        "label": "Workflow Automation",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Automating approval flows, notifications and operational processes",
    },
    "integration_hub": {
        "key": "integration_hub",
        "label": "Integration Hub",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Pre-built connectors to HCM, ERP, and payroll systems",
    },
    "platform_ecosystem": {
        "key": "platform_ecosystem",
        "label": "Platform & Ecosystem",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Partner ecosystem, marketplace, and platform extensibility",
    },
    "vertical_solutions": {
        "key": "vertical_solutions",
        "label": "Vertical Solutions",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Industry-specific WFM modules for retail, healthcare, logistics, etc.",
    },
    "data_foundation": {
        "key": "data_foundation",
        "label": "Data Foundation",
        "visibility_to_user": False,
        "strategic_weight": 6,
        "default_evolution_band": "product",
        "description": "Underlying data model, multi-tenant architecture and data quality",
    },
    "optimization_engine": {
        "key": "optimization_engine",
        "label": "Optimization Engine",
        "visibility_to_user": True,
        "strategic_weight": 9,
        "default_evolution_band": "product",
        "description": "Mathematical optimization for schedule quality, cost and coverage",
    },
}

CAPABILITY_KEYS = list(CAPABILITIES.keys())
```

- [ ] **Step 3: Add ASSESSMENT_THRESHOLD to config**

Edit `backend/app/config.py` — add one field to the `Settings` class:

```python
# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql://wfm:wfm@localhost:5432/wfmintel"
    auth_username: str = "admin"
    auth_password: str = "changeme"
    llm_provider: str = "claude"
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    discovery_depth: int = 1
    js_rendering_enabled: bool = True
    tavily_api_key: str = ""
    search_relevance_threshold: float = 0.5
    search_queries_per_company: int = 8
    assessment_threshold: float = 0.4


settings = Settings()
```

- [ ] **Step 4: Verify**

```bash
cd backend && python -c "from app.assessor.capabilities import CAPABILITIES, CAPABILITY_KEYS; from app.config import settings; assert len(CAPABILITIES) == 16; assert settings.assessment_threshold == 0.4; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/assessor/ backend/app/config.py
rtk git commit -m "feat: add assessor package, capabilities dict, ASSESSMENT_THRESHOLD config"
```

---

## Task 5: Scoring Rules

**Files:**
- Create: `backend/app/assessor/rules.py`
- Create: `backend/tests/test_assessor_rules.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_assessor_rules.py
from app.assessor.rules import compute_movement_score, compute_movement_strength, map_signal_type_to_class
from app.models.signal import SignalType


def test_compute_movement_score_high():
    score = compute_movement_score(
        relevance_score=1.0,
        confidence_score=1.0,
        evidence_strength=5,
        visibility_impact="high",
        signal_class="product_capability_move",
    )
    # 35 + 20 + 30 + 15 - 0 = 100
    assert score == 100


def test_compute_movement_score_thought_leadership_penalty():
    score = compute_movement_score(
        relevance_score=1.0,
        confidence_score=1.0,
        evidence_strength=5,
        visibility_impact="high",
        signal_class="thought_leadership_signal",
    )
    # 100 - 10 = 90
    assert score == 90


def test_compute_movement_score_clamp_min():
    score = compute_movement_score(
        relevance_score=0.0,
        confidence_score=0.0,
        evidence_strength=1,
        visibility_impact="low",
        signal_class="weak_signal",
    )
    # 0 + 0 + 6 + 0 = 6
    assert score == 6


def test_compute_movement_strength_thresholds():
    assert compute_movement_strength(0) == "weak"
    assert compute_movement_strength(29) == "weak"
    assert compute_movement_strength(30) == "relevant"
    assert compute_movement_strength(59) == "relevant"
    assert compute_movement_strength(60) == "strong"
    assert compute_movement_strength(79) == "strong"
    assert compute_movement_strength(80) == "market_shaping"
    assert compute_movement_strength(100) == "market_shaping"


def test_map_signal_type_to_class():
    assert map_signal_type_to_class(SignalType.product_update) == "product_capability_move"
    assert map_signal_type_to_class(SignalType.ai_announcement) == "product_capability_move"
    assert map_signal_type_to_class(SignalType.partnership) == "ecosystem_move"
    assert map_signal_type_to_class(SignalType.positioning_change) == "positioning_move"
    assert map_signal_type_to_class(SignalType.target_market_change) == "positioning_move"
    assert map_signal_type_to_class(SignalType.event_or_thought_leadership) == "thought_leadership_signal"
    assert map_signal_type_to_class(SignalType.hiring_signal) == "hiring_signal"
    assert map_signal_type_to_class(SignalType.other) == "weak_signal"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_assessor_rules.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement rules.py**

```python
# backend/app/assessor/rules.py
from app.models.signal import SignalType

_VISIBILITY_WEIGHTS = {"low": 0, "medium": 8, "high": 15}
_SIGNAL_TYPE_CLASS_MAP = {
    SignalType.product_update: "product_capability_move",
    SignalType.ai_announcement: "product_capability_move",
    SignalType.partnership: "ecosystem_move",
    SignalType.positioning_change: "positioning_move",
    SignalType.target_market_change: "positioning_move",
    SignalType.event_or_thought_leadership: "thought_leadership_signal",
    SignalType.hiring_signal: "hiring_signal",
    SignalType.other: "weak_signal",
}


def compute_movement_score(
    relevance_score: float,
    confidence_score: float,
    evidence_strength: int,
    visibility_impact: str,
    signal_class: str,
) -> int:
    score = (
        relevance_score * 35
        + confidence_score * 20
        + evidence_strength * 6
        + _VISIBILITY_WEIGHTS.get(visibility_impact, 0)
        - (10 if signal_class == "thought_leadership_signal" else 0)
    )
    return max(0, min(100, round(score)))


def compute_movement_strength(movement_score: int) -> str:
    if movement_score >= 80:
        return "market_shaping"
    if movement_score >= 60:
        return "strong"
    if movement_score >= 30:
        return "relevant"
    return "weak"


def map_signal_type_to_class(signal_type: SignalType) -> str:
    return _SIGNAL_TYPE_CLASS_MAP.get(signal_type, "weak_signal")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_assessor_rules.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/assessor/rules.py backend/tests/test_assessor_rules.py
rtk git commit -m "feat: implement movement_score scoring formula and signal_type→signal_class mapping"
```

---

## Task 6: LLM Prompts

**Files:**
- Create: `backend/app/assessor/prompts.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_assessor_rules.py — append
def test_build_assessment_prompt_contains_signal_data():
    from app.assessor.prompts import build_assessment_prompt
    prompt = build_assessment_prompt(
        company_name="ATOSS",
        signal_type="ai_announcement",
        title="New AI Scheduling",
        topic="AI",
        summary="ATOSS launches AI scheduling module.",
        why_it_matters="Competes with our core product.",
        relevance_score=0.9,
        confidence_score=0.85,
        context={"core_capabilities": ["WFM"], "strategic_priorities": ["AI-first"], "differentiators": ["Speed"]},
        capability_keys=["shift_scheduling", "ai_copilot"],
    )
    assert "ATOSS" in prompt
    assert "ai_announcement" in prompt
    assert "New AI Scheduling" in prompt
    assert "shift_scheduling" in prompt
    assert "JSON" in prompt


def test_build_summary_prompt_contains_assessments():
    from app.assessor.prompts import build_summary_prompt
    assessments = [
        {"capability_primary": "ai_copilot", "signal_class": "product_capability_move",
         "assessment_summary": "Launched AI feature.", "movement_strength": "strong"}
    ]
    prompt = build_summary_prompt(
        company_name="ATOSS",
        period_label="last 30 days",
        assessments=assessments,
        context={"core_capabilities": ["WFM"], "strategic_priorities": ["Scale"]},
    )
    assert "ATOSS" in prompt
    assert "ai_copilot" in prompt
    assert "last 30 days" in prompt
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && python -m pytest tests/test_assessor_rules.py::test_build_assessment_prompt_contains_signal_data tests/test_assessor_rules.py::test_build_summary_prompt_contains_assessments -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement prompts.py**

```python
# backend/app/assessor/prompts.py
import json
from typing import Any

ASSESSMENT_SYSTEM_PROMPT = """You are a competitive intelligence analyst for a Workforce Management (WFM) software company.
Your task is to assess competitor signals and return a structured JSON evaluation.
Return ONLY valid JSON. No prose, no explanation, no markdown code fences.
Your output must be parseable by json.loads()."""


def build_assessment_prompt(
    company_name: str,
    signal_type: str,
    title: str,
    topic: str | None,
    summary: str | None,
    why_it_matters: str | None,
    relevance_score: float,
    confidence_score: float,
    context: dict[str, Any],
    capability_keys: list[str],
) -> str:
    return f"""Assess this competitor signal for a WFM software vendor.

Signal:
- Company: {company_name}
- Type: {signal_type}
- Title: {title}
- Topic: {topic or "unknown"}
- Summary: {summary or "no summary"}
- Why it matters: {why_it_matters or "unknown"}
- Relevance score: {relevance_score}
- Confidence score: {confidence_score}

Our internal context:
- Core capabilities: {", ".join(context.get("core_capabilities", []))}
- Strategic priorities: {", ".join(context.get("strategic_priorities", []))}
- Differentiators: {", ".join(context.get("differentiators", []))}

Available capability keys: {", ".join(capability_keys)}

Return exactly this JSON object (no other text):
{{
  "capability_primary": "<one capability key from the list above, or null>",
  "capability_secondary": ["<key>"],
  "signal_class": "<product_capability_move|positioning_move|ecosystem_move|thought_leadership_signal|hiring_signal|weak_signal|market_expansion_move>",
  "evidence_strength": <integer 1-5>,
  "visibility_impact": "<low|medium|high>",
  "strategic_intent_guess": "<one sentence describing likely strategic intent>",
  "gameplay_tags": ["<tag>"],
  "assessment_summary": "<2-3 sentence summary of what this signal means>",
  "implication_for_us": "<1-2 sentences on what this means for our product/strategy>",
  "watch_items": ["<specific thing to monitor>"],
  "confidence": <float 0.0-1.0>
}}"""


SUMMARY_SYSTEM_PROMPT = """You are a competitive intelligence analyst for a WFM software company.
Synthesize multiple signal assessments into a competitor summary.
Return ONLY valid JSON. No prose, no markdown."""


def build_summary_prompt(
    company_name: str,
    period_label: str,
    assessments: list[dict[str, Any]],
    context: dict[str, Any],
) -> str:
    assessments_text = json.dumps(assessments, indent=2)
    return f"""Synthesize these signal assessments for competitor "{company_name}" over the {period_label}.

Assessments ({len(assessments)} signals):
{assessments_text}

Our internal context:
- Core capabilities: {", ".join(context.get("core_capabilities", []))}
- Strategic priorities: {", ".join(context.get("strategic_priorities", []))}

Return exactly this JSON object (no other text):
{{
  "strategic_posture": "<2-4 word label e.g. aggressive_expansion, defensive_consolidation, niche_deepening>",
  "positioning_summary": "<2-3 sentences on the competitor's overall strategic direction>",
  "top_capabilities": ["<capability_key>"],
  "capability_assessment": [
    {{"key": "<capability_key>", "label": "<label>", "activity_level": "<low|medium|high>", "notes": "<one sentence>"}}
  ],
  "top_risks": ["<risk for us, one sentence each>"],
  "top_opportunities": ["<opportunity for us, one sentence each>"],
  "watchpoints": ["<specific thing to monitor going forward>"]
}}"""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_assessor_rules.py::test_build_assessment_prompt_contains_signal_data tests/test_assessor_rules.py::test_build_summary_prompt_contains_assessments -v
```
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/assessor/prompts.py
rtk git commit -m "feat: add assessor LLM prompt templates for assessment and competitor summary"
```

---

## Task 7: Assessment Parser

**Files:**
- Create: `backend/app/assessor/parser.py`
- Update: `backend/tests/test_assessor_rules.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_assessor_rules.py — append
def test_parse_assessment_valid_json():
    from app.assessor.parser import parse_assessment_response, AssessmentLLMOutput
    raw = json.dumps({
        "capability_primary": "ai_copilot",
        "capability_secondary": ["shift_scheduling"],
        "signal_class": "product_capability_move",
        "evidence_strength": 4,
        "visibility_impact": "high",
        "strategic_intent_guess": "Positioning as AI-first WFM vendor.",
        "gameplay_tags": ["ai-narrative"],
        "assessment_summary": "Launched new AI feature.",
        "implication_for_us": "Direct competition with our roadmap.",
        "watch_items": ["Monitor adoption rate"],
        "confidence": 0.85,
    })
    result = parse_assessment_response(raw)
    assert result is not None
    assert result.capability_primary == "ai_copilot"
    assert result.evidence_strength == 4
    assert result.confidence == 0.85


def test_parse_assessment_invalid_json_returns_none():
    from app.assessor.parser import parse_assessment_response
    result = parse_assessment_response("not json at all")
    assert result is None


def test_parse_assessment_missing_required_field_returns_none():
    from app.assessor.parser import parse_assessment_response
    raw = json.dumps({"capability_primary": "ai_copilot"})  # missing most fields
    # Should still parse — all fields are optional in LLM output
    result = parse_assessment_response(raw)
    assert result is not None  # partial data is accepted


import json  # add this at the top of the test file
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && python -m pytest tests/test_assessor_rules.py::test_parse_assessment_valid_json tests/test_assessor_rules.py::test_parse_assessment_invalid_json_returns_none -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement parser.py**

```python
# backend/app/assessor/parser.py
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class AssessmentLLMOutput(BaseModel):
    capability_primary: Optional[str] = None
    capability_secondary: list[str] = Field(default_factory=list)
    signal_class: Optional[str] = None
    evidence_strength: Optional[int] = Field(default=None, ge=1, le=5)
    visibility_impact: Optional[str] = None
    strategic_intent_guess: Optional[str] = None
    gameplay_tags: list[str] = Field(default_factory=list)
    assessment_summary: Optional[str] = None
    implication_for_us: Optional[str] = None
    watch_items: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @field_validator("visibility_impact")
    @classmethod
    def validate_visibility_impact(cls, v):
        if v is not None and v not in ("low", "medium", "high"):
            return None
        return v

    @field_validator("signal_class")
    @classmethod
    def validate_signal_class(cls, v):
        valid = {
            "product_capability_move", "positioning_move", "ecosystem_move",
            "thought_leadership_signal", "hiring_signal", "weak_signal", "market_expansion_move",
        }
        if v is not None and v not in valid:
            return None
        return v


class SummaryLLMOutput(BaseModel):
    strategic_posture: Optional[str] = None
    positioning_summary: Optional[str] = None
    top_capabilities: list[str] = Field(default_factory=list)
    capability_assessment: list[dict] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    top_opportunities: list[str] = Field(default_factory=list)
    watchpoints: list[str] = Field(default_factory=list)


def _extract_json(raw: str) -> Optional[dict]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    import re
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def parse_assessment_response(raw: str) -> Optional[AssessmentLLMOutput]:
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        return AssessmentLLMOutput.model_validate(data)
    except Exception as e:
        logger.warning("Assessment validation error: %s", e)
        return None


def parse_summary_response(raw: str) -> Optional[SummaryLLMOutput]:
    data = _extract_json(raw)
    if data is None:
        return None
    try:
        return SummaryLLMOutput.model_validate(data)
    except Exception as e:
        logger.warning("Summary validation error: %s", e)
        return None
```

- [ ] **Step 4: Add `import json` to top of test file**

Open `backend/tests/test_assessor_rules.py` and add `import json` at line 1 (before other imports).

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_assessor_rules.py -v
```
Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/assessor/parser.py backend/tests/test_assessor_rules.py
rtk git commit -m "feat: add assessment LLM output parser with Pydantic v2 validation"
```

---

## Task 8: assess_signal() Pipeline

**Files:**
- Create: `backend/app/assessor/pipeline.py`
- Create: `backend/tests/test_assessor_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_assessor_pipeline.py
import json
from unittest.mock import patch
import pytest


def _make_assessment_json(**overrides):
    base = {
        "capability_primary": "ai_copilot",
        "capability_secondary": ["shift_scheduling"],
        "signal_class": "product_capability_move",
        "evidence_strength": 4,
        "visibility_impact": "high",
        "strategic_intent_guess": "AI-first positioning.",
        "gameplay_tags": ["ai-narrative"],
        "assessment_summary": "Launched new AI module.",
        "implication_for_us": "Direct competition.",
        "watch_items": ["Monitor adoption"],
        "confidence": 0.85,
    }
    base.update(overrides)
    return json.dumps(base)


def test_assess_signal_creates_assessment(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    company = Company(name="ATOSS", slug="atoss-assess", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/assess", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/assess/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="AI Feature", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.85,
    )
    db_session.add(signal)
    db_session.commit()

    with patch("app.assessor.pipeline.call_llm", return_value=_make_assessment_json()):
        assess_signal(signal, db_session)

    assessment = db_session.query(SignalAssessment).filter(SignalAssessment.signal_id == signal.id).first()
    assert assessment is not None
    assert assessment.capability_primary == "ai_copilot"
    assert assessment.movement_score is not None
    assert assessment.movement_strength is not None


def test_assess_signal_overwrites_existing(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    company = Company(name="ATOSS2", slug="atoss-reassess", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/reassess", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/reassess/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="AI Feature 2", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.85,
    )
    db_session.add(signal)
    db_session.commit()

    with patch("app.assessor.pipeline.call_llm", return_value=_make_assessment_json(capability_primary="demand_forecasting")):
        assess_signal(signal, db_session)

    # Re-assess with different capability
    with patch("app.assessor.pipeline.call_llm", return_value=_make_assessment_json(capability_primary="shift_scheduling")):
        assess_signal(signal, db_session)

    assessments = db_session.query(SignalAssessment).filter(SignalAssessment.signal_id == signal.id).all()
    assert len(assessments) == 1
    assert assessments[0].capability_primary == "shift_scheduling"


def test_assess_signal_handles_llm_failure_gracefully(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    company = Company(name="ATOSS3", slug="atoss-fail", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/fail", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/fail/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="AI Feature 3", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.85,
    )
    db_session.add(signal)
    db_session.commit()

    with patch("app.assessor.pipeline.call_llm", return_value="not json"):
        assess_signal(signal, db_session)

    # No assessment created, no exception raised
    assert db_session.query(SignalAssessment).count() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_assessor_pipeline.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement pipeline.py**

```python
# backend/app/assessor/pipeline.py
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.analyser.client import call_llm
from app.assessor.prompts import ASSESSMENT_SYSTEM_PROMPT, build_assessment_prompt
from app.assessor.parser import parse_assessment_response, MAX_RETRIES
from app.assessor.rules import compute_movement_score, compute_movement_strength, map_signal_type_to_class
from app.assessor.capabilities import CAPABILITY_KEYS, CAPABILITIES
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.context import InternalCompanyContext

logger = logging.getLogger(__name__)


def assess_signal(signal: Signal, db: Session) -> SignalAssessment | None:
    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
            "core_capabilities": ctx_record.core_capabilities or [],
            "strategic_priorities": ctx_record.strategic_priorities or [],
            "differentiators": ctx_record.differentiators or [],
        }

    company_name = signal.company.name if signal.company else "Unknown"
    prompt = build_assessment_prompt(
        company_name=company_name,
        signal_type=signal.signal_type.value,
        title=signal.title,
        topic=signal.topic,
        summary=signal.summary,
        why_it_matters=signal.why_it_matters,
        relevance_score=signal.relevance_score or 0.0,
        confidence_score=signal.confidence_score or 0.0,
        context=context,
        capability_keys=CAPABILITY_KEYS,
    )

    parsed = None
    for attempt in range(MAX_RETRIES + 1):
        raw = call_llm(prompt)
        parsed = parse_assessment_response(raw)
        if parsed is not None:
            break
        logger.warning(
            "Assessment parse failed (attempt %d/%d) for signal %s",
            attempt + 1, MAX_RETRIES + 1, signal.id,
        )

    if parsed is None:
        logger.warning("All assessment attempts failed for signal %s — skipping", signal.id)
        return None

    # Rule-based fallback for signal_class if LLM returned None
    signal_class = parsed.signal_class or map_signal_type_to_class(signal.signal_type)
    capability_primary = parsed.capability_primary
    strategic_weight = (
        CAPABILITIES[capability_primary]["strategic_weight"]
        if capability_primary and capability_primary in CAPABILITIES
        else 5
    )

    movement_score = compute_movement_score(
        relevance_score=signal.relevance_score or 0.0,
        confidence_score=signal.confidence_score or 0.0,
        evidence_strength=parsed.evidence_strength or 3,
        visibility_impact=parsed.visibility_impact or "low",
        signal_class=signal_class,
    )
    movement_strength = compute_movement_strength(movement_score)

    existing = db.query(SignalAssessment).filter(SignalAssessment.signal_id == signal.id).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.capability_primary = capability_primary
        existing.capability_secondary = parsed.capability_secondary
        existing.signal_class = signal_class
        existing.evidence_strength = parsed.evidence_strength
        existing.visibility_impact = parsed.visibility_impact
        existing.strategic_weight = strategic_weight
        existing.movement_score = movement_score
        existing.movement_strength = movement_strength
        existing.confidence = parsed.confidence
        existing.strategic_intent_guess = parsed.strategic_intent_guess
        existing.gameplay_tags = parsed.gameplay_tags
        existing.assessment_summary = parsed.assessment_summary
        existing.implication_for_us = parsed.implication_for_us
        existing.watch_items = parsed.watch_items
        existing.updated_at = now
        db.commit()
        return existing

    assessment = SignalAssessment(
        signal_id=signal.id,
        company_id=signal.company_id,
        capability_primary=capability_primary,
        capability_secondary=parsed.capability_secondary,
        signal_class=signal_class,
        evidence_strength=parsed.evidence_strength,
        visibility_impact=parsed.visibility_impact,
        strategic_weight=strategic_weight,
        movement_score=movement_score,
        movement_strength=movement_strength,
        confidence=parsed.confidence,
        strategic_intent_guess=parsed.strategic_intent_guess,
        gameplay_tags=parsed.gameplay_tags,
        assessment_summary=parsed.assessment_summary,
        implication_for_us=parsed.implication_for_us,
        watch_items=parsed.watch_items,
        created_at=now,
        updated_at=now,
    )
    db.add(assessment)
    db.commit()
    return assessment
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_assessor_pipeline.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/assessor/pipeline.py backend/tests/test_assessor_pipeline.py
rtk git commit -m "feat: implement assess_signal() pipeline with retry and movement scoring"
```

---

## Task 9: Competitor Summarizer

**Files:**
- Create: `backend/app/assessor/summarizer.py`
- Update: `backend/tests/test_assessor_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_assessor_pipeline.py — append
def test_generate_competitor_summary_creates_record(db_session):
    import json
    from datetime import date
    from unittest.mock import patch
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal, SignalType
    from app.models.signal_assessment import SignalAssessment, MovementStrength, SignalClass, VisibilityImpact
    from app.models.competitor_summary import CompetitorSummary
    from app.assessor.summarizer import generate_competitor_summary

    company = Company(name="SumCo", slug="sumco", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://sumco.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://sumco.com/1")
    db_session.add(doc)
    db_session.commit()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="Big Move", signal_type=SignalType.ai_announcement,
        relevance_score=0.9, confidence_score=0.8,
    )
    db_session.add(signal)
    db_session.commit()
    assessment = SignalAssessment(
        signal_id=signal.id, company_id=company.id,
        capability_primary="ai_copilot",
        signal_class=SignalClass.product_capability_move,
        evidence_strength=4,
        visibility_impact=VisibilityImpact.high,
        movement_score=82, movement_strength=MovementStrength.market_shaping,
        assessment_summary="Major AI move.",
    )
    db_session.add(assessment)
    db_session.commit()

    summary_json = json.dumps({
        "strategic_posture": "aggressive_expansion",
        "positioning_summary": "Moving aggressively into AI.",
        "top_capabilities": ["ai_copilot"],
        "capability_assessment": [{"key": "ai_copilot", "label": "AI Copilot", "activity_level": "high", "notes": "Flagship feature."}],
        "top_risks": ["AI feature parity risk"],
        "top_opportunities": ["Partner with adjacent vendors"],
        "watchpoints": ["Track AI copilot adoption"],
    })

    with patch("app.assessor.summarizer.call_llm", return_value=summary_json):
        result = generate_competitor_summary(company, "30d", db_session)

    assert result is not None
    assert result.strategic_posture == "aggressive_expansion"
    assert db_session.query(CompetitorSummary).count() == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd backend && python -m pytest tests/test_assessor_pipeline.py::test_generate_competitor_summary_creates_record -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement summarizer.py**

```python
# backend/app/assessor/summarizer.py
import logging
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.orm import Session

from app.analyser.client import call_llm
from app.assessor.prompts import SUMMARY_SYSTEM_PROMPT, build_summary_prompt
from app.assessor.parser import parse_summary_response
from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.competitor_summary import CompetitorSummary, PeriodType
from app.models.context import InternalCompanyContext

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "quarter": 90}
_PERIOD_LABELS = {"7d": "last 7 days", "30d": "last 30 days", "90d": "last 90 days", "quarter": "last quarter"}


def generate_competitor_summary(
    company: Company,
    period_type: str,
    db: Session,
) -> CompetitorSummary | None:
    days = _PERIOD_DAYS.get(period_type, 30)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    assessments = (
        db.query(SignalAssessment)
        .join(Signal, SignalAssessment.signal_id == Signal.id)
        .filter(
            SignalAssessment.company_id == company.id,
            Signal.created_at >= since,
        )
        .order_by(Signal.created_at.desc())
        .limit(50)
        .all()
    )

    if not assessments:
        logger.info("No assessments found for %s in period %s — skipping summary", company.name, period_type)
        return None

    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
            "core_capabilities": ctx_record.core_capabilities or [],
            "strategic_priorities": ctx_record.strategic_priorities or [],
        }

    assessments_data = [
        {
            "capability_primary": a.capability_primary,
            "signal_class": a.signal_class.value if a.signal_class else None,
            "evidence_strength": a.evidence_strength,
            "movement_strength": a.movement_strength.value if a.movement_strength else None,
            "assessment_summary": a.assessment_summary,
            "implication_for_us": a.implication_for_us,
            "gameplay_tags": a.gameplay_tags or [],
        }
        for a in assessments
    ]

    prompt = build_summary_prompt(
        company_name=company.name,
        period_label=_PERIOD_LABELS.get(period_type, f"last {days} days"),
        assessments=assessments_data,
        context=context,
    )

    raw = call_llm(prompt)
    parsed = parse_summary_response(raw)

    if parsed is None:
        logger.warning("Summary parsing failed for %s period %s", company.name, period_type)
        return None

    scores = [a.movement_score for a in assessments if a.movement_score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    try:
        period_type_enum = PeriodType(period_type)
    except ValueError:
        period_type_enum = PeriodType.thirty_days

    summary = CompetitorSummary(
        company_id=company.id,
        period_type=period_type_enum,
        period_start=date.fromtimestamp((now - timedelta(days=days)).timestamp()),
        period_end=date.fromtimestamp(now.timestamp()),
        strategic_posture=parsed.strategic_posture,
        positioning_summary=parsed.positioning_summary,
        top_capabilities=parsed.top_capabilities,
        capability_assessment=parsed.capability_assessment,
        top_risks=parsed.top_risks,
        top_opportunities=parsed.top_opportunities,
        watchpoints=parsed.watchpoints,
        avg_movement_score=avg_score,
        signal_count=len(assessments),
        created_at=now,
        updated_at=now,
    )
    db.add(summary)
    db.commit()
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_assessor_pipeline.py -v
```
Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/assessor/summarizer.py
rtk git commit -m "feat: implement generate_competitor_summary() with LLM aggregation"
```

---

## Task 10: Intelligence Router

**Files:**
- Create: `backend/app/routers/intelligence.py`
- Create: `backend/tests/test_intelligence_router.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_intelligence_router.py
def test_overview_endpoint_returns_expected_keys(client):
    resp = client.get("/api/intelligence/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_movers_7d" in data
    assert "top_movers_30d" in data
    assert "capability_heatmap" in data
    assert "recent_market_shaping" in data
    assert "emerging_risks" in data
    assert "emerging_opportunities" in data


def test_signals_feed_returns_paginated_response(client):
    resp = client.get("/api/intelligence/signals/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_competitor_workspace_404_for_unknown_slug(client):
    resp = client.get("/api/intelligence/competitors/nonexistent-slug/workspace")
    assert resp.status_code == 404


def test_assess_signal_endpoint_404_for_unknown_id(client):
    resp = client.post("/api/intelligence/signals/nonexistent-id/assess")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && python -m pytest tests/test_intelligence_router.py -v
```
Expected: 404 or `ImportError` (endpoint not registered yet)

- [ ] **Step 3: Implement intelligence.py**

```python
# backend/app/routers/intelligence.py
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.database import get_db
from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment, MovementStrength
from app.models.competitor_summary import CompetitorSummary, PeriodType

logger = logging.getLogger(__name__)
router = APIRouter()


def _assessment_to_dict(a: SignalAssessment) -> dict:
    return {
        "id": a.id,
        "signal_id": a.signal_id,
        "company_id": a.company_id,
        "capability_primary": a.capability_primary,
        "capability_secondary": a.capability_secondary or [],
        "signal_class": a.signal_class.value if a.signal_class else None,
        "evidence_strength": a.evidence_strength,
        "visibility_impact": a.visibility_impact.value if a.visibility_impact else None,
        "strategic_weight": a.strategic_weight,
        "movement_score": a.movement_score,
        "movement_strength": a.movement_strength.value if a.movement_strength else None,
        "confidence": a.confidence,
        "strategic_intent_guess": a.strategic_intent_guess,
        "gameplay_tags": a.gameplay_tags or [],
        "assessment_summary": a.assessment_summary,
        "implication_for_us": a.implication_for_us,
        "watch_items": a.watch_items or [],
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _signal_feed_item(signal: Signal, assessment: Optional[SignalAssessment]) -> dict:
    doc = signal.document
    source = doc.source if doc else None
    return {
        "id": signal.id,
        "title": signal.title,
        "signal_type": signal.signal_type.value,
        "topic": signal.topic,
        "summary": signal.summary,
        "why_it_matters": signal.why_it_matters,
        "relevance_score": signal.relevance_score,
        "confidence_score": signal.confidence_score,
        "published_at": signal.published_at.isoformat() if signal.published_at else None,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
        "company_id": signal.company_id,
        "company_name": signal.company.name if signal.company else None,
        "company_slug": signal.company.slug if signal.company else None,
        "source_url": doc.url if doc else None,
        "document_id": signal.document_id,
        "document_title": doc.title if doc else None,
        "assessment": _assessment_to_dict(assessment) if assessment else None,
    }


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    def _top_movers(cutoff: datetime) -> list[dict]:
        rows = (
            db.query(
                SignalAssessment.company_id,
                func.avg(SignalAssessment.movement_score).label("avg_score"),
                func.count(SignalAssessment.id).label("count"),
            )
            .join(Signal, SignalAssessment.signal_id == Signal.id)
            .filter(Signal.created_at >= cutoff)
            .group_by(SignalAssessment.company_id)
            .order_by(func.avg(SignalAssessment.movement_score).desc())
            .limit(10)
            .all()
        )
        result = []
        for row in rows:
            company = db.query(Company).filter(Company.id == row.company_id).first()
            if not company:
                continue
            top_cap = (
                db.query(SignalAssessment.capability_primary)
                .join(Signal, SignalAssessment.signal_id == Signal.id)
                .filter(SignalAssessment.company_id == row.company_id, Signal.created_at >= cutoff)
                .group_by(SignalAssessment.capability_primary)
                .order_by(func.count(SignalAssessment.id).desc())
                .limit(1)
                .scalar()
            )
            result.append({
                "company_id": company.id,
                "company_name": company.name,
                "company_slug": company.slug,
                "avg_movement_score": round(row.avg_score or 0, 1),
                "signal_count": row.count,
                "top_capability": top_cap,
            })
        return result

    # Capability heatmap: companies × capabilities, colored by avg movement_score (30d)
    heatmap_rows = (
        db.query(
            SignalAssessment.company_id,
            SignalAssessment.capability_primary,
            func.avg(SignalAssessment.movement_score).label("avg_score"),
        )
        .join(Signal, SignalAssessment.signal_id == Signal.id)
        .filter(Signal.created_at >= cutoff_30d, SignalAssessment.capability_primary.isnot(None))
        .group_by(SignalAssessment.company_id, SignalAssessment.capability_primary)
        .all()
    )
    heatmap: dict[str, dict] = {}
    for row in heatmap_rows:
        company = db.query(Company).filter(Company.id == row.company_id).first()
        if not company:
            continue
        key = company.id
        if key not in heatmap:
            heatmap[key] = {"company_id": company.id, "company_name": company.name, "capabilities": {}}
        if row.capability_primary:
            heatmap[key]["capabilities"][row.capability_primary] = round(row.avg_score or 0, 1)

    # Recent market_shaping signals
    market_shaping = (
        db.query(SignalAssessment)
        .options(selectinload(SignalAssessment.signal))
        .filter(SignalAssessment.movement_strength == MovementStrength.market_shaping)
        .join(Signal, SignalAssessment.signal_id == Signal.id)
        .filter(Signal.created_at >= cutoff_30d)
        .order_by(Signal.created_at.desc())
        .limit(10)
        .all()
    )

    # Emerging risks/opportunities from newest 30d summaries
    emerging_risks: list[str] = []
    emerging_opportunities: list[str] = []
    companies_with_summaries = (
        db.query(CompetitorSummary.company_id)
        .filter(CompetitorSummary.period_type == PeriodType.thirty_days)
        .distinct()
        .all()
    )
    for (cid,) in companies_with_summaries:
        latest = (
            db.query(CompetitorSummary)
            .filter(
                CompetitorSummary.company_id == cid,
                CompetitorSummary.period_type == PeriodType.thirty_days,
            )
            .order_by(CompetitorSummary.created_at.desc())
            .first()
        )
        if latest:
            emerging_risks.extend(latest.top_risks or [])
            emerging_opportunities.extend(latest.top_opportunities or [])
    # Simple dedup
    emerging_risks = list(dict.fromkeys(emerging_risks))[:10]
    emerging_opportunities = list(dict.fromkeys(emerging_opportunities))[:10]

    return {
        "top_movers_7d": _top_movers(cutoff_7d),
        "top_movers_30d": _top_movers(cutoff_30d),
        "capability_heatmap": list(heatmap.values()),
        "recent_market_shaping": [
            _signal_feed_item(a.signal, a)
            for a in market_shaping
            if a.signal
        ],
        "emerging_risks": emerging_risks,
        "emerging_opportunities": emerging_opportunities,
    }


@router.get("/competitors/{slug}/workspace")
def get_competitor_workspace(slug: str, db: Session = Depends(get_db)) -> dict:
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Competitor not found")

    now = datetime.now(timezone.utc)
    cutoff_30d = now - timedelta(days=30)

    def _latest_summary(period_type: PeriodType):
        return (
            db.query(CompetitorSummary)
            .filter(
                CompetitorSummary.company_id == company.id,
                CompetitorSummary.period_type == period_type,
            )
            .order_by(CompetitorSummary.created_at.desc())
            .first()
        )

    def _summary_to_dict(s: Optional[CompetitorSummary]) -> Optional[dict]:
        if s is None:
            return None
        return {
            "id": s.id,
            "company_id": s.company_id,
            "period_type": s.period_type.value,
            "period_start": s.period_start.isoformat(),
            "period_end": s.period_end.isoformat(),
            "strategic_posture": s.strategic_posture,
            "positioning_summary": s.positioning_summary,
            "top_capabilities": s.top_capabilities or [],
            "capability_assessment": s.capability_assessment or [],
            "top_risks": s.top_risks or [],
            "top_opportunities": s.top_opportunities or [],
            "watchpoints": s.watchpoints or [],
            "avg_movement_score": s.avg_movement_score,
            "signal_count": s.signal_count,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }

    recent_assessments = (
        db.query(SignalAssessment)
        .options(selectinload(SignalAssessment.signal))
        .filter(SignalAssessment.company_id == company.id)
        .join(Signal, SignalAssessment.signal_id == Signal.id)
        .order_by(Signal.created_at.desc())
        .limit(20)
        .all()
    )

    cap_dist_rows = (
        db.query(
            SignalAssessment.capability_primary,
            func.count(SignalAssessment.id).label("count"),
            func.avg(SignalAssessment.movement_score).label("avg_score"),
        )
        .filter(SignalAssessment.company_id == company.id, SignalAssessment.capability_primary.isnot(None))
        .group_by(SignalAssessment.capability_primary)
        .order_by(func.count(SignalAssessment.id).desc())
        .all()
    )

    timeline = (
        db.query(Signal)
        .options(selectinload(Signal.assessment))
        .filter(Signal.company_id == company.id)
        .order_by(Signal.published_at.desc().nullslast(), Signal.created_at.desc())
        .limit(30)
        .all()
    )

    return {
        "competitor_profile": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "type": company.type.value,
            "description": company.description,
            "website": company.website,
            "created_at": company.created_at.isoformat() if company.created_at else None,
        },
        "summary_30d": _summary_to_dict(_latest_summary(PeriodType.thirty_days)),
        "summary_90d": _summary_to_dict(_latest_summary(PeriodType.ninety_days)),
        "recent_assessments": [
            _signal_feed_item(a.signal, a) for a in recent_assessments if a.signal
        ],
        "capability_distribution": [
            {
                "capability_key": r.capability_primary,
                "count": r.count,
                "avg_movement_score": round(r.avg_score or 0, 1),
            }
            for r in cap_dist_rows
        ],
        "timeline_of_moves": [
            {
                "signal_id": s.id,
                "title": s.title,
                "signal_type": s.signal_type.value,
                "published_at": s.published_at.isoformat() if s.published_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "movement_strength": s.assessment.movement_strength.value if s.assessment and s.assessment.movement_strength else None,
                "movement_score": s.assessment.movement_score if s.assessment else None,
                "capability_primary": s.assessment.capability_primary if s.assessment else None,
            }
            for s in timeline
        ],
    }


@router.get("/signals/feed")
def get_signals_feed(
    company_id: Optional[str] = None,
    capability: Optional[str] = None,
    signal_type: Optional[str] = None,
    movement_strength: Optional[str] = None,
    min_confidence: Optional[float] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sort_by: str = Query(default="published_at", pattern="^(published_at|movement_score|confidence)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    query = (
        db.query(Signal)
        .options(
            selectinload(Signal.company),
            selectinload(Signal.document).selectinload("source"),
            selectinload(Signal.assessment),
        )
    )

    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if from_date:
        try:
            query = query.filter(Signal.published_at >= datetime.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            query = query.filter(Signal.published_at <= datetime.fromisoformat(to_date))
        except ValueError:
            pass

    if capability or movement_strength or min_confidence:
        query = query.join(SignalAssessment, SignalAssessment.signal_id == Signal.id, isouter=True)
        if capability:
            query = query.filter(SignalAssessment.capability_primary == capability)
        if movement_strength:
            query = query.filter(SignalAssessment.movement_strength == movement_strength)
        if min_confidence:
            query = query.filter(SignalAssessment.confidence >= min_confidence)

    total = query.count()

    if sort_by == "movement_score":
        if not (capability or movement_strength or min_confidence):
            query = query.join(SignalAssessment, SignalAssessment.signal_id == Signal.id, isouter=True)
        query = query.order_by(SignalAssessment.movement_score.desc().nullslast(), Signal.created_at.desc())
    elif sort_by == "confidence":
        if not (capability or movement_strength or min_confidence):
            query = query.join(SignalAssessment, SignalAssessment.signal_id == Signal.id, isouter=True)
        query = query.order_by(SignalAssessment.confidence.desc().nullslast(), Signal.created_at.desc())
    else:
        query = query.order_by(Signal.published_at.desc().nullslast(), Signal.created_at.desc())

    signals = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_signal_feed_item(s, s.assessment) for s in signals],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/signals/{signal_id}/assess")
def trigger_assess_signal(signal_id: str, db: Session = Depends(get_db)) -> dict:
    signal = (
        db.query(Signal)
        .options(selectinload(Signal.company), selectinload(Signal.document))
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    from app.assessor.pipeline import assess_signal
    assessment = assess_signal(signal, db)
    if assessment is None:
        raise HTTPException(status_code=422, detail="Assessment generation failed")
    return _assessment_to_dict(assessment)


@router.post("/competitors/{company_id}/summarize")
def trigger_summarize(
    company_id: str,
    period_type: str = Query(default="30d", pattern="^(7d|30d|90d|quarter)$"),
    db: Session = Depends(get_db),
) -> dict:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from app.assessor.summarizer import generate_competitor_summary
    summary = generate_competitor_summary(company, period_type, db)
    if summary is None:
        raise HTTPException(status_code=422, detail="No assessments found for this period")

    return {
        "id": summary.id,
        "company_id": summary.company_id,
        "period_type": summary.period_type.value,
        "strategic_posture": summary.strategic_posture,
        "signal_count": summary.signal_count,
        "avg_movement_score": summary.avg_movement_score,
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_intelligence_router.py -v
```
Expected: 4 PASSED (router not yet registered — will get 404 for all routes until Task 11)

Note: The tests will fail with 404 until the router is registered in `main.py` in the next task. Proceed to Task 11.

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/routers/intelligence.py backend/tests/test_intelligence_router.py
rtk git commit -m "feat: implement intelligence router with overview, workspace, feed, and trigger endpoints"
```

---

## Task 11: Wire Up — main.py + Pipeline Hook + Crawl Post-Trigger

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/analyser/pipeline.py`
- Modify: `backend/app/routers/crawl.py`

- [ ] **Step 1: Register intelligence router in main.py**

Edit `backend/app/main.py`. Add import and router registration:

```python
# In the import block (after existing router imports):
from app.routers import intelligence  # noqa: E402

# After the last app.include_router line:
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
```

Full updated import + register section:
```python
from app.routers import (
    companies,
    sources,
    documents,
    signals,
    digests,
    context,
    crawl,
    crawl_runs,
    discovered_pages,
    search,
    stats,
    briefings,
    intelligence,
)  # noqa: E402

app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(digests.router, prefix="/api/digests", tags=["digests"])
app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(crawl_runs.router, prefix="/api/crawl-runs", tags=["crawl-runs"])
app.include_router(
    discovered_pages.router, prefix="/api/discovered-pages", tags=["discovered-pages"]
)
app.include_router(search.search_router, prefix="/api/search", tags=["search"])
app.include_router(
    search.candidates_router,
    prefix="/api/source-candidates",
    tags=["source-candidates"],
)
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(briefings.router, prefix="/api/briefings", tags=["briefings"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
```

- [ ] **Step 2: Add assessment hook to analyser/pipeline.py**

In `backend/app/analyser/pipeline.py`, add the post-step hook immediately after `db.add(signal)` and `doc.is_analysed = True; db.commit()`. The hook should fire after the commit:

```python
# backend/app/analyser/pipeline.py — replace the final section starting from "signal = Signal(..."

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

    # Trigger assessment if signal meets threshold
    try:
        from app.config import settings
        if (signal.relevance_score or 0.0) >= settings.assessment_threshold:
            from app.assessor.pipeline import assess_signal
            assess_signal(signal, db)
    except Exception as e:
        logger.warning("Assessment hook failed for signal %s: %s", signal.id, e)
```

- [ ] **Step 3: Add post-crawl summary trigger to crawl.py**

In `backend/app/routers/crawl.py`, inside `_run_sources_in_thread`, after the existing briefing generation block (around line 204), add:

```python
            # Trigger competitor summaries for companies with new signals in this run
            try:
                from app.models.signal import Signal
                from app.models.company import Company
                from app.assessor.summarizer import generate_competitor_summary
                import threading

                company_ids_with_new_signals = (
                    thread_db.query(Signal.company_id)
                    .filter(Signal.created_at >= crawl_run.started_at)
                    .distinct()
                    .all()
                )
                for (cid,) in company_ids_with_new_signals:
                    company = thread_db.query(Company).filter(Company.id == cid).first()
                    if company:
                        for period in ("7d", "30d"):
                            try:
                                generate_competitor_summary(company, period, thread_db)
                            except Exception as e:
                                logger.warning("Summary gen failed for %s/%s: %s", company.name, period, e)
            except Exception as e:
                logger.warning("Post-crawl summary trigger failed: %s", e)
```

Place this block right after the existing briefing try/except block in `_run_sources_in_thread`.

- [ ] **Step 4: Run all tests to verify nothing is broken**

```bash
cd backend && python -m pytest tests/ -v --tb=short
```
Expected: all previously passing tests still PASS; intelligence router tests now PASS

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/main.py backend/app/analyser/pipeline.py backend/app/routers/crawl.py
rtk git commit -m "feat: wire intelligence router, add assessment hook to analyser pipeline, post-crawl summary trigger"
```

---

## Task 12: Backfill Script

**Files:**
- Create: `backend/scripts/backfill_assessments.py`

- [ ] **Step 1: Create the script**

```python
# backend/scripts/backfill_assessments.py
"""One-time backfill: generate SignalAssessment for all existing signals above threshold.

Usage:
    cd backend
    python scripts/backfill_assessments.py [--threshold 0.4] [--batch-size 20] [--dry-run]
"""
import sys
import os
import argparse
import logging

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Backfill SignalAssessments")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Override ASSESSMENT_THRESHOLD (default: from config)")
    parser.add_argument("--batch-size", type=int, default=20, dest="batch_size")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Report how many signals would be processed, don't call LLM")
    args = parser.parse_args()

    from app.config import settings
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    threshold = args.threshold if args.threshold is not None else settings.assessment_threshold
    logger.info("Starting backfill with threshold=%.2f, batch_size=%d, dry_run=%s",
                threshold, args.batch_size, args.dry_run)

    db = SessionLocal()
    try:
        # Find signals above threshold without an assessment
        already_assessed = db.query(SignalAssessment.signal_id).subquery()
        signals_to_process = (
            db.query(Signal)
            .filter(
                Signal.relevance_score >= threshold,
                ~Signal.id.in_(already_assessed),
            )
            .order_by(Signal.created_at.desc())
            .all()
        )

        total = len(signals_to_process)
        logger.info("Found %d signals to assess", total)

        if args.dry_run:
            logger.info("Dry run — exiting without processing")
            return

        processed = 0
        failed = 0
        for i, signal in enumerate(signals_to_process):
            try:
                # Eager-load relationships needed by assess_signal
                from sqlalchemy.orm import selectinload
                signal = (
                    db.query(Signal)
                    .options(selectinload(Signal.company), selectinload(Signal.document))
                    .filter(Signal.id == signal.id)
                    .first()
                )
                result = assess_signal(signal, db)
                if result:
                    processed += 1
                else:
                    failed += 1
                if (i + 1) % args.batch_size == 0:
                    logger.info("Progress: %d/%d (failed: %d)", i + 1, total, failed)
            except Exception as e:
                logger.error("Error processing signal %s: %s", signal.id, e)
                failed += 1

        logger.info("Backfill complete: %d processed, %d failed, %d total", processed, failed, total)
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script is importable (dry-run)**

```bash
cd backend && python scripts/backfill_assessments.py --dry-run
```
Expected: logs `Found N signals to assess` and `Dry run — exiting without processing`

- [ ] **Step 3: Run full test suite one final time**

```bash
cd backend && python -m pytest tests/ -v --tb=short
```
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
rtk git add backend/scripts/backfill_assessments.py
rtk git commit -m "feat: add backfill script for generating assessments on existing signals"
```

---

## Self-Review Checklist

- [x] All 5 intelligence endpoints implemented and tested
- [x] `assess_signal()` handles LLM failure gracefully (returns None, no crash)
- [x] `movement_score` is rule-computed, never from LLM
- [x] Assessment threshold configurable via `ASSESSMENT_THRESHOLD` env var
- [x] Post-crawl summary trigger fires for affected companies only
- [x] Backfill script is idempotent (skips already-assessed signals)
- [x] `competitor_summaries` stores history (no unique constraint)
- [x] `signal_assessments.signal_id` is UNIQUE (one assessment per signal)
- [x] JSON fields use `sqlalchemy.JSON` (SQLite-compatible for tests)
- [x] No modifications to existing `/api/signals`, `/api/companies`, etc. endpoints
