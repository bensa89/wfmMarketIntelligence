# Web Search Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the monitoring system with AI-driven Tavily web search as a second ingestion channel feeding the same Document/Signal pipeline.

**Architecture:** New `searcher/` module (peer of `crawler/` and `analyser/`) owns Tavily client, LLM query generation, and orchestration. SearchResult records link to Documents; SourceCandidates surface new domains for review. A hidden per-company "search inbox" Source (is_active=False) satisfies Document.source_id NOT NULL without changing the schema constraint.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), Tavily REST API via httpx, Anthropic SDK (query generation), React/TanStack Query (frontend).

---

## File Map

**Create:**
- `backend/app/models/search_query.py`
- `backend/app/models/search_run.py`
- `backend/app/models/search_result.py`
- `backend/app/models/source_candidate.py`
- `backend/app/schemas/search.py`
- `backend/app/searcher/__init__.py`
- `backend/app/searcher/client.py`
- `backend/app/searcher/query_generator.py`
- `backend/app/searcher/pipeline.py`
- `backend/app/routers/search.py`
- `backend/tests/test_search_router.py`
- `frontend/src/hooks/useSearch.ts`
- `frontend/src/pages/SearchPage.tsx`

**Modify:**
- `backend/app/models/document.py` — add `from_search` column
- `backend/app/models/__init__.py` — export new models
- `backend/app/schemas/__init__.py` — export new schemas
- `backend/app/config.py` — add tavily/search settings
- `backend/app/main.py` — mount search router
- `frontend/src/types/index.ts` — add new types
- `frontend/src/App.tsx` — add `/search` route
- `frontend/src/components/Layout.tsx` — add Search nav item
- `frontend/src/components/SignalCard.tsx` — add from_search badge (read file first)

---

## Task 1: Config — Add Search Settings

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add new settings fields**

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
    tavily_api_key: str = ""
    search_relevance_threshold: float = 0.5
    search_queries_per_company: int = 8


settings = Settings()
```

- [ ] **Step 2: Commit**

```bash
rtk git add backend/app/config.py
rtk git commit -m "feat: add tavily and search settings to config"
```

---

## Task 2: New Data Models

**Files:**
- Create: `backend/app/models/search_query.py`
- Create: `backend/app/models/search_run.py`
- Create: `backend/app/models/search_result.py`
- Create: `backend/app/models/source_candidate.py`
- Modify: `backend/app/models/document.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create SearchQuery model**

```python
# backend/app/models/search_query.py
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_text = Column(String(500), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    topic = Column(String(255), nullable=True)
    search_intent = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    runs = relationship("SearchRun", back_populates="query")
    company = relationship("Company", foreign_keys=[company_id])
```

- [ ] **Step 2: Create SearchRun model**

```python
# backend/app/models/search_run.py
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SearchRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class SearchRun(Base):
    __tablename__ = "search_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_query_id = Column(String(36), ForeignKey("search_queries.id"), nullable=False)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(SAEnum(SearchRunStatus), nullable=False, default=SearchRunStatus.pending)
    result_count = Column(Integer, nullable=True)
    error_message = Column(String(1000), nullable=True)

    query = relationship("SearchQuery", back_populates="runs")
    results = relationship("SearchResult", back_populates="run")
```

- [ ] **Step 3: Create SearchResult model**

```python
# backend/app/models/search_result.py
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class SearchResultStatus(str, enum.Enum):
    pending = "pending"
    fetched = "fetched"
    skipped = "skipped"
    error = "error"


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_run_id = Column(String(36), ForeignKey("search_runs.id"), nullable=False)
    title = Column(String(500), nullable=True)
    url = Column(String(2000), nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    snippet = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    relevance_score = Column(Float, nullable=True)
    processing_status = Column(
        SAEnum(SearchResultStatus),
        nullable=False,
        default=SearchResultStatus.pending,
    )
    linked_document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)

    run = relationship("SearchRun", back_populates="results")
    linked_document = relationship("Document", foreign_keys=[linked_document_id])
```

- [ ] **Step 4: Create SourceCandidate model**

```python
# backend/app/models/source_candidate.py
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.source import SourceType


class SourceCandidateStatus(str, enum.Enum):
    candidate = "candidate"
    approved = "approved"
    rejected = "rejected"
    monitored = "monitored"


class SourceCandidate(Base):
    __tablename__ = "source_candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String(2000), nullable=False)
    domain = Column(String(255), nullable=False)
    title = Column(String(500), nullable=True)
    snippet = Column(Text, nullable=True)
    found_via_query = Column(String(500), nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    source_type_guess = Column(SAEnum(SourceType), nullable=True)
    relevance_score = Column(Float, nullable=True)
    status = Column(
        SAEnum(SourceCandidateStatus),
        nullable=False,
        default=SourceCandidateStatus.candidate,
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", foreign_keys=[company_id])
```

- [ ] **Step 5: Add `from_search` to Document**

Edit `backend/app/models/document.py`. Add one import and one column after `is_analysed`:

```python
# backend/app/models/document.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    url = Column(String(2000), unique=True, nullable=False)
    title = Column(String(500), nullable=True)
    content_markdown = Column(Text, nullable=True)
    content_raw_html = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    content_hash = Column(String(64), nullable=True, index=True)
    is_analysed = Column(Boolean, default=False)
    from_search = Column(Boolean, default=False, nullable=False)

    source = relationship("Source", back_populates="documents")
    signals = relationship("Signal", back_populates="document")
```

- [ ] **Step 6: Update models `__init__.py`**

```python
# backend/app/models/__init__.py
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
]
```

- [ ] **Step 7: Commit**

```bash
rtk git add backend/app/models/search_query.py backend/app/models/search_run.py \
  backend/app/models/search_result.py backend/app/models/source_candidate.py \
  backend/app/models/document.py backend/app/models/__init__.py
rtk git commit -m "feat: add SearchQuery, SearchRun, SearchResult, SourceCandidate models + Document.from_search"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/search.py`
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Create search schemas**

```python
# backend/app/schemas/search.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.search_run import SearchRunStatus
from app.models.search_result import SearchResultStatus
from app.models.source_candidate import SourceCandidateStatus
from app.models.source import SourceType


class SearchQueryRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    query_text: str
    company_id: Optional[str]
    topic: Optional[str]
    search_intent: str
    generated_at: datetime


class SearchRunRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    search_query_id: str
    executed_at: datetime
    status: SearchRunStatus
    result_count: Optional[int]
    error_message: Optional[str]
    query: Optional[SearchQueryRead] = None


class SearchResultRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    search_run_id: str
    title: Optional[str]
    url: str
    domain: Optional[str]
    snippet: Optional[str]
    discovered_at: datetime
    relevance_score: Optional[float]
    processing_status: SearchResultStatus
    linked_document_id: Optional[str]


class SourceCandidateRead(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    url: str
    domain: str
    title: Optional[str]
    snippet: Optional[str]
    found_via_query: Optional[str]
    company_id: Optional[str]
    source_type_guess: Optional[SourceType]
    relevance_score: Optional[float]
    status: SourceCandidateStatus
    created_at: datetime


class SourceCandidateApprove(BaseModel):
    label: Optional[str] = None
    source_type: SourceType = SourceType.news
```

- [ ] **Step 2: Update schemas `__init__.py`**

Read the current `backend/app/schemas/__init__.py` first, then append the new imports. The file currently re-exports company, source, document, signal, digest, context schemas. Add:

```python
from app.schemas.search import (
    SearchQueryRead,
    SearchRunRead,
    SearchResultRead,
    SourceCandidateRead,
    SourceCandidateApprove,
)
```

- [ ] **Step 3: Commit**

```bash
rtk git add backend/app/schemas/search.py backend/app/schemas/__init__.py
rtk git commit -m "feat: add search/source-candidate pydantic schemas"
```

---

## Task 4: Alembic Migration

**Files:**
- Auto-generated migration file in `backend/alembic/versions/`

- [ ] **Step 1: Generate migration**

Run from inside `backend/`:
```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend
alembic revision --autogenerate -m "add_websearch_tables"
```

Expected: a new file created in `alembic/versions/` with upgrade/downgrade functions containing `op.create_table("search_queries", ...)`, `op.create_table("search_runs", ...)`, `op.create_table("search_results", ...)`, `op.create_table("source_candidates", ...)`, and `op.add_column("documents", sa.Column("from_search", ...))`.

- [ ] **Step 2: Apply migration (dev)**

```bash
alembic upgrade head
```

Expected output ends with: `Running upgrade ... -> <revision_id>, add_websearch_tables`

- [ ] **Step 3: Commit migration file**

```bash
rtk git add alembic/versions/
rtk git commit -m "feat: alembic migration for websearch tables"
```

---

## Task 5: Tavily Client

**Files:**
- Create: `backend/app/searcher/__init__.py`
- Create: `backend/app/searcher/client.py`

The Tavily REST API endpoint is `https://api.tavily.com/search`. We use httpx (already in requirements) directly — no new dependency needed.

- [ ] **Step 1: Create `searcher/__init__.py`**

```python
# backend/app/searcher/__init__.py
```

(empty file)

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_searcher_client.py
from unittest.mock import patch, MagicMock
from app.searcher.client import search_tavily, TavilyResult


def test_search_tavily_returns_results():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Quinyx launches AI features",
                "url": "https://techcrunch.com/quinyx-ai",
                "content": "Quinyx announced new AI scheduling features.",
                "score": 0.87,
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.searcher.client.httpx.post", return_value=mock_response):
        results = search_tavily("Quinyx AI scheduling 2025", api_key="fake-key")

    assert len(results) == 1
    assert results[0].title == "Quinyx launches AI features"
    assert results[0].url == "https://techcrunch.com/quinyx-ai"
    assert results[0].score == 0.87
    assert results[0].domain == "techcrunch.com"


def test_search_tavily_returns_empty_on_api_error():
    with patch("app.searcher.client.httpx.post", side_effect=Exception("network error")):
        results = search_tavily("any query", api_key="fake-key")
    assert results == []
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/backend
python -m pytest tests/test_searcher_client.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `app.searcher.client` doesn't exist yet.

- [ ] **Step 4: Implement `searcher/client.py`**

```python
# backend/app/searcher/client.py
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse
import httpx


@dataclass
class TavilyResult:
    title: str
    url: str
    domain: str
    snippet: str
    score: float


def search_tavily(query: str, api_key: str, max_results: int = 10) -> List[TavilyResult]:
    try:
        response = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("results", []):
            parsed = urlparse(item.get("url", ""))
            domain = parsed.netloc.lstrip("www.")
            results.append(
                TavilyResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    domain=domain,
                    snippet=item.get("content") or "",
                    score=float(item.get("score", 0.0)),
                )
            )
        return results
    except Exception:
        return []
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_searcher_client.py -v
```

Expected: 2 tests PASSED.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/searcher/__init__.py backend/app/searcher/client.py \
  backend/tests/test_searcher_client.py
rtk git commit -m "feat: add Tavily search client with tests"
```

---

## Task 6: Query Generator

**Files:**
- Create: `backend/app/searcher/query_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_query_generator.py
from unittest.mock import patch
from app.searcher.query_generator import generate_queries_for_company, QuerySpec


def test_generate_queries_returns_list():
    mock_llm_response = '''[
      {"query_text": "Quinyx AI scheduling 2025", "search_intent": "ai_announcement"},
      {"query_text": "Quinyx partnership announcement", "search_intent": "partnership"}
    ]'''

    with patch("app.searcher.query_generator.call_llm", return_value=mock_llm_response):
        queries = generate_queries_for_company(
            company_name="Quinyx",
            company_type="competitor",
            context={
                "target_industries": ["retail", "healthcare"],
                "core_capabilities": ["scheduling", "time tracking"],
                "strategic_priorities": ["AI"],
                "relevant_competitive_areas": ["workforce management"],
            },
        )

    assert len(queries) == 2
    assert queries[0].query_text == "Quinyx AI scheduling 2025"
    assert queries[0].search_intent == "ai_announcement"


def test_generate_queries_returns_empty_on_parse_error():
    with patch("app.searcher.query_generator.call_llm", return_value="invalid json"):
        queries = generate_queries_for_company(
            company_name="Quinyx",
            company_type="competitor",
            context={},
        )
    assert queries == []


def test_generate_trend_queries_returns_list():
    mock_response = '''[
      {"query_text": "workforce management AI trends 2025", "search_intent": "market_trend"}
    ]'''

    with patch("app.searcher.query_generator.call_llm", return_value=mock_response):
        queries = generate_trend_queries(competitive_areas=["workforce management", "scheduling"])

    assert len(queries) == 1
    assert queries[0].search_intent == "market_trend"


# add import at top after writing implementation
from app.searcher.query_generator import generate_trend_queries  # noqa: E402
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_query_generator.py -v
```

Expected: `ImportError` — module doesn't exist.

- [ ] **Step 3: Implement `searcher/query_generator.py`**

```python
# backend/app/searcher/query_generator.py
import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any

from app.analyser.client import call_llm
from app.config import settings


@dataclass
class QuerySpec:
    query_text: str
    search_intent: str


def _parse_query_list(raw: str) -> List[QuerySpec]:
    try:
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not json_match:
            return []
        data = json.loads(json_match.group(0))
        return [
            QuerySpec(
                query_text=str(item.get("query_text", ""))[:500],
                search_intent=str(item.get("search_intent", "general"))[:100],
            )
            for item in data
            if item.get("query_text")
        ]
    except Exception:
        return []


def generate_queries_for_company(
    company_name: str,
    company_type: str,
    context: Dict[str, Any],
) -> List[QuerySpec]:
    n = settings.search_queries_per_company
    industries = ", ".join(context.get("target_industries", []))
    capabilities = ", ".join(context.get("core_capabilities", []))
    priorities = ", ".join(context.get("strategic_priorities", []))
    competitive = ", ".join(context.get("relevant_competitive_areas", []))

    prompt = f"""You are a competitive intelligence analyst. Generate {n} web search queries to find recent news, reports, and mentions about the company "{company_name}" (type: {company_type}).

Our company context:
- Target industries: {industries or "N/A"}
- Core capabilities: {capabilities or "N/A"}
- Strategic priorities: {priorities or "N/A"}
- Competitive areas: {competitive or "N/A"}

Generate queries covering these intents: ai_announcement, product_update, partnership, pricing, hiring, event, analyst_coverage, positioning.

Respond ONLY with a JSON array:
[
  {{"query_text": "short precise search query", "search_intent": "intent_name"}},
  ...
]

No markdown fences, no extra text."""

    raw = call_llm(prompt)
    return _parse_query_list(raw)


def generate_trend_queries(competitive_areas: List[str]) -> List[QuerySpec]:
    areas = ", ".join(competitive_areas) if competitive_areas else "workforce management"
    prompt = f"""Generate 5 web search queries to discover recent market trends, news, and analysis in these areas: {areas}.

Focus on: industry reports, analyst coverage, emerging technologies, regulatory changes, market developments.

Respond ONLY with a JSON array:
[
  {{"query_text": "short precise search query", "search_intent": "market_trend"}},
  ...
]

No markdown fences, no extra text."""

    raw = call_llm(prompt)
    return _parse_query_list(raw)
```

- [ ] **Step 4: Fix test import — update test file to import `generate_trend_queries` at top**

Edit `backend/tests/test_query_generator.py`: move the `generate_trend_queries` import to the top with the other imports:

```python
from app.searcher.query_generator import generate_queries_for_company, generate_trend_queries, QuerySpec
```

Remove the duplicate import at the bottom of the test file.

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_query_generator.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/searcher/query_generator.py backend/tests/test_query_generator.py
rtk git commit -m "feat: add LLM-based search query generator with tests"
```

---

## Task 7: Searcher Pipeline

**Files:**
- Create: `backend/app/searcher/pipeline.py`

The pipeline orchestrates: generate queries → search Tavily → save SearchRun/SearchResult → fetch relevant results → create Document (from_search=True) → analyse → create SourceCandidates.

**Key rule for source_id:** Before processing a company's search results, ensure a hidden "search inbox" Source exists for that company (`url=f"search://{company.id}"`, `is_active=False`). All search-ingested Documents for that company use this source_id.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_searcher_pipeline.py
import os
os.environ["AUTH_USERNAME"] = "testuser"
os.environ["AUTH_PASSWORD"] = "testpass"
os.environ["DATABASE_URL"] = "sqlite:///./test_search_pipeline.db"

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.company import Company, CompanyType
from app.models.search_run import SearchRunStatus
from app.models.search_result import SearchResultStatus
from app.models.source_candidate import SourceCandidateStatus
from app.searcher.pipeline import run_search_for_company
from app.searcher.client import TavilyResult
from app.searcher.query_generator import QuerySpec

TEST_DB = "./test_search_pipeline.db"

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os as _os
    if _os.path.exists(TEST_DB):
        _os.remove(TEST_DB)


@pytest.fixture
def company(db_session):
    c = Company(name="Quinyx", slug="quinyx", type=CompanyType.competitor)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def test_run_search_creates_search_run_and_results(db_session, company):
    fake_queries = [QuerySpec(query_text="Quinyx AI 2025", search_intent="ai_announcement")]
    fake_results = [
        TavilyResult(
            title="Quinyx AI news",
            url="https://techcrunch.com/quinyx-ai",
            domain="techcrunch.com",
            snippet="Quinyx launched AI features.",
            score=0.9,
        )
    ]

    with patch("app.searcher.pipeline.generate_queries_for_company", return_value=fake_queries), \
         patch("app.searcher.pipeline.search_tavily", return_value=fake_results), \
         patch("app.searcher.pipeline.fetch_url") as mock_fetch, \
         patch("app.searcher.pipeline.extract_content") as mock_extract, \
         patch("app.searcher.pipeline.analyse_document"):

        mock_fetch.return_value = MagicMock(html="<p>content</p>", final_url="https://techcrunch.com/quinyx-ai", status_code=200)
        mock_extract.return_value = MagicMock(title="Quinyx AI news", markdown="# Quinyx AI", content_hash="abc123")

        result = run_search_for_company(company, db_session)

    assert result["queries_generated"] == 1
    assert result["results_found"] == 1
    assert result["documents_created"] >= 1

    from app.models.search_run import SearchRun
    run = db_session.query(SearchRun).first()
    assert run is not None
    assert run.status == SearchRunStatus.done

    from app.models.search_result import SearchResult
    sr = db_session.query(SearchResult).first()
    assert sr is not None
    assert sr.processing_status == SearchResultStatus.fetched


def test_run_search_skips_low_relevance_result(db_session, company):
    fake_queries = [QuerySpec(query_text="Quinyx pricing", search_intent="pricing")]
    fake_results = [
        TavilyResult(
            title="Old news",
            url="https://example.com/old",
            domain="example.com",
            snippet="Nothing relevant.",
            score=0.2,  # below default threshold of 0.5
        )
    ]

    with patch("app.searcher.pipeline.generate_queries_for_company", return_value=fake_queries), \
         patch("app.searcher.pipeline.search_tavily", return_value=fake_results), \
         patch("app.searcher.pipeline.analyse_document") as mock_analyse:

        result = run_search_for_company(company, db_session)

    mock_analyse.assert_not_called()

    from app.models.search_result import SearchResult
    sr = db_session.query(SearchResult).first()
    assert sr.processing_status == SearchResultStatus.skipped


def test_run_search_creates_source_candidate_for_new_domain(db_session, company):
    fake_queries = [QuerySpec(query_text="Quinyx partner", search_intent="partnership")]
    fake_results = [
        TavilyResult(
            title="News about Quinyx",
            url="https://newsite.com/quinyx-partner",
            domain="newsite.com",
            snippet="Quinyx partners with X.",
            score=0.8,
        )
    ]

    with patch("app.searcher.pipeline.generate_queries_for_company", return_value=fake_queries), \
         patch("app.searcher.pipeline.search_tavily", return_value=fake_results), \
         patch("app.searcher.pipeline.fetch_url") as mock_fetch, \
         patch("app.searcher.pipeline.extract_content") as mock_extract, \
         patch("app.searcher.pipeline.analyse_document"):

        mock_fetch.return_value = MagicMock(html="<p>content</p>", final_url="https://newsite.com/quinyx-partner", status_code=200)
        mock_extract.return_value = MagicMock(title="News", markdown="# News", content_hash="xyz789")

        run_search_for_company(company, db_session)

    from app.models.source_candidate import SourceCandidate
    candidate = db_session.query(SourceCandidate).filter_by(domain="newsite.com").first()
    assert candidate is not None
    assert candidate.status == SourceCandidateStatus.candidate
    assert candidate.company_id == company.id
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_searcher_pipeline.py -v
```

Expected: `ImportError` — `app.searcher.pipeline` doesn't exist.

- [ ] **Step 3: Implement `searcher/pipeline.py`**

```python
# backend/app/searcher/pipeline.py
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config import settings
from app.models.company import Company
from app.models.context import InternalCompanyContext
from app.models.document import Document
from app.models.search_query import SearchQuery
from app.models.search_result import SearchResult, SearchResultStatus
from app.models.search_run import SearchRun, SearchRunStatus
from app.models.source import Source, SourceType
from app.models.source_candidate import SourceCandidate, SourceCandidateStatus
from app.analyser.pipeline import analyse_document
from app.crawler.extractor import extract_content
from app.crawler.fetcher import fetch_url
from app.searcher.client import search_tavily
from app.searcher.query_generator import generate_queries_for_company, generate_trend_queries


def _get_or_create_search_inbox_source(company: Company, db: Session) -> Source:
    inbox_url = f"search://{company.id}"
    source = db.query(Source).filter(Source.url == inbox_url).first()
    if not source:
        source = Source(
            company_id=company.id,
            url=inbox_url,
            label="Web Search Inbox",
            source_type=SourceType.news,
            is_active=False,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    return source


def _domain_has_active_source(domain: str, db: Session) -> bool:
    sources = db.query(Source).filter(Source.is_active == True).all()  # noqa: E712
    for s in sources:
        parsed = urlparse(s.url)
        if parsed.netloc.lstrip("www.") == domain:
            return True
    return False


def _domain_has_candidate(domain: str, db: Session) -> bool:
    return db.query(SourceCandidate).filter(SourceCandidate.domain == domain).first() is not None


def _get_context(db: Session) -> Dict:
    ctx = db.query(InternalCompanyContext).first()
    if not ctx:
        return {}
    return {
        "target_industries": ctx.target_industries or [],
        "target_segments": ctx.target_segments or [],
        "core_capabilities": ctx.core_capabilities or [],
        "strategic_priorities": ctx.strategic_priorities or [],
        "differentiators": ctx.differentiators or [],
        "relevant_competitive_areas": ctx.relevant_competitive_areas or [],
        "non_focus_areas": ctx.non_focus_areas or [],
    }


def _process_result(
    tavily_result,
    search_run: SearchRun,
    company: Company,
    inbox_source: Source,
    db: Session,
) -> SearchResult:
    sr = SearchResult(
        search_run_id=search_run.id,
        title=tavily_result.title,
        url=tavily_result.url,
        domain=tavily_result.domain,
        snippet=tavily_result.snippet,
        relevance_score=tavily_result.score,
        processing_status=SearchResultStatus.pending,
    )
    db.add(sr)
    db.flush()

    if tavily_result.score < settings.search_relevance_threshold:
        sr.processing_status = SearchResultStatus.skipped
        db.commit()
        return sr

    existing_doc = db.query(Document).filter(Document.url == tavily_result.url).first()
    if existing_doc:
        sr.linked_document_id = existing_doc.id
        sr.processing_status = SearchResultStatus.fetched
        db.commit()
        return sr

    fetch_result = fetch_url(tavily_result.url)
    if not fetch_result or not fetch_result.html:
        sr.processing_status = SearchResultStatus.error
        db.commit()
        return sr

    extraction = extract_content(fetch_result.html, fetch_result.final_url)
    existing_hash = db.query(Document).filter(Document.content_hash == extraction.content_hash).first()
    if existing_hash:
        sr.linked_document_id = existing_hash.id
        sr.processing_status = SearchResultStatus.fetched
        db.commit()
        return sr

    doc = Document(
        source_id=inbox_source.id,
        url=fetch_result.final_url,
        title=extraction.title,
        content_markdown=extraction.markdown,
        content_hash=extraction.content_hash,
        from_search=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        analyse_document(doc, company.id, db)
    except Exception:
        pass

    sr.linked_document_id = doc.id
    sr.processing_status = SearchResultStatus.fetched
    db.commit()

    if not _domain_has_active_source(tavily_result.domain, db) and not _domain_has_candidate(tavily_result.domain, db):
        candidate = SourceCandidate(
            url=tavily_result.url,
            domain=tavily_result.domain,
            title=tavily_result.title,
            snippet=tavily_result.snippet,
            found_via_query=search_run.query.query_text if search_run.query else None,
            company_id=company.id,
            source_type_guess=SourceType.news,
            relevance_score=tavily_result.score,
            status=SourceCandidateStatus.candidate,
        )
        db.add(candidate)
        db.commit()

    return sr


def run_search_for_company(company: Company, db: Session) -> Dict[str, Any]:
    context = _get_context(db)
    queries = generate_queries_for_company(
        company_name=company.name,
        company_type=company.type.value if hasattr(company.type, "value") else str(company.type),
        context=context,
    )

    inbox_source = _get_or_create_search_inbox_source(company, db)
    total_results = 0
    total_docs = 0

    for q in queries:
        sq = SearchQuery(
            query_text=q.query_text,
            company_id=company.id,
            search_intent=q.search_intent,
        )
        db.add(sq)
        db.commit()
        db.refresh(sq)

        run = SearchRun(search_query_id=sq.id, status=SearchRunStatus.running)
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            tavily_results = search_tavily(q.query_text, api_key=settings.tavily_api_key)
            run.result_count = len(tavily_results)
            total_results += len(tavily_results)

            for tr in tavily_results:
                sr = _process_result(tr, run, company, inbox_source, db)
                if sr.processing_status == SearchResultStatus.fetched and sr.linked_document_id:
                    existing = db.query(Document).filter(Document.id == sr.linked_document_id).first()
                    if existing and existing.from_search:
                        total_docs += 1

            run.status = SearchRunStatus.done
        except Exception as e:
            run.status = SearchRunStatus.error
            run.error_message = str(e)[:1000]

        db.commit()

    return {
        "company_id": company.id,
        "queries_generated": len(queries),
        "results_found": total_results,
        "documents_created": total_docs,
    }


def run_search_all_companies(db: Session) -> Dict[str, Any]:
    companies = db.query(Company).all()
    results = []
    for company in companies:
        result = run_search_for_company(company, db)
        results.append(result)

    ctx = _get_context(db)
    competitive_areas = ctx.get("relevant_competitive_areas", [])
    if competitive_areas:
        trend_queries = generate_trend_queries(competitive_areas)
        for q in trend_queries:
            sq = SearchQuery(
                query_text=q.query_text,
                company_id=None,
                search_intent=q.search_intent,
            )
            db.add(sq)
            db.commit()
            db.refresh(sq)

            run = SearchRun(search_query_id=sq.id, status=SearchRunStatus.running)
            db.add(run)
            db.commit()
            db.refresh(run)

            try:
                tavily_results = search_tavily(q.query_text, api_key=settings.tavily_api_key)
                run.result_count = len(tavily_results)
                for tr in tavily_results:
                    sr = SearchResult(
                        search_run_id=run.id,
                        title=tr.title,
                        url=tr.url,
                        domain=tr.domain,
                        snippet=tr.snippet,
                        relevance_score=tr.score,
                        processing_status=SearchResultStatus.skipped,
                    )
                    db.add(sr)
                    if not _domain_has_active_source(tr.domain, db) and not _domain_has_candidate(tr.domain, db):
                        candidate = SourceCandidate(
                            url=tr.url,
                            domain=tr.domain,
                            title=tr.title,
                            snippet=tr.snippet,
                            found_via_query=q.query_text,
                            company_id=None,
                            source_type_guess=SourceType.news,
                            relevance_score=tr.score,
                            status=SourceCandidateStatus.candidate,
                        )
                        db.add(candidate)
                db.commit()
                run.status = SearchRunStatus.done
            except Exception as e:
                run.status = SearchRunStatus.error
                run.error_message = str(e)[:1000]
            db.commit()

    return {"companies_searched": len(companies), "results": results}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_searcher_pipeline.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/searcher/pipeline.py backend/tests/test_searcher_pipeline.py
rtk git commit -m "feat: add searcher pipeline with source candidate detection"
```

---

## Task 8: Search Router

**Files:**
- Create: `backend/app/routers/search.py`
- Create: `backend/tests/test_search_router.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_search_router.py
from unittest.mock import patch


def test_run_search_all_returns_results(client, db_session):
    mock_result = {"companies_searched": 0, "results": []}
    with patch("app.routers.search.run_search_all_companies", return_value=mock_result):
        resp = client.post("/api/search/run")
    assert resp.status_code == 200
    data = resp.json()
    assert "companies_searched" in data


def test_run_search_for_company_returns_404_if_not_found(client):
    resp = client.post("/api/search/run/nonexistent-id")
    assert resp.status_code == 404


def test_run_search_for_company_returns_result(client, db_session):
    from app.models.company import Company, CompanyType
    company = Company(name="TestCo", slug="testco", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    mock_result = {"company_id": company.id, "queries_generated": 2, "results_found": 5, "documents_created": 1}
    with patch("app.routers.search.run_search_for_company", return_value=mock_result):
        resp = client.post(f"/api/search/run/{company.id}")
    assert resp.status_code == 200
    assert resp.json()["queries_generated"] == 2


def test_list_search_runs_returns_empty(client):
    resp = client.get("/api/search/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_search_results_returns_empty(client):
    resp = client.get("/api/search/results")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_source_candidates_returns_empty(client):
    resp = client.get("/api/source-candidates")
    assert resp.status_code == 200
    assert resp.json() == []


def test_approve_source_candidate(client, db_session):
    from app.models.company import Company, CompanyType
    from app.models.source_candidate import SourceCandidate, SourceCandidateStatus

    company = Company(name="TestCo2", slug="testco2", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    candidate = SourceCandidate(
        url="https://newssite.com/article",
        domain="newssite.com",
        title="News Site",
        snippet="A news site about WFM.",
        company_id=company.id,
        relevance_score=0.8,
        status=SourceCandidateStatus.candidate,
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    resp = client.post(
        f"/api/source-candidates/{candidate.id}/approve",
        json={"label": "News Site", "source_type": "news"},
    )
    assert resp.status_code == 200

    db_session.refresh(candidate)
    assert candidate.status == SourceCandidateStatus.monitored

    from app.models.source import Source
    source = db_session.query(Source).filter(Source.url == "https://newssite.com/article").first()
    assert source is not None
    assert source.label == "News Site"


def test_reject_source_candidate(client, db_session):
    from app.models.source_candidate import SourceCandidate, SourceCandidateStatus

    candidate = SourceCandidate(
        url="https://spam.com/article",
        domain="spam.com",
        title="Spam",
        snippet="Irrelevant.",
        relevance_score=0.3,
        status=SourceCandidateStatus.candidate,
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    resp = client.post(f"/api/source-candidates/{candidate.id}/reject")
    assert resp.status_code == 200

    db_session.refresh(candidate)
    assert candidate.status == SourceCandidateStatus.rejected
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_search_router.py -v
```

Expected: errors about missing router (404s or ImportError).

- [ ] **Step 3: Implement `routers/search.py`**

```python
# backend/app/routers/search.py
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.company import Company
from app.models.search_run import SearchRun
from app.models.search_result import SearchResult
from app.models.source import Source
from app.models.source_candidate import SourceCandidate, SourceCandidateStatus
from app.schemas.search import SearchRunRead, SearchResultRead, SourceCandidateRead, SourceCandidateApprove
from app.searcher.pipeline import run_search_all_companies, run_search_for_company

router = APIRouter()


@router.post("/run")
def search_run_all(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return run_search_all_companies(db)


@router.post("/run/{company_id}")
def search_run_company(company_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return run_search_for_company(company, db)


@router.get("/runs", response_model=List[SearchRunRead])
def list_search_runs(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SearchRun).options(selectinload(SearchRun.query))
    if company_id:
        q = q.join(SearchRun.query).filter(SearchRun.query.has(company_id=company_id))
    return q.order_by(SearchRun.executed_at.desc()).limit(100).all()


@router.get("/results", response_model=List[SearchResultRead])
def list_search_results(
    run_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SearchResult)
    if run_id:
        q = q.filter(SearchResult.search_run_id == run_id)
    return q.order_by(SearchResult.discovered_at.desc()).limit(200).all()


@router.get("/source-candidates", response_model=List[SourceCandidateRead])
def list_source_candidates(
    status: Optional[str] = None,
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SourceCandidate)
    if status:
        q = q.filter(SourceCandidate.status == status)
    if company_id:
        q = q.filter(SourceCandidate.company_id == company_id)
    return q.order_by(SourceCandidate.created_at.desc()).all()


@router.post("/source-candidates/{candidate_id}/approve")
def approve_source_candidate(
    candidate_id: str,
    body: SourceCandidateApprove,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    candidate = db.query(SourceCandidate).filter(SourceCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    source = Source(
        company_id=candidate.company_id,
        url=candidate.url,
        label=body.label or candidate.title,
        source_type=body.source_type,
        is_active=True,
    )
    db.add(source)

    candidate.status = SourceCandidateStatus.monitored
    db.commit()

    return {"status": "approved", "source_id": source.id}


@router.post("/source-candidates/{candidate_id}/reject")
def reject_source_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    candidate = db.query(SourceCandidate).filter(SourceCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.status = SourceCandidateStatus.rejected
    db.commit()
    return {"status": "rejected"}
```

- [ ] **Step 4: Run tests to verify they fail (router not mounted yet)**

```bash
python -m pytest tests/test_search_router.py -v
```

Expected: 404 errors because router is not mounted in `main.py` yet.

- [ ] **Step 5: Mount router in `main.py`**

Edit `backend/app/main.py`. Add the search router import to the existing import block:

```python
from app.routers import (
    companies,
    sources,
    documents,
    signals,
    digests,
    context,
    crawl,
    discovered_pages,
    search,
)  # noqa: E402
```

Add mount after existing routers:
```python
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(search.router, prefix="/api/source-candidates", tags=["source-candidates"])
```

Wait — the source-candidates endpoints are under `/api/source-candidates` but defined in the search router under `/source-candidates/{id}/approve`. We need to mount them separately or restructure. Use this approach instead — split into two routers in the same file:

In `backend/app/routers/search.py`, define two separate routers:

```python
# At the top of routers/search.py, replace `router = APIRouter()` with:
search_router = APIRouter()
candidates_router = APIRouter()
```

Then update all `@router.` decorators: search endpoints use `@search_router.`, candidate endpoints use `@candidates_router.`. Update the `list_source_candidates` route path from `/source-candidates/...` to just `/` and the approve/reject to `/{candidate_id}/approve` and `/{candidate_id}/reject` (already correct).

The final `backend/app/routers/search.py` with two routers:

```python
# backend/app/routers/search.py
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.company import Company
from app.models.search_run import SearchRun
from app.models.search_result import SearchResult
from app.models.source import Source
from app.models.source_candidate import SourceCandidate, SourceCandidateStatus
from app.schemas.search import SearchRunRead, SearchResultRead, SourceCandidateRead, SourceCandidateApprove
from app.searcher.pipeline import run_search_all_companies, run_search_for_company

search_router = APIRouter()
candidates_router = APIRouter()


@search_router.post("/run")
def search_run_all(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return run_search_all_companies(db)


@search_router.post("/run/{company_id}")
def search_run_company(company_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return run_search_for_company(company, db)


@search_router.get("/runs", response_model=List[SearchRunRead])
def list_search_runs(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SearchRun).options(selectinload(SearchRun.query))
    if company_id:
        q = q.join(SearchRun.query).filter(SearchRun.query.has(company_id=company_id))
    return q.order_by(SearchRun.executed_at.desc()).limit(100).all()


@search_router.get("/results", response_model=List[SearchResultRead])
def list_search_results(
    run_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SearchResult)
    if run_id:
        q = q.filter(SearchResult.search_run_id == run_id)
    return q.order_by(SearchResult.discovered_at.desc()).limit(200).all()


@candidates_router.get("/", response_model=List[SourceCandidateRead])
def list_source_candidates(
    status: Optional[str] = None,
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SourceCandidate)
    if status:
        q = q.filter(SourceCandidate.status == status)
    if company_id:
        q = q.filter(SourceCandidate.company_id == company_id)
    return q.order_by(SourceCandidate.created_at.desc()).all()


@candidates_router.post("/{candidate_id}/approve")
def approve_source_candidate(
    candidate_id: str,
    body: SourceCandidateApprove,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    candidate = db.query(SourceCandidate).filter(SourceCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    source = Source(
        company_id=candidate.company_id,
        url=candidate.url,
        label=body.label or candidate.title,
        source_type=body.source_type,
        is_active=True,
    )
    db.add(source)
    candidate.status = SourceCandidateStatus.monitored
    db.commit()
    return {"status": "approved", "source_id": source.id}


@candidates_router.post("/{candidate_id}/reject")
def reject_source_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    candidate = db.query(SourceCandidate).filter(SourceCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.status = SourceCandidateStatus.rejected
    db.commit()
    return {"status": "rejected"}
```

- [ ] **Step 6: Update `main.py` to mount both routers**

```python
# backend/app/main.py — update the import block and router mounting

from app.routers import (
    companies,
    sources,
    documents,
    signals,
    digests,
    context,
    crawl,
    discovered_pages,
)  # noqa: E402
from app.routers.search import search_router, candidates_router  # noqa: E402

app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(digests.router, prefix="/api/digests", tags=["digests"])
app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(
    discovered_pages.router, prefix="/api/discovered-pages", tags=["discovered-pages"]
)
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(candidates_router, prefix="/api/source-candidates", tags=["source-candidates"])
```

Also update the test file to use the correct paths — `test_list_source_candidates_returns_empty` hits `/api/source-candidates`, which maps to `candidates_router` at `/`. The test is already correct.

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/test_search_router.py -v
```

Expected: all 8 tests PASSED.

- [ ] **Step 8: Run full test suite to check for regressions**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass (no regressions from model/main.py changes).

- [ ] **Step 9: Commit**

```bash
rtk git add backend/app/routers/search.py backend/app/main.py \
  backend/tests/test_search_router.py
rtk git commit -m "feat: add search router with run, list runs/results, source candidate approve/reject"
```

---

## Task 9: Frontend Types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Append new types to `frontend/src/types/index.ts`**

Add at the end of the file:

```typescript
// --- Search / Source Candidates ---

export type SearchRunStatus = 'pending' | 'running' | 'done' | 'error';
export type SearchResultStatus = 'pending' | 'fetched' | 'skipped' | 'error';
export type SourceCandidateStatus = 'candidate' | 'approved' | 'rejected' | 'monitored';

export interface SearchQuery {
  id: string;
  query_text: string;
  company_id: string | null;
  topic: string | null;
  search_intent: string;
  generated_at: string;
}

export interface SearchRun {
  id: string;
  search_query_id: string;
  executed_at: string;
  status: SearchRunStatus;
  result_count: number | null;
  error_message: string | null;
  query: SearchQuery | null;
}

export interface SearchResult {
  id: string;
  search_run_id: string;
  title: string | null;
  url: string;
  domain: string | null;
  snippet: string | null;
  discovered_at: string;
  relevance_score: number | null;
  processing_status: SearchResultStatus;
  linked_document_id: string | null;
}

export interface SourceCandidate {
  id: string;
  url: string;
  domain: string;
  title: string | null;
  snippet: string | null;
  found_via_query: string | null;
  company_id: string | null;
  source_type_guess: SourceType | null;
  relevance_score: number | null;
  status: SourceCandidateStatus;
  created_at: string;
}

export interface SourceCandidateApprove {
  label?: string;
  source_type: SourceType;
}

export interface SearchRunResult {
  companies_searched: number;
  results: unknown[];
}
```

Also update the existing `Document` interface to include `from_search`:

```typescript
export interface Document {
  id: string;
  source_id: string;
  url: string;
  title: string | null;
  content_markdown: string | null;
  published_at: string | null;
  crawled_at: string;
  content_hash: string | null;
  is_analysed: boolean;
  from_search: boolean;
}
```

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/src/types/index.ts
rtk git commit -m "feat: add search/source-candidate TypeScript types"
```

---

## Task 10: Frontend Hooks

**Files:**
- Create: `frontend/src/hooks/useSearch.ts`

- [ ] **Step 1: Create `useSearch.ts`**

```typescript
// frontend/src/hooks/useSearch.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type {
  SearchRun,
  SearchResult,
  SourceCandidate,
  SearchRunResult,
  SourceCandidateApprove,
  SourceType,
} from '../types';

export function useRunSearchAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<SearchRunResult>('/search/run'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-runs'] });
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useRunSearchForCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (companyId: string) => apiPost<SearchRunResult>(`/search/run/${companyId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-runs'] });
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}

export function useSearchRuns(companyId?: string) {
  return useQuery({
    queryKey: ['search-runs', companyId],
    queryFn: () => {
      const params = companyId ? `?company_id=${companyId}` : '';
      return apiGet<SearchRun[]>(`/search/runs${params}`);
    },
  });
}

export function useSearchResults(runId?: string) {
  return useQuery({
    queryKey: ['search-results', runId],
    queryFn: () => {
      const params = runId ? `?run_id=${runId}` : '';
      return apiGet<SearchResult[]>(`/search/results${params}`);
    },
    enabled: !!runId,
  });
}

export function useSourceCandidates(status?: string, companyId?: string) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (companyId) params.set('company_id', companyId);
  const query = params.toString();

  return useQuery({
    queryKey: ['source-candidates', status, companyId],
    queryFn: () => apiGet<SourceCandidate[]>(`/source-candidates${query ? `?${query}` : ''}`),
  });
}

export function useApproveCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SourceCandidateApprove }) =>
      apiPost<{ status: string; source_id: string }>(`/source-candidates/${id}/approve`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
      qc.invalidateQueries({ queryKey: ['sources'] });
    },
  });
}

export function useRejectCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiPost<{ status: string }>(`/source-candidates/${id}/reject`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
    },
  });
}
```

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/src/hooks/useSearch.ts
rtk git commit -m "feat: add search/source-candidate React Query hooks"
```

---

## Task 11: Frontend Search Page

**Files:**
- Create: `frontend/src/pages/SearchPage.tsx`

- [ ] **Step 1: Read an existing page for style reference**

Read `frontend/src/pages/SourcesAdmin.tsx` to understand the dark-theme class conventions used (dark-card, dark-border, dark-text, dark-muted, dark-accent, etc.) before implementing.

- [ ] **Step 2: Create `SearchPage.tsx`**

```tsx
// frontend/src/pages/SearchPage.tsx
import { useState } from 'react';
import { Search, CheckCircle, XCircle, ExternalLink, ChevronDown, ChevronRight } from 'lucide-react';
import {
  useRunSearchAll,
  useSearchRuns,
  useSearchResults,
  useSourceCandidates,
  useApproveCandidate,
  useRejectCandidate,
} from '../hooks/useSearch';
import type { SearchRun, SourceCandidate, SourceType } from '../types';

type Tab = 'runs' | 'candidates';

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    done: 'bg-green-900/40 text-green-400',
    running: 'bg-yellow-900/40 text-yellow-400',
    error: 'bg-red-900/40 text-red-400',
    pending: 'bg-gray-700 text-gray-400',
    fetched: 'bg-blue-900/40 text-blue-400',
    skipped: 'bg-gray-700 text-gray-400',
    candidate: 'bg-yellow-900/40 text-yellow-400',
    approved: 'bg-green-900/40 text-green-400',
    rejected: 'bg-red-900/40 text-red-400',
    monitored: 'bg-blue-900/40 text-blue-400',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${colors[status] ?? 'bg-gray-700 text-gray-400'}`}>
      {status}
    </span>
  );
}

function SearchRunRow({ run }: { run: SearchRun }) {
  const [expanded, setExpanded] = useState(false);
  const { data: results } = useSearchResults(expanded ? run.id : undefined);

  return (
    <div className="border border-dark-border rounded mb-2">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-dark-bg transition-colors text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={16} className="text-dark-muted" /> : <ChevronRight size={16} className="text-dark-muted" />}
        <span className="text-sm text-dark-text flex-1">
          {run.query?.query_text ?? run.search_query_id}
        </span>
        <span className="text-xs text-dark-muted mr-3">
          {run.query?.search_intent}
        </span>
        <span className="text-xs text-dark-muted mr-3">
          {run.result_count ?? 0} results
        </span>
        <StatusBadge status={run.status} />
        <span className="text-xs text-dark-muted ml-3">
          {new Date(run.executed_at).toLocaleDateString()}
        </span>
      </button>

      {expanded && results && (
        <div className="border-t border-dark-border divide-y divide-dark-border">
          {results.length === 0 && (
            <p className="px-6 py-3 text-sm text-dark-muted">No results</p>
          )}
          {results.map(r => (
            <div key={r.id} className="px-6 py-2 flex items-start gap-4">
              <StatusBadge status={r.processing_status} />
              <div className="flex-1 min-w-0">
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-dark-accent hover:underline flex items-center gap-1"
                >
                  {r.title || r.url}
                  <ExternalLink size={12} />
                </a>
                {r.snippet && (
                  <p className="text-xs text-dark-muted mt-0.5 line-clamp-2">{r.snippet}</p>
                )}
              </div>
              {r.relevance_score != null && (
                <span className="text-xs text-dark-muted shrink-0">
                  {(r.relevance_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ApproveCandidateDialog({
  candidate,
  onClose,
}: {
  candidate: SourceCandidate;
  onClose: () => void;
}) {
  const [label, setLabel] = useState(candidate.title ?? candidate.domain);
  const [sourceType, setSourceType] = useState<SourceType>(
    (candidate.source_type_guess as SourceType) ?? 'news'
  );
  const approve = useApproveCandidate();

  function handleApprove() {
    approve.mutate(
      { id: candidate.id, body: { label, source_type: sourceType } },
      { onSuccess: onClose }
    );
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-dark-card border border-dark-border rounded-lg p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold text-dark-text mb-4">Approve Source Candidate</h2>
        <p className="text-sm text-dark-muted mb-4">{candidate.domain}</p>

        <div className="mb-4">
          <label className="block text-sm text-dark-muted mb-1">Label</label>
          <input
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-dark-text text-sm"
            value={label}
            onChange={e => setLabel(e.target.value)}
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm text-dark-muted mb-1">Source Type</label>
          <select
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-dark-text text-sm"
            value={sourceType}
            onChange={e => setSourceType(e.target.value as SourceType)}
          >
            {(['news', 'blog', 'product', 'press', 'jobs'] as SourceType[]).map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-dark-muted hover:text-dark-text transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            disabled={approve.isPending}
            className="px-4 py-2 text-sm bg-dark-accent text-white rounded hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {approve.isPending ? 'Approving…' : 'Approve & Add Source'}
          </button>
        </div>
      </div>
    </div>
  );
}

function CandidatesTab() {
  const [statusFilter, setStatusFilter] = useState<string>('candidate');
  const [approving, setApproving] = useState<SourceCandidate | null>(null);
  const { data: candidates, isLoading } = useSourceCandidates(statusFilter || undefined);
  const reject = useRejectCandidate();

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {['candidate', 'approved', 'rejected', ''].map(s => (
          <button
            key={s || 'all'}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              statusFilter === s
                ? 'bg-dark-accent/20 text-dark-accent border border-dark-accent/40'
                : 'text-dark-muted hover:text-dark-text border border-dark-border'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-dark-muted text-sm">Loading…</p>}
      {!isLoading && (!candidates || candidates.length === 0) && (
        <p className="text-dark-muted text-sm">No candidates found.</p>
      )}

      <div className="space-y-2">
        {candidates?.map(c => (
          <div key={c.id} className="bg-dark-card border border-dark-border rounded p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-dark-text">{c.domain}</span>
                  <StatusBadge status={c.status} />
                  {c.relevance_score != null && (
                    <span className="text-xs text-dark-muted">
                      {(c.relevance_score * 100).toFixed(0)}% relevance
                    </span>
                  )}
                </div>
                {c.title && <p className="text-xs text-dark-muted mb-1">{c.title}</p>}
                {c.snippet && (
                  <p className="text-xs text-dark-muted line-clamp-2">{c.snippet}</p>
                )}
                {c.found_via_query && (
                  <p className="text-xs text-dark-muted/60 mt-1">via: {c.found_via_query}</p>
                )}
              </div>
              {c.status === 'candidate' && (
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => setApproving(c)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-green-900/30 text-green-400 border border-green-800/50 rounded hover:bg-green-900/50 transition-colors"
                  >
                    <CheckCircle size={13} />
                    Approve
                  </button>
                  <button
                    onClick={() => reject.mutate(c.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-900/30 text-red-400 border border-red-800/50 rounded hover:bg-red-900/50 transition-colors"
                  >
                    <XCircle size={13} />
                    Reject
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {approving && (
        <ApproveCandidateDialog candidate={approving} onClose={() => setApproving(null)} />
      )}
    </div>
  );
}

export default function SearchPage() {
  const [tab, setTab] = useState<Tab>('runs');
  const runSearch = useRunSearchAll();
  const { data: runs, isLoading: runsLoading } = useSearchRuns();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-dark-text">Web Search</h1>
          <p className="text-dark-muted text-sm mt-1">AI-driven search for news, reports, and new sources</p>
        </div>
        <button
          onClick={() => runSearch.mutate()}
          disabled={runSearch.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-dark-accent text-white rounded hover:opacity-90 disabled:opacity-50 transition-opacity text-sm"
        >
          <Search size={16} />
          {runSearch.isPending ? 'Searching…' : 'Search Run starten'}
        </button>
      </div>

      <div className="flex gap-1 mb-6 border-b border-dark-border">
        {(['runs', 'candidates'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-dark-accent text-dark-accent'
                : 'border-transparent text-dark-muted hover:text-dark-text'
            }`}
          >
            {t === 'runs' ? 'Search Runs' : 'Source Candidates'}
          </button>
        ))}
      </div>

      {tab === 'runs' && (
        <div>
          {runsLoading && <p className="text-dark-muted text-sm">Loading…</p>}
          {!runsLoading && (!runs || runs.length === 0) && (
            <p className="text-dark-muted text-sm">No search runs yet. Click "Search Run starten" to begin.</p>
          )}
          {runs?.map(run => <SearchRunRow key={run.id} run={run} />)}
        </div>
      )}

      {tab === 'candidates' && <CandidatesTab />}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/pages/SearchPage.tsx
rtk git commit -m "feat: add SearchPage with run history and source candidate review"
```

---

## Task 12: Wire Search into App Router and Navigation

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add route to `App.tsx`**

Add import at top of file:
```typescript
import SearchPage from './pages/SearchPage';
```

Add route inside the protected `<Route>` block, after the `digest` route:
```tsx
<Route path="search" element={<SearchPage />} />
```

- [ ] **Step 2: Add nav item to `Layout.tsx`**

Add `Search` icon import (it's already in lucide-react). Update the `navItems` array to include the Search entry between Weekly Digest and Sources Admin:

```typescript
import {
  BarChart3,
  Users,
  TrendingUp,
  Calendar,
  Search,
  Settings,
  Globe,
  LogOut,
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/competitors', label: 'Competitors', icon: Users },
  { to: '/trends', label: 'Market Trends', icon: TrendingUp },
  { to: '/digest', label: 'Weekly Digest', icon: Calendar },
  { to: '/search', label: 'Search', icon: Search },
  { to: '/admin/sources', label: 'Sources Admin', icon: Settings },
  { to: '/context', label: 'Company Context', icon: Globe },
];
```

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/App.tsx frontend/src/components/Layout.tsx
rtk git commit -m "feat: add Search route and nav item"
```

---

## Task 13: Dashboard Signal Badge (from_search)

**Files:**
- Modify: `frontend/src/components/SignalCard.tsx`

- [ ] **Step 1: Read `SignalCard.tsx`**

Read `frontend/src/components/SignalCard.tsx` to understand its current structure and the Signal type it receives.

- [ ] **Step 2: Add from_search badge**

Signal has `document_id` but not `from_search` directly. The Signal type does not include `from_search`. Two options:
- Fetch the document per signal (expensive)
- Add `from_search` to the SignalRead schema on the backend and return it with signals

Use option B — extend the backend SignalRead schema to include `from_search` from the linked Document.

Read `backend/app/routers/signals.py` to see how signals are returned, then add `from_search` to the SignalRead schema and the query.

Read `backend/app/schemas/signal.py` to see the current SignalRead schema.

- [ ] **Step 3: Update backend `schemas/signal.py`**

After reading the file, add `from_search: bool = False` to `SignalRead`. This field must be populated by the router.

- [ ] **Step 4: Update `routers/signals.py`**

After reading the file, update the signal list query to join/load the Document and set `from_search` in the response. The easiest approach: after fetching signals, check `signal.document.from_search` (the relationship is already there via `selectinload(Signal.document)`).

Since Pydantic's `from_attributes=True` only reads from the ORM object, add a computed property or use a response model with a custom validator. Simplest: return a list of dicts manually.

Actually, the simplest approach: in `SignalRead`, add `from_search: bool = False`. In the router, after loading signals with their documents, create response dicts:

```python
def _signal_to_dict(signal) -> dict:
    d = {
        "id": signal.id,
        "document_id": signal.document_id,
        "company_id": signal.company_id,
        "title": signal.title,
        "signal_type": signal.signal_type,
        "topic": signal.topic,
        "summary": signal.summary,
        "why_it_matters": signal.why_it_matters,
        "relevance_score": signal.relevance_score,
        "confidence_score": signal.confidence_score,
        "source_url": signal.document.url if signal.document else None,
        "published_at": signal.published_at,
        "created_at": signal.created_at,
        "from_search": signal.document.from_search if signal.document else False,
    }
    return d
```

Then return `[_signal_to_dict(s) for s in signals]` from the list endpoint.

- [ ] **Step 5: Update `types/index.ts` Signal interface**

Add `from_search: boolean;` to the existing `Signal` interface.

- [ ] **Step 6: Update `SignalCard.tsx` to show badge**

After reading the file, add a small badge near the signal title or source URL line:

```tsx
{signal.from_search && (
  <span className="text-xs px-1.5 py-0.5 bg-purple-900/40 text-purple-400 rounded">
    Search
  </span>
)}
```

For crawled signals (from_search=false), show nothing (no badge needed — search badge alone provides distinction).

- [ ] **Step 7: Commit**

```bash
rtk git add backend/app/schemas/signal.py backend/app/routers/signals.py \
  frontend/src/types/index.ts frontend/src/components/SignalCard.tsx
rtk git commit -m "feat: add from_search badge to signal cards"
```

---

## Self-Review

**Spec coverage check:**

| Spec Requirement | Task |
|---|---|
| Suchläufe unabhängig vom Crawling | Task 7–8: separate /api/search/run endpoint |
| Suchtreffer wie Dokumente behandeln | Task 7: pipeline creates Document(from_search=True) |
| Speichern, deduplizieren, bewerten | Task 7: hash dedup + relevance_score threshold |
| Irrelevante Treffer herausfiltern | Task 7: score < threshold → skipped |
| KI-generierte Suchanfragen | Task 6: query_generator.py |
| Query Fan-Out / verschiedene Intents | Task 6: 8 queries per company, multiple intents |
| Trend-Queries | Task 7: run_search_all_companies calls generate_trend_queries |
| SearchQuery / SearchRun / SearchResult | Task 2: models |
| SourceCandidate mit status-Workflow | Task 2: model + Task 8: approve/reject |
| Document.from_search | Task 2: column added |
| Frontend Search Runs tab | Task 11 |
| Frontend Source Candidates tab | Task 11 |
| Approve → neue Source | Task 8: approve endpoint creates Source |
| Dashboard from_search badge | Task 13 |
| Relevanz gegen Company Context | Task 6: context passed to query generator prompt |

**Type consistency check:** `SourceCandidateApprove.source_type` is `SourceType` throughout. `SearchRunStatus`, `SearchResultStatus`, `SourceCandidateStatus` enums match between models and schemas. `from_search` is `bool`/`boolean` consistently.

**Placeholder check:** None found — all code blocks are complete.
