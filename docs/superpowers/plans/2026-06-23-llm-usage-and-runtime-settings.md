# LLM Token-Usage-Tracking & Runtime-Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track token usage/cost for every LLM call across all pipelines and surface it in a new admin page; add a DB-backed runtime-settings override for tuning fields so they survive redeploys and need no restart.

**Architecture:** Token usage is captured at the single LLM call chokepoint (`call_llm()` in `backend/app/analyser/client.py`) and written to a new `llm_calls` table; costs are computed live from an editable `llm_model_prices` table. Runtime settings are stored in a new `app_settings` key/value table and applied to the existing `settings` singleton via `setattr` at startup and on every admin edit — no existing call site changes.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest, SQLite (tests) — backend; React 18 + TypeScript + `@tanstack/react-query` + Tailwind — frontend. No new dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-23-llm-usage-and-runtime-settings-design.md`
- Backend tests MUST run inside Docker: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/<file> -v`
- Before starting, ensure the dev stack is up: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml up -d`
- Alembic migrations: revision IDs in this plan chain from current head `bc9bbf2a2b8b` (verified via `alembic heads`). Apply with `docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`.
- No secrets (`anthropic_api_key`, `opencode_api_key`, `tavily_api_key`, `database_url`, `auth_username`, `auth_password`, `app_base_url`) become DB-overridable — only the 14 tuning fields listed in the spec.
- Frontend type-check/build: `docker compose -f docker-compose.dev.yml exec frontend npm run build`

---

### Task 1: `LlmCall` and `LlmModelPrice` models + migration

**Files:**
- Create: `backend/app/models/llm_call.py`
- Create: `backend/app/models/llm_model_price.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/d4f8a1c2b3e5_add_llm_calls_and_llm_model_prices.py`
- Test: `backend/tests/test_llm_call_model.py`

**Interfaces:**
- Produces: `LlmCall(id, created_at, caller, provider, model, input_tokens, output_tokens, estimated, duration_ms)`, `LlmModelPrice(model, input_price_per_1m, output_price_per_1m, updated_at)` — consumed by Task 2 (writes) and Tasks 4–5 (reads/queries).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_llm_call_model.py
from app.models.llm_call import LlmCall
from app.models.llm_model_price import LlmModelPrice


def test_llm_call_round_trip(db_session):
    call = LlmCall(
        caller="analyser",
        provider="claude",
        model="claude-haiku-4-5-20251001",
        input_tokens=120,
        output_tokens=45,
        estimated=False,
        duration_ms=850,
    )
    db_session.add(call)
    db_session.commit()

    fetched = db_session.query(LlmCall).first()
    assert fetched.caller == "analyser"
    assert fetched.input_tokens == 120
    assert fetched.estimated is False
    assert fetched.created_at is not None


def test_llm_model_price_round_trip(db_session):
    price = LlmModelPrice(model="claude-haiku-4-5-20251001", input_price_per_1m=1.0, output_price_per_1m=5.0)
    db_session.add(price)
    db_session.commit()

    fetched = db_session.query(LlmModelPrice).filter(LlmModelPrice.model == "claude-haiku-4-5-20251001").first()
    assert fetched.output_price_per_1m == 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_call_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.llm_call'`

- [ ] **Step 3: Create the models**

```python
# backend/app/models/llm_call.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.database import Base


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    caller = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    estimated = Column(Boolean, nullable=False, default=False)
    duration_ms = Column(Integer, nullable=False, default=0)
```

```python
# backend/app/models/llm_model_price.py
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, String
from app.database import Base


class LlmModelPrice(Base):
    __tablename__ = "llm_model_prices"

    model = Column(String(100), primary_key=True)
    input_price_per_1m = Column(Float, nullable=False, default=0.0)
    output_price_per_1m = Column(Float, nullable=False, default=0.0)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

Register both in `backend/app/models/__init__.py` — add imports after the `ExternalCompanyView` import and append to `__all__`:

```python
from app.models.llm_call import LlmCall  # noqa: F401
from app.models.llm_model_price import LlmModelPrice  # noqa: F401
```

```python
    "ExternalCompanyView",
    "LlmCall",
    "LlmModelPrice",
]
```

- [ ] **Step 4: Write the migration**

```python
# backend/alembic/versions/d4f8a1c2b3e5_add_llm_calls_and_llm_model_prices.py
"""add llm_calls and llm_model_prices tables

Revision ID: d4f8a1c2b3e5
Revises: bc9bbf2a2b8b
Create Date: 2026-06-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4f8a1c2b3e5'
down_revision: Union[str, Sequence[str], None] = 'bc9bbf2a2b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('caller', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('estimated', sa.Boolean(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_calls_created_at', 'llm_calls', ['created_at'])
    op.create_index('ix_llm_calls_caller', 'llm_calls', ['caller'])
    op.create_index('ix_llm_calls_provider', 'llm_calls', ['provider'])
    op.create_index('ix_llm_calls_model', 'llm_calls', ['model'])

    op.create_table(
        'llm_model_prices',
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('input_price_per_1m', sa.Float(), nullable=False),
        sa.Column('output_price_per_1m', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('model'),
    )


def downgrade() -> None:
    op.drop_table('llm_model_prices')
    op.drop_index('ix_llm_calls_model', table_name='llm_calls')
    op.drop_index('ix_llm_calls_provider', table_name='llm_calls')
    op.drop_index('ix_llm_calls_caller', table_name='llm_calls')
    op.drop_index('ix_llm_calls_created_at', table_name='llm_calls')
    op.drop_table('llm_calls')
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_call_model.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Apply migration to dev DB**

Run: `docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`
Expected: output ends with `... -> d4f8a1c2b3e5, add llm_calls and llm_model_prices tables`

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/llm_call.py backend/app/models/llm_model_price.py backend/app/models/__init__.py backend/alembic/versions/d4f8a1c2b3e5_add_llm_calls_and_llm_model_prices.py backend/tests/test_llm_call_model.py
git commit -m "feat: add LlmCall and LlmModelPrice models for token usage tracking"
```

---

### Task 2: Capture exact token usage for Claude and Ollama in `call_llm`

**Files:**
- Modify: `backend/app/analyser/client.py`
- Test: `backend/tests/test_llm_call_tracking.py`

**Interfaces:**
- Consumes: `LlmCall` model from Task 1 (`backend/app/models/llm_call.py`).
- Produces: `call_llm(prompt: str, max_tokens: int = 1024, caller: str = "") -> str` (signature unchanged — all 16 existing call sites keep working). Internal helpers `_call_claude`, `_call_ollama`, `_call_opencode` now return `tuple[str, int, int, bool]` (`text, input_tokens, output_tokens, estimated`). New helper `_record_llm_call(caller, provider, model, input_tokens, output_tokens, estimated, duration_ms) -> None`, consumed by Task 3.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_llm_call_tracking.py
from unittest.mock import MagicMock, patch


def test_call_llm_claude_records_exact_token_usage(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "claude")
    monkeypatch.setattr(settings, "claude_model", "claude-haiku-4-5-20251001")

    mock_usage = MagicMock(input_tokens=120, output_tokens=45)
    mock_message = MagicMock(usage=mock_usage)
    mock_message.content = [MagicMock(text="hello world")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    client_module._anthropic_client = mock_client

    result = client_module.call_llm("prompt text", caller="analyser")

    assert result == "hello world"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].caller == "analyser"
    assert rows[0].provider == "claude"
    assert rows[0].model == "claude-haiku-4-5-20251001"
    assert rows[0].input_tokens == 120
    assert rows[0].output_tokens == 45
    assert rows[0].estimated is False


def test_call_llm_ollama_records_exact_token_usage(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_model", "llama3")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": "ollama reply",
        "prompt_eval_count": 80,
        "eval_count": 30,
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.post", return_value=mock_response):
        result = client_module.call_llm("prompt", caller="assessor")

    assert result == "ollama reply"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].provider == "ollama"
    assert rows[0].input_tokens == 80
    assert rows[0].output_tokens == 30
    assert rows[0].estimated is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_call_tracking.py -v`
Expected: FAIL — no `LlmCall` rows are created (current `call_llm` doesn't persist anything)

- [ ] **Step 3: Update `call_llm` and the provider helpers**

Replace the body of `backend/app/analyser/client.py` from `def call_llm` to the end of `_call_ollama` with:

```python
def call_llm(prompt: str, max_tokens: int = 1024, caller: str = "") -> str:
    label = caller or "unknown"
    logger.info("LLM call start [caller=%s provider=%s max_tokens=%d]", label, settings.llm_provider, max_tokens)
    t0 = time.monotonic()
    if settings.llm_provider == "ollama":
        text, input_tokens, output_tokens, estimated = _call_ollama(prompt, max_tokens=max_tokens)
        model = settings.ollama_model
    elif settings.llm_provider == "opencode":
        text, input_tokens, output_tokens, estimated = _call_opencode(prompt, max_tokens=max_tokens)
        model = settings.opencode_model
    else:
        text, input_tokens, output_tokens, estimated = _call_claude(prompt, max_tokens=max_tokens)
        model = settings.claude_model
    elapsed = time.monotonic() - t0
    logger.info("LLM call done [caller=%s duration=%.1fs chars=%d]", label, elapsed, len(text))
    _record_llm_call(
        caller=label,
        provider=settings.llm_provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated=estimated,
        duration_ms=int(elapsed * 1000),
    )
    return text


def _record_llm_call(
    caller: str, provider: str, model: str,
    input_tokens: int, output_tokens: int, estimated: bool, duration_ms: int,
) -> None:
    from app.database import SessionLocal
    from app.models.llm_call import LlmCall

    db = SessionLocal()
    try:
        db.add(LlmCall(
            caller=caller,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated=estimated,
            duration_ms=duration_ms,
        ))
        db.commit()
    except Exception:
        logger.warning("Failed to record LLM usage", exc_info=True)
        db.rollback()
    finally:
        db.close()


def _call_claude(prompt: str, max_tokens: int = 1024) -> tuple[str, int, int, bool]:
    client = _get_anthropic_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    return text, message.usage.input_tokens, message.usage.output_tokens, False
```

Leave `_call_opencode` untouched for now (Task 3 changes it). Replace `_call_ollama` with:

```python
def _call_ollama(prompt: str, max_tokens: int = 1024) -> tuple[str, int, int, bool]:
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
    data = response.json()
    return data["response"], data.get("prompt_eval_count", 0), data.get("eval_count", 0), False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_call_tracking.py tests/test_analyser_client.py -v`
Expected: PASS (existing `test_analyser_client.py` tests still pass since `_get_anthropic_client`/`_get_opencode_client` are untouched)

- [ ] **Step 5: Commit**

```bash
git add backend/app/analyser/client.py backend/tests/test_llm_call_tracking.py
git commit -m "feat: record exact token usage for Claude and Ollama LLM calls"
```

---

### Task 3: Capture token usage (or estimate) for Opencode in `call_llm`

**Files:**
- Modify: `backend/app/analyser/client.py`
- Modify: `backend/tests/test_llm_call_tracking.py`

**Interfaces:**
- Consumes: `_record_llm_call` from Task 2.
- Produces: `_call_opencode(prompt, max_tokens) -> tuple[str, int, int, bool]`, same contract as `_call_claude`/`_call_ollama`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_llm_call_tracking.py`:

```python
def test_call_llm_opencode_uses_exact_usage_when_available(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "opencode")
    monkeypatch.setattr(settings, "opencode_model", "qwen3.6-plus")

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="hi"))]
    mock_chunk.usage = MagicMock(prompt_tokens=50, completion_tokens=20)

    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = [mock_chunk]
    mock_stream.__exit__.return_value = False

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream
    client_module._opencode_client = mock_client

    result = client_module.call_llm("prompt", caller="synthesizer")

    assert result == "hi"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].input_tokens == 50
    assert rows[0].output_tokens == 20
    assert rows[0].estimated is False


def test_call_llm_opencode_estimates_tokens_when_usage_missing(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "opencode")
    monkeypatch.setattr(settings, "opencode_model", "qwen3.6-plus")

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="hi"))]
    mock_chunk.usage = None

    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = [mock_chunk]
    mock_stream.__exit__.return_value = False

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream
    client_module._opencode_client = mock_client

    result = client_module.call_llm("prompt", caller="synthesizer")

    assert result == "hi"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].estimated is True
    assert rows[0].input_tokens > 0
    assert rows[0].output_tokens > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_call_tracking.py -v -k opencode`
Expected: FAIL — current `_call_opencode` returns a plain `str`, not a 4-tuple, so `call_llm` (already updated in Task 2 to unpack 4 values for opencode) raises `TypeError: cannot unpack non-iterable str`

- [ ] **Step 3: Update `_call_opencode`**

Replace `_call_opencode` in `backend/app/analyser/client.py` with:

```python
def _call_opencode(prompt: str, max_tokens: int = 1024) -> tuple[str, int, int, bool]:
    """Stream the response to avoid Cloudflare's 120-second proxy timeout (error 524)."""
    client = _get_opencode_client()
    last_exc: Exception | None = None
    for attempt in range(_OPENCODE_RETRY_ATTEMPTS):
        if attempt > 0:
            wait = _OPENCODE_RETRY_BACKOFF * attempt
            logger.warning("opencode retry %d/%d after %ds", attempt + 1, _OPENCODE_RETRY_ATTEMPTS, wait)
            time.sleep(wait)
        try:
            chunks: list[str] = []
            usage = None
            with client.chat.completions.create(
                model=settings.opencode_model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                stream_options={"include_usage": True},
            ) as stream:
                for chunk in stream:
                    if getattr(chunk, "usage", None):
                        usage = chunk.usage
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if delta:
                        chunks.append(delta)
            text = "".join(chunks)
            if usage is not None:
                return text, usage.prompt_tokens, usage.completion_tokens, False
            input_tokens = max(len(prompt) // 4, 1)
            output_tokens = max(len(text) // 4, 1)
            return text, input_tokens, output_tokens, True
        except Exception as exc:
            last_exc = exc
            logger.warning("opencode attempt %d failed: %s", attempt + 1, exc)
    raise last_exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_call_tracking.py tests/test_analyser_client.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/analyser/client.py backend/tests/test_llm_call_tracking.py
git commit -m "feat: record exact or estimated token usage for Opencode LLM calls"
```

---

### Task 4: LLM usage summary, timeseries, and breakdown endpoints

**Files:**
- Create: `backend/app/schemas/llm_usage.py`
- Create: `backend/app/routers/llm_usage.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_llm_usage_router.py`

**Interfaces:**
- Consumes: `LlmCall`, `LlmModelPrice` models (Task 1).
- Produces: `GET /api/llm-usage/summary`, `GET /api/llm-usage/timeseries?days=N`, `GET /api/llm-usage/breakdown?days=N` — consumed by Task 8 (frontend API client).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_llm_usage_router.py
from datetime import datetime, timedelta, timezone

from app.models.llm_call import LlmCall
from app.models.llm_model_price import LlmModelPrice


def _seed_call(db_session, **overrides):
    defaults = dict(
        caller="analyser", provider="claude", model="claude-haiku-4-5-20251001",
        input_tokens=1000, output_tokens=500, estimated=False, duration_ms=1200,
    )
    defaults.update(overrides)
    call = LlmCall(**defaults)
    db_session.add(call)
    db_session.commit()
    return call


def test_summary_empty(client):
    response = client.get("/api/llm-usage/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["today"]["total_tokens"] == 0
    assert data["all_time"]["total_tokens"] == 0


def test_summary_counts_todays_call(client, db_session):
    _seed_call(db_session)
    response = client.get("/api/llm-usage/summary")
    data = response.json()
    assert data["today"]["total_tokens"] == 1500
    assert data["all_time"]["total_tokens"] == 1500


def test_summary_excludes_old_calls_from_today(client, db_session):
    old_call = _seed_call(db_session)
    old_call.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    db_session.commit()

    response = client.get("/api/llm-usage/summary")
    data = response.json()
    assert data["today"]["total_tokens"] == 0
    assert data["last_30_days"]["total_tokens"] == 1500


def test_summary_computes_cost_from_price_table(client, db_session):
    _seed_call(db_session, input_tokens=1_000_000, output_tokens=1_000_000)
    db_session.add(LlmModelPrice(model="claude-haiku-4-5-20251001", input_price_per_1m=1.0, output_price_per_1m=5.0))
    db_session.commit()

    response = client.get("/api/llm-usage/summary")
    data = response.json()
    assert data["today"]["cost_usd"] == 6.0


def test_timeseries_groups_by_day(client, db_session):
    _seed_call(db_session)
    response = client.get("/api/llm-usage/timeseries?days=7")
    assert response.status_code == 200
    points = response.json()
    assert len(points) == 1
    assert points[0]["total_tokens"] == 1500


def test_breakdown_groups_by_caller_provider_model(client, db_session):
    _seed_call(db_session, caller="analyser")
    _seed_call(db_session, caller="assessor", input_tokens=200, output_tokens=100)
    response = client.get("/api/llm-usage/breakdown?days=30")
    rows = response.json()
    assert len(rows) == 2
    callers = {r["caller"] for r in rows}
    assert callers == {"analyser", "assessor"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_usage_router.py -v`
Expected: FAIL with 404 (no `/api/llm-usage/*` routes registered yet)

- [ ] **Step 3: Write the schemas**

```python
# backend/app/schemas/llm_usage.py
from typing import List
from pydantic import BaseModel


class LlmUsageTotals(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class LlmUsageSummary(BaseModel):
    today: LlmUsageTotals
    last_7_days: LlmUsageTotals
    last_30_days: LlmUsageTotals
    all_time: LlmUsageTotals


class LlmUsageTimeseriesPoint(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class LlmUsageBreakdownRow(BaseModel):
    caller: str
    provider: str
    model: str
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class LlmModelPriceRead(BaseModel):
    model: str
    input_price_per_1m: float
    output_price_per_1m: float

    class Config:
        from_attributes = True


class LlmModelPriceUpdate(BaseModel):
    input_price_per_1m: float
    output_price_per_1m: float
```

- [ ] **Step 4: Write the router**

```python
# backend/app/routers/llm_usage.py
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_call import LlmCall
from app.models.llm_model_price import LlmModelPrice
from app.schemas.llm_usage import (
    LlmModelPriceRead,
    LlmModelPriceUpdate,
    LlmUsageBreakdownRow,
    LlmUsageSummary,
    LlmUsageTimeseriesPoint,
    LlmUsageTotals,
)

router = APIRouter()


def _price_map(db: Session) -> dict:
    return {p.model: p for p in db.query(LlmModelPrice).all()}


def _cost_usd(model: str, input_tokens: int, output_tokens: int, prices: dict) -> float:
    price = prices.get(model)
    if price is None:
        return 0.0
    return (input_tokens / 1_000_000 * price.input_price_per_1m) + (
        output_tokens / 1_000_000 * price.output_price_per_1m
    )


def _totals_since(db: Session, since: datetime, prices: dict) -> LlmUsageTotals:
    rows = db.query(LlmCall.model, LlmCall.input_tokens, LlmCall.output_tokens).filter(
        LlmCall.created_at >= since
    ).all()
    input_tokens = sum(r.input_tokens for r in rows)
    output_tokens = sum(r.output_tokens for r in rows)
    cost = sum(_cost_usd(r.model, r.input_tokens, r.output_tokens, prices) for r in rows)
    return LlmUsageTotals(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=round(cost, 4),
    )


@router.get("/summary", response_model=LlmUsageSummary)
def get_summary(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    prices = _price_map(db)
    return LlmUsageSummary(
        today=_totals_since(db, today_start, prices),
        last_7_days=_totals_since(db, now - timedelta(days=7), prices),
        last_30_days=_totals_since(db, now - timedelta(days=30), prices),
        all_time=_totals_since(db, datetime.min.replace(tzinfo=timezone.utc), prices),
    )


@router.get("/timeseries", response_model=List[LlmUsageTimeseriesPoint])
def get_timeseries(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    prices = _price_map(db)
    rows = db.query(LlmCall.created_at, LlmCall.model, LlmCall.input_tokens, LlmCall.output_tokens).filter(
        LlmCall.created_at >= since
    ).all()

    by_day: dict = {}
    for r in rows:
        day_key = r.created_at.date().isoformat()
        bucket = by_day.setdefault(day_key, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
        bucket["input_tokens"] += r.input_tokens
        bucket["output_tokens"] += r.output_tokens
        bucket["cost_usd"] += _cost_usd(r.model, r.input_tokens, r.output_tokens, prices)

    return [
        LlmUsageTimeseriesPoint(
            date=day,
            input_tokens=v["input_tokens"],
            output_tokens=v["output_tokens"],
            total_tokens=v["input_tokens"] + v["output_tokens"],
            cost_usd=round(v["cost_usd"], 4),
        )
        for day, v in sorted(by_day.items())
    ]


@router.get("/breakdown", response_model=List[LlmUsageBreakdownRow])
def get_breakdown(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    prices = _price_map(db)
    rows = db.query(
        LlmCall.caller, LlmCall.provider, LlmCall.model,
        func.count(LlmCall.id).label("call_count"),
        func.sum(LlmCall.input_tokens).label("input_tokens"),
        func.sum(LlmCall.output_tokens).label("output_tokens"),
    ).filter(LlmCall.created_at >= since).group_by(
        LlmCall.caller, LlmCall.provider, LlmCall.model
    ).all()

    result = []
    for r in rows:
        input_tokens = r.input_tokens or 0
        output_tokens = r.output_tokens or 0
        result.append(LlmUsageBreakdownRow(
            caller=r.caller,
            provider=r.provider,
            model=r.model,
            call_count=r.call_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=round(_cost_usd(r.model, input_tokens, output_tokens, prices), 4),
        ))
    return result


@router.get("/prices", response_model=List[LlmModelPriceRead])
def get_prices(db: Session = Depends(get_db)):
    return db.query(LlmModelPrice).order_by(LlmModelPrice.model).all()


@router.put("/prices/{model}", response_model=LlmModelPriceRead)
def upsert_price(model: str, payload: LlmModelPriceUpdate, db: Session = Depends(get_db)):
    price = db.query(LlmModelPrice).filter(LlmModelPrice.model == model).first()
    if price is None:
        price = LlmModelPrice(model=model)
        db.add(price)
    price.input_price_per_1m = payload.input_price_per_1m
    price.output_price_per_1m = payload.output_price_per_1m
    db.commit()
    db.refresh(price)
    return price
```

- [ ] **Step 5: Register the router**

In `backend/app/main.py`, add `llm_usage` to the router import block (after `logs`):

```python
    logs,
    llm_usage,
)  # noqa: E402
```

Add after the `logs` router registration line:

```python
app.include_router(llm_usage.router, prefix="/api/llm-usage", tags=["llm-usage"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_usage_router.py -v`
Expected: PASS (6 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/llm_usage.py backend/app/routers/llm_usage.py backend/app/main.py backend/tests/test_llm_usage_router.py
git commit -m "feat: add LLM usage summary, timeseries, breakdown and price endpoints"
```

---

### Task 5: Model price write tests

**Files:**
- Modify: `backend/tests/test_llm_usage_router.py`

**Interfaces:**
- Consumes: `PUT /api/llm-usage/prices/{model}` from Task 4.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_llm_usage_router.py`:

```python
def test_put_price_creates_new_entry(client):
    response = client.put(
        "/api/llm-usage/prices/claude-haiku-4-5-20251001",
        json={"input_price_per_1m": 1.0, "output_price_per_1m": 5.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "claude-haiku-4-5-20251001"
    assert data["output_price_per_1m"] == 5.0


def test_put_price_updates_existing_entry(client, db_session):
    db_session.add(LlmModelPrice(model="claude-haiku-4-5-20251001", input_price_per_1m=1.0, output_price_per_1m=5.0))
    db_session.commit()

    response = client.put(
        "/api/llm-usage/prices/claude-haiku-4-5-20251001",
        json={"input_price_per_1m": 2.0, "output_price_per_1m": 10.0},
    )
    assert response.status_code == 200
    assert response.json()["input_price_per_1m"] == 2.0

    response = client.get("/api/llm-usage/prices")
    assert len(response.json()) == 1
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_llm_usage_router.py -v`
Expected: PASS (8 passed) — `upsert_price` from Task 4 already implements this behavior

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_llm_usage_router.py
git commit -m "test: cover LLM model price create/update via PUT endpoint"
```

---

### Task 6: `AppSetting` model, migration, and override-application module

**Files:**
- Create: `backend/app/models/app_setting.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/e6a9c3f7d1b8_add_app_settings.py`
- Create: `backend/app/settings_overrides.py`
- Test: `backend/tests/test_settings_overrides.py`

**Interfaces:**
- Produces: `OVERRIDABLE_FIELDS: dict[str, type]`, `cast_value(key, raw_value) -> Any`, `validate_value(key, value) -> None` (raises `ValueError`), `default_value(key) -> Any`, `apply_override(key, raw_value) -> Any`, `reset_override(key) -> Any`, `load_overrides_from_db(db) -> None` — consumed by Task 7 (router) and Task 9 (lifespan wiring).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_settings_overrides.py
import pytest


def test_cast_value_casts_per_field_type():
    from app.settings_overrides import cast_value

    assert cast_value("crawl_concurrency", "9") == 9
    assert cast_value("search_relevance_threshold", "0.6") == 0.6
    assert cast_value("js_rendering_enabled", "true") is True
    assert cast_value("js_rendering_enabled", "false") is False
    assert cast_value("claude_model", "claude-x") == "claude-x"


def test_validate_value_rejects_unknown_llm_provider():
    from app.settings_overrides import validate_value

    with pytest.raises(ValueError):
        validate_value("llm_provider", "gpt4")
    validate_value("llm_provider", "ollama")  # does not raise


def test_apply_override_sets_live_settings_singleton():
    from app.settings_overrides import apply_override
    from app.config import settings

    apply_override("crawl_concurrency", "9")
    assert settings.crawl_concurrency == 9
    apply_override("crawl_concurrency", "4")  # restore


def test_reset_override_restores_env_default():
    from app.settings_overrides import apply_override, reset_override
    from app.config import settings

    apply_override("analysis_concurrency", "11")
    assert settings.analysis_concurrency == 11
    reset_override("analysis_concurrency")
    assert settings.analysis_concurrency == 3  # default from config.py


def test_load_overrides_from_db_applies_stored_rows(db_session):
    from app.models.app_setting import AppSetting
    from app.settings_overrides import load_overrides_from_db
    from app.config import settings

    db_session.add(AppSetting(key="discovery_depth", value="3"))
    db_session.commit()

    load_overrides_from_db(db_session)
    assert settings.discovery_depth == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_settings_overrides.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.settings_overrides'`

- [ ] **Step 3: Create the `AppSetting` model**

```python
# backend/app/models/app_setting.py
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String
from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(String(500), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

Register in `backend/app/models/__init__.py`:

```python
from app.models.app_setting import AppSetting  # noqa: F401
```

```python
    "LlmModelPrice",
    "AppSetting",
]
```

- [ ] **Step 4: Write the migration**

```python
# backend/alembic/versions/e6a9c3f7d1b8_add_app_settings.py
"""add app_settings table

Revision ID: e6a9c3f7d1b8
Revises: d4f8a1c2b3e5
Create Date: 2026-06-23 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e6a9c3f7d1b8'
down_revision: Union[str, Sequence[str], None] = 'd4f8a1c2b3e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'app_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('app_settings')
```

- [ ] **Step 5: Write `settings_overrides.py`**

```python
# backend/app/settings_overrides.py
import logging
from typing import Any, Dict

from app.config import Settings, settings

logger = logging.getLogger(__name__)

OVERRIDABLE_FIELDS: Dict[str, type] = {
    "llm_provider": str,
    "claude_model": str,
    "ollama_base_url": str,
    "ollama_model": str,
    "opencode_model": str,
    "opencode_base_url": str,
    "discovery_depth": int,
    "js_rendering_enabled": bool,
    "search_relevance_threshold": float,
    "search_queries_per_company": int,
    "assessment_threshold": float,
    "crawl_concurrency": int,
    "discovery_concurrency": int,
    "analysis_concurrency": int,
}

LLM_PROVIDER_CHOICES = {"claude", "ollama", "opencode"}


def cast_value(key: str, raw_value: str) -> Any:
    field_type = OVERRIDABLE_FIELDS[key]
    if field_type is bool:
        return raw_value.strip().lower() in ("true", "1", "yes")
    if field_type is int:
        return int(raw_value)
    if field_type is float:
        return float(raw_value)
    return raw_value


def validate_value(key: str, value: Any) -> None:
    if key == "llm_provider" and value not in LLM_PROVIDER_CHOICES:
        raise ValueError(f"llm_provider must be one of {sorted(LLM_PROVIDER_CHOICES)}")


def default_value(key: str) -> Any:
    return getattr(Settings(), key)


def load_overrides_from_db(db) -> None:
    from app.models.app_setting import AppSetting

    for row in db.query(AppSetting).all():
        if row.key not in OVERRIDABLE_FIELDS:
            continue
        try:
            value = cast_value(row.key, row.value)
            setattr(settings, row.key, value)
        except (ValueError, TypeError):
            logger.warning("Skipping invalid stored setting %s=%s", row.key, row.value)


def apply_override(key: str, raw_value: str) -> Any:
    value = cast_value(key, raw_value)
    validate_value(key, value)
    setattr(settings, key, value)
    return value


def reset_override(key: str) -> Any:
    value = default_value(key)
    setattr(settings, key, value)
    return value
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_settings_overrides.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Apply migration to dev DB**

Run: `docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`
Expected: output ends with `... -> e6a9c3f7d1b8, add app_settings table`

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/app_setting.py backend/app/models/__init__.py backend/alembic/versions/e6a9c3f7d1b8_add_app_settings.py backend/app/settings_overrides.py backend/tests/test_settings_overrides.py
git commit -m "feat: add AppSetting model and runtime settings override module"
```

---

### Task 7: Settings admin endpoints (GET/PUT/DELETE)

**Files:**
- Create: `backend/app/schemas/settings_admin.py`
- Create: `backend/app/routers/settings_admin.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_settings_admin_router.py`

**Interfaces:**
- Consumes: `OVERRIDABLE_FIELDS`, `apply_override`, `reset_override`, `default_value` from Task 6.
- Produces: `GET /api/admin/settings`, `PUT /api/admin/settings/{key}`, `DELETE /api/admin/settings/{key}` — consumed by Task 8 (frontend API client).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_settings_admin_router.py
import pytest

from app.settings_overrides import OVERRIDABLE_FIELDS, default_value


@pytest.fixture(autouse=True)
def _restore_live_settings():
    from app.config import settings as live_settings

    snapshot = {key: getattr(live_settings, key) for key in OVERRIDABLE_FIELDS}
    yield
    for key, value in snapshot.items():
        setattr(live_settings, key, value)


def test_list_settings_shows_defaults_initially(client):
    response = client.get("/api/admin/settings")
    assert response.status_code == 200
    data = response.json()
    entry = next(s for s in data if s["key"] == "crawl_concurrency")
    assert entry["is_override"] is False
    assert entry["current_value"] == entry["default_value"] == str(default_value("crawl_concurrency"))


def test_put_setting_applies_immediately(client):
    from app.config import settings as live_settings

    response = client.put("/api/admin/settings/crawl_concurrency", json={"value": "9"})
    assert response.status_code == 200
    data = response.json()
    assert data["is_override"] is True
    assert data["current_value"] == "9"
    assert live_settings.crawl_concurrency == 9


def test_put_setting_rejects_invalid_llm_provider(client):
    response = client.put("/api/admin/settings/llm_provider", json={"value": "gpt4"})
    assert response.status_code == 422


def test_put_setting_rejects_unknown_key(client):
    response = client.put("/api/admin/settings/anthropic_api_key", json={"value": "sk-x"})
    assert response.status_code == 404


def test_delete_setting_resets_to_default(client):
    from app.config import settings as live_settings

    client.put("/api/admin/settings/crawl_concurrency", json={"value": "9"})
    response = client.delete("/api/admin/settings/crawl_concurrency")
    assert response.status_code == 200
    data = response.json()
    assert data["is_override"] is False
    assert live_settings.crawl_concurrency == default_value("crawl_concurrency")


def test_load_overrides_from_db_reapplies_after_restart(client, db_session):
    from app.config import settings as live_settings
    from app.settings_overrides import load_overrides_from_db

    client.put("/api/admin/settings/analysis_concurrency", json={"value": "7"})
    live_settings.analysis_concurrency = 3  # simulate a fresh process re-reading .env

    load_overrides_from_db(db_session)
    assert live_settings.analysis_concurrency == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_settings_admin_router.py -v`
Expected: FAIL with 404 (no `/api/admin/settings` routes registered yet)

- [ ] **Step 3: Write the schemas**

```python
# backend/app/schemas/settings_admin.py
from pydantic import BaseModel


class AppSettingRead(BaseModel):
    key: str
    current_value: str
    default_value: str
    is_override: bool


class AppSettingUpdate(BaseModel):
    value: str
```

- [ ] **Step 4: Write the router**

```python
# backend/app/routers/settings_admin.py
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.app_setting import AppSetting
from app.schemas.settings_admin import AppSettingRead, AppSettingUpdate
from app.settings_overrides import OVERRIDABLE_FIELDS, apply_override, default_value, reset_override

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[AppSettingRead])
def list_settings(db: Session = Depends(get_db)):
    overridden_keys = {row.key for row in db.query(AppSetting.key).all()}
    return [
        AppSettingRead(
            key=key,
            current_value=str(getattr(settings, key)),
            default_value=str(default_value(key)),
            is_override=key in overridden_keys,
        )
        for key in OVERRIDABLE_FIELDS
    ]


@router.put("/{key}", response_model=AppSettingRead)
def update_setting(key: str, payload: AppSettingUpdate, db: Session = Depends(get_db)):
    if key not in OVERRIDABLE_FIELDS:
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")
    try:
        value = apply_override(key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is None:
        row = AppSetting(key=key, value=str(value))
        db.add(row)
    else:
        row.value = str(value)
    db.commit()
    logger.info("Setting override applied: %s=%s", key, value)

    return AppSettingRead(
        key=key, current_value=str(value), default_value=str(default_value(key)), is_override=True,
    )


@router.delete("/{key}", response_model=AppSettingRead)
def delete_setting(key: str, db: Session = Depends(get_db)):
    if key not in OVERRIDABLE_FIELDS:
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is not None:
        db.delete(row)
        db.commit()
    value = reset_override(key)
    logger.info("Setting override reset: %s -> %s", key, value)
    return AppSettingRead(
        key=key, current_value=str(value), default_value=str(default_value(key)), is_override=False,
    )
```

- [ ] **Step 5: Register the router**

In `backend/app/main.py`, add `settings_admin` to the router import block:

```python
    llm_usage,
    settings_admin,
)  # noqa: E402
```

Add after the `llm_usage` router registration line:

```python
app.include_router(settings_admin.router, prefix="/api/admin/settings", tags=["settings-admin"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_settings_admin_router.py -v`
Expected: PASS (6 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/settings_admin.py backend/app/routers/settings_admin.py backend/app/main.py backend/tests/test_settings_admin_router.py
git commit -m "feat: add settings admin GET/PUT/DELETE endpoints"
```

---

### Task 8: Apply DB overrides on app startup

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_settings_admin_router.py` (already covers `load_overrides_from_db` directly; this task wires it into `lifespan`)

**Interfaces:**
- Consumes: `load_overrides_from_db(db)` from Task 6.

- [ ] **Step 1: Update the `lifespan` function**

In `backend/app/main.py`, the `lifespan` function currently is:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, SessionLocal
    from app.models.schedule import ScheduleConfig
    from app import scheduler as sched_module
    from app import log_stream

    log_stream.install()

    try:
        sched_module.startup_scheduler(engine)

        db = SessionLocal()
        config = None
        try:
            config = db.query(ScheduleConfig).filter(ScheduleConfig.id == 1).first()
            if config is None:
                config = ScheduleConfig()
                db.add(config)
                db.commit()
                db.refresh(config)
        finally:
            db.close()

        sched_module.apply_schedule(config)
    except Exception as exc:
        logger.warning("Scheduler startup failed (likely test environment): %s", exc)

    yield

    sched_module.shutdown_scheduler()
```

Replace it with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, SessionLocal
    from app.models.schedule import ScheduleConfig
    from app import scheduler as sched_module
    from app import log_stream
    from app.settings_overrides import load_overrides_from_db

    log_stream.install()

    try:
        sched_module.startup_scheduler(engine)

        db = SessionLocal()
        config = None
        try:
            config = db.query(ScheduleConfig).filter(ScheduleConfig.id == 1).first()
            if config is None:
                config = ScheduleConfig()
                db.add(config)
                db.commit()
                db.refresh(config)
            load_overrides_from_db(db)
        finally:
            db.close()

        sched_module.apply_schedule(config)
    except Exception as exc:
        logger.warning("Scheduler startup failed (likely test environment): %s", exc)

    yield

    sched_module.shutdown_scheduler()
```

- [ ] **Step 2: Run the full backend suite to verify nothing regressed**

Run: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/ -v`
Expected: PASS (all tests, including `test_schedule_router.py`, which already exercises this `lifespan` path)

- [ ] **Step 3: Restart the dev backend and verify startup logs are clean**

Run: `docker compose -f docker-compose.dev.yml restart backend && docker compose -f docker-compose.dev.yml logs backend --tail 30`
Expected: no traceback; normal startup log lines

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: apply DB setting overrides on application startup"
```

---

### Task 9: Frontend types and API clients

**Files:**
- Create: `frontend/src/types/llmUsage.ts`
- Create: `frontend/src/types/settings.ts`
- Create: `frontend/src/api/llmUsage.ts`
- Create: `frontend/src/api/settingsAdmin.ts`

**Interfaces:**
- Consumes: `apiGet`, `apiPut`, `apiDelete` from `frontend/src/api/client.ts`.
- Produces: `fetchLlmUsageSummary`, `fetchLlmUsageTimeseries`, `fetchLlmUsageBreakdown`, `fetchLlmModelPrices`, `updateLlmModelPrice`, `fetchAppSettings`, `updateAppSetting`, `resetAppSetting` — consumed by Tasks 10–11.

- [ ] **Step 1: Write the types**

```typescript
// frontend/src/types/llmUsage.ts
export interface LlmUsageTotals {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface LlmUsageSummary {
  today: LlmUsageTotals;
  last_7_days: LlmUsageTotals;
  last_30_days: LlmUsageTotals;
  all_time: LlmUsageTotals;
}

export interface LlmUsageTimeseriesPoint {
  date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface LlmUsageBreakdownRow {
  caller: string;
  provider: string;
  model: string;
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface LlmModelPrice {
  model: string;
  input_price_per_1m: number;
  output_price_per_1m: number;
}
```

```typescript
// frontend/src/types/settings.ts
export interface AppSetting {
  key: string;
  current_value: string;
  default_value: string;
  is_override: boolean;
}
```

- [ ] **Step 2: Write the API clients**

```typescript
// frontend/src/api/llmUsage.ts
import { apiGet, apiPut } from './client';
import type {
  LlmUsageBreakdownRow, LlmUsageSummary, LlmUsageTimeseriesPoint, LlmModelPrice,
} from '../types/llmUsage';

export function fetchLlmUsageSummary() {
  return apiGet<LlmUsageSummary>('/llm-usage/summary');
}

export function fetchLlmUsageTimeseries(days = 30) {
  return apiGet<LlmUsageTimeseriesPoint[]>('/llm-usage/timeseries', { days: String(days) });
}

export function fetchLlmUsageBreakdown(days = 30) {
  return apiGet<LlmUsageBreakdownRow[]>('/llm-usage/breakdown', { days: String(days) });
}

export function fetchLlmModelPrices() {
  return apiGet<LlmModelPrice[]>('/llm-usage/prices');
}

export function updateLlmModelPrice(
  model: string,
  price: { input_price_per_1m: number; output_price_per_1m: number },
) {
  return apiPut<LlmModelPrice>(`/llm-usage/prices/${encodeURIComponent(model)}`, price);
}
```

```typescript
// frontend/src/api/settingsAdmin.ts
import { apiDelete, apiGet, apiPut } from './client';
import type { AppSetting } from '../types/settings';

export function fetchAppSettings() {
  return apiGet<AppSetting[]>('/admin/settings');
}

export function updateAppSetting(key: string, value: string) {
  return apiPut<AppSetting>(`/admin/settings/${encodeURIComponent(key)}`, { value });
}

export function resetAppSetting(key: string): Promise<void> {
  return apiDelete(`/admin/settings/${encodeURIComponent(key)}`);
}
```

- [ ] **Step 3: Verify the project still type-checks**

Run: `docker compose -f docker-compose.dev.yml exec frontend npm run build`
Expected: build succeeds with no TypeScript errors (these files are not imported anywhere yet, so this just confirms valid syntax/types)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/llmUsage.ts frontend/src/types/settings.ts frontend/src/api/llmUsage.ts frontend/src/api/settingsAdmin.ts
git commit -m "feat: add frontend types and API clients for LLM usage and settings"
```

---

### Task 10: `LlmUsageAdmin` page

**Files:**
- Create: `frontend/src/pages/LlmUsageAdmin.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

**Interfaces:**
- Consumes: API client functions from Task 9.

- [ ] **Step 1: Write the page component**

```tsx
// frontend/src/pages/LlmUsageAdmin.tsx
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchLlmModelPrices, fetchLlmUsageBreakdown, fetchLlmUsageSummary, fetchLlmUsageTimeseries,
  updateLlmModelPrice,
} from '../api/llmUsage';
import type { LlmUsageTimeseriesPoint, LlmUsageTotals } from '../types/llmUsage';

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function formatCost(n: number): string {
  return `$${n.toFixed(2)}`;
}

function SummaryTile({ label, totals }: { label: string; totals: LlmUsageTotals }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-semibold text-slate-800 mt-1">{formatTokens(totals.total_tokens)}</p>
      <p className="text-xs text-slate-400 mt-0.5">{formatCost(totals.cost_usd)}</p>
    </div>
  );
}

function Sparkbars({ points }: { points: LlmUsageTimeseriesPoint[] }) {
  const max = Math.max(1, ...points.map((p) => p.total_tokens));
  return (
    <div className="flex items-end gap-1 h-32">
      {points.map((p) => (
        <div
          key={p.date}
          className="flex-1 bg-blue-500/70 rounded-t hover:bg-blue-500 transition-colors min-h-[2px]"
          style={{ height: `${Math.max(2, (p.total_tokens / max) * 100)}%` }}
          title={`${p.date}: ${formatTokens(p.total_tokens)} Tokens · ${formatCost(p.cost_usd)}`}
        />
      ))}
    </div>
  );
}

function PriceEditorRow({ model, inputPrice, outputPrice, onSaved }: {
  model: string; inputPrice: number; outputPrice: number; onSaved: () => void;
}) {
  const [input, setInput] = useState(String(inputPrice));
  const [output, setOutput] = useState(String(outputPrice));

  const saveMutation = useMutation({
    mutationFn: () => updateLlmModelPrice(model, {
      input_price_per_1m: parseFloat(input) || 0,
      output_price_per_1m: parseFloat(output) || 0,
    }),
    onSuccess: onSaved,
  });

  return (
    <tr className="border-b border-slate-100">
      <td className="py-2 text-sm text-slate-700">{model}</td>
      <td className="py-2">
        <input
          type="number" step="0.01" value={input} onChange={(e) => setInput(e.target.value)}
          className="border border-slate-200 rounded-lg px-2 py-1 text-sm w-24"
        />
      </td>
      <td className="py-2">
        <input
          type="number" step="0.01" value={output} onChange={(e) => setOutput(e.target.value)}
          className="border border-slate-200 rounded-lg px-2 py-1 text-sm w-24"
        />
      </td>
      <td className="py-2">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-50"
        >
          Speichern
        </button>
      </td>
    </tr>
  );
}

const KNOWN_MODELS = ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6', 'claude-opus-4-8'];

export default function LlmUsageAdmin() {
  const queryClient = useQueryClient();
  const [days, setDays] = useState(30);

  const { data: summary } = useQuery({ queryKey: ['llm-usage-summary'], queryFn: fetchLlmUsageSummary });
  const { data: timeseries } = useQuery({
    queryKey: ['llm-usage-timeseries', days],
    queryFn: () => fetchLlmUsageTimeseries(days),
  });
  const { data: breakdown } = useQuery({
    queryKey: ['llm-usage-breakdown', days],
    queryFn: () => fetchLlmUsageBreakdown(days),
  });
  const { data: prices } = useQuery({ queryKey: ['llm-model-prices'], queryFn: fetchLlmModelPrices });

  function refetchAll() {
    queryClient.invalidateQueries({ queryKey: ['llm-model-prices'] });
    queryClient.invalidateQueries({ queryKey: ['llm-usage-summary'] });
    queryClient.invalidateQueries({ queryKey: ['llm-usage-timeseries', days] });
    queryClient.invalidateQueries({ queryKey: ['llm-usage-breakdown', days] });
  }

  const priceByModel = new Map((prices ?? []).map((p) => [p.model, p]));
  const allModels = Array.from(new Set([...KNOWN_MODELS, ...(prices ?? []).map((p) => p.model)]));

  return (
    <div className="p-6 max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">LLM-Token-Nutzung</h1>
        <p className="text-sm text-slate-500 mt-0.5">Token-Verbrauch und Kosten über alle Pipelines</p>
      </div>

      {summary && (
        <div className="grid grid-cols-4 gap-3">
          <SummaryTile label="Heute" totals={summary.today} />
          <SummaryTile label="7 Tage" totals={summary.last_7_days} />
          <SummaryTile label="30 Tage" totals={summary.last_30_days} />
          <SummaryTile label="Gesamt" totals={summary.all_time} />
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Verlauf</h2>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-white"
          >
            <option value={7}>7 Tage</option>
            <option value={30}>30 Tage</option>
            <option value={90}>90 Tage</option>
          </select>
        </div>
        {timeseries && timeseries.length > 0 ? (
          <Sparkbars points={timeseries} />
        ) : (
          <p className="text-sm text-slate-400">Keine Daten im Zeitraum.</p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 overflow-x-auto">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-3">
          Aufschlüsselung nach Caller / Provider / Modell
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-400 border-b border-slate-200">
              <th className="py-2">Caller</th>
              <th className="py-2">Provider</th>
              <th className="py-2">Modell</th>
              <th className="py-2 text-right">Calls</th>
              <th className="py-2 text-right">Tokens</th>
              <th className="py-2 text-right">Kosten</th>
            </tr>
          </thead>
          <tbody>
            {(breakdown ?? []).map((row) => (
              <tr key={`${row.caller}-${row.provider}-${row.model}`} className="border-b border-slate-100">
                <td className="py-2 text-slate-700">{row.caller}</td>
                <td className="py-2 text-slate-500">{row.provider}</td>
                <td className="py-2 text-slate-500">{row.model}</td>
                <td className="py-2 text-right">{row.call_count}</td>
                <td className="py-2 text-right">{formatTokens(row.total_tokens)}</td>
                <td className="py-2 text-right">{formatCost(row.cost_usd)}</td>
              </tr>
            ))}
            {(breakdown ?? []).length === 0 && (
              <tr><td colSpan={6} className="py-4 text-center text-slate-400">Keine Daten im Zeitraum.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 overflow-x-auto">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-3">
          Preistabelle ($ pro 1M Tokens)
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-400 border-b border-slate-200">
              <th className="py-2">Modell</th>
              <th className="py-2">Input</th>
              <th className="py-2">Output</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {allModels.map((model) => {
              const price = priceByModel.get(model);
              return (
                <PriceEditorRow
                  key={model}
                  model={model}
                  inputPrice={price?.input_price_per_1m ?? 0}
                  outputPrice={price?.output_price_per_1m ?? 0}
                  onSaved={refetchAll}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire up the route**

In `frontend/src/App.tsx`, add the import after `LogsAdmin`:

```tsx
import LogsAdmin from './pages/LogsAdmin';
import LlmUsageAdmin from './pages/LlmUsageAdmin';
```

Add the route after `admin/logs`:

```tsx
            <Route path="admin/logs" element={<LogsAdmin />} />
            <Route path="admin/llm-usage" element={<LlmUsageAdmin />} />
```

- [ ] **Step 3: Add the nav entry**

In `frontend/src/components/Layout.tsx`, add `Coins` to the `lucide-react` import:

```tsx
import {
  LayoutDashboard, Users, TrendingUp, FileText, Settings, Search,
  Globe, LogOut, Zap, BookOpen, Clock, Terminal, Menu, X, GitCommit, Calendar, Coins,
} from 'lucide-react';
```

Add a nav item to the `Admin` section, after `Logs`:

```tsx
      { to: '/admin/logs', label: 'Logs', icon: Terminal },
      { to: '/admin/llm-usage', label: 'LLM-Nutzung', icon: Coins },
```

- [ ] **Step 4: Verify the build**

Run: `docker compose -f docker-compose.dev.yml exec frontend npm run build`
Expected: build succeeds with no TypeScript errors

- [ ] **Step 5: Manual check**

Open `http://localhost:5173/admin/llm-usage` in a browser, log in, and confirm the page renders tiles, the verlauf section ("Keine Daten im Zeitraum." if no `llm_calls` rows exist yet), the breakdown table, and the price table with the three known Claude models pre-listed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/LlmUsageAdmin.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add LLM usage admin page with summary, timeseries, breakdown, and price editor"
```

---

### Task 11: `SettingsAdmin` page

**Files:**
- Create: `frontend/src/pages/SettingsAdmin.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

**Interfaces:**
- Consumes: `fetchAppSettings`, `updateAppSetting`, `resetAppSetting` from Task 9.

- [ ] **Step 1: Write the page component**

```tsx
// frontend/src/pages/SettingsAdmin.tsx
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RotateCcw, Save } from 'lucide-react';
import { fetchAppSettings, resetAppSetting, updateAppSetting } from '../api/settingsAdmin';
import type { AppSetting } from '../types/settings';

type FieldKind = 'select' | 'number' | 'boolean' | 'text';

interface FieldDef {
  key: string;
  label: string;
  kind: FieldKind;
  options?: { value: string; label: string }[];
  step?: string;
}

const FIELD_GROUPS: { title: string; fields: FieldDef[] }[] = [
  {
    title: 'LLM-Provider',
    fields: [
      {
        key: 'llm_provider', label: 'Provider', kind: 'select', options: [
          { value: 'claude', label: 'Claude' },
          { value: 'ollama', label: 'Ollama' },
          { value: 'opencode', label: 'Opencode' },
        ],
      },
      { key: 'claude_model', label: 'Claude-Modell', kind: 'text' },
      { key: 'ollama_base_url', label: 'Ollama Base URL', kind: 'text' },
      { key: 'ollama_model', label: 'Ollama-Modell', kind: 'text' },
      { key: 'opencode_model', label: 'Opencode-Modell', kind: 'text' },
      { key: 'opencode_base_url', label: 'Opencode Base URL', kind: 'text' },
    ],
  },
  {
    title: 'Crawling',
    fields: [
      { key: 'discovery_depth', label: 'Discovery-Tiefe', kind: 'number' },
      { key: 'js_rendering_enabled', label: 'JS-Rendering aktiv', kind: 'boolean' },
      { key: 'crawl_concurrency', label: 'Crawl-Concurrency', kind: 'number' },
      { key: 'discovery_concurrency', label: 'Discovery-Concurrency', kind: 'number' },
      { key: 'analysis_concurrency', label: 'Analyse-Concurrency', kind: 'number' },
    ],
  },
  {
    title: 'Suche & Bewertung',
    fields: [
      { key: 'search_relevance_threshold', label: 'Such-Relevanz-Schwelle', kind: 'number', step: '0.05' },
      { key: 'search_queries_per_company', label: 'Suchanfragen pro Unternehmen', kind: 'number' },
      { key: 'assessment_threshold', label: 'Assessment-Schwelle', kind: 'number', step: '0.05' },
    ],
  },
];

function FieldRow({ def, setting, onSaved }: { def: FieldDef; setting: AppSetting; onSaved: () => void }) {
  const [value, setValue] = useState(setting.current_value);

  const saveMutation = useMutation({
    mutationFn: (v: string) => updateAppSetting(def.key, v),
    onSuccess: onSaved,
  });
  const resetMutation = useMutation({
    mutationFn: () => resetAppSetting(def.key),
    onSuccess: onSaved,
  });

  const dirty = value !== setting.current_value;

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-slate-100 last:border-b-0">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-700">{def.label}</span>
          {setting.is_override && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
              Override
            </span>
          )}
        </div>
        <span className="text-[11px] text-slate-400">Default: {setting.default_value}</span>
      </div>

      {def.kind === 'select' && (
        <select
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-white"
        >
          {def.options!.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      )}

      {def.kind === 'boolean' && (
        <select
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-white"
        >
          <option value="true">An</option>
          <option value="false">Aus</option>
        </select>
      )}

      {def.kind === 'number' && (
        <input
          type="number"
          step={def.step ?? '1'}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm w-28"
        />
      )}

      {def.kind === 'text' && (
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm w-56"
        />
      )}

      <button
        onClick={() => saveMutation.mutate(value)}
        disabled={!dirty || saveMutation.isPending}
        className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
        title="Speichern"
      >
        <Save size={14} />
      </button>

      {setting.is_override && (
        <button
          onClick={() => resetMutation.mutate()}
          disabled={resetMutation.isPending}
          className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
          title="Auf Default zurücksetzen"
        >
          <RotateCcw size={14} />
        </button>
      )}
    </div>
  );
}

export default function SettingsAdmin() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['app-settings'], queryFn: fetchAppSettings });

  function refetchSettings() {
    queryClient.invalidateQueries({ queryKey: ['app-settings'] });
  }

  if (isLoading || !data) {
    return <div className="p-6 text-sm text-slate-500">Lade Einstellungen…</div>;
  }

  const byKey = new Map(data.map((s) => [s.key, s]));

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Runtime-Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Änderungen wirken sofort und überleben Deployments. Felder ohne Override nutzen
          den Wert aus .env/GitHub-Variablen.
        </p>
      </div>

      {FIELD_GROUPS.map((group) => (
        <div key={group.title} className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-2">
            {group.title}
          </h2>
          {group.fields.map((def) => {
            const setting = byKey.get(def.key);
            if (!setting) return null;
            return <FieldRow key={def.key} def={def} setting={setting} onSaved={refetchSettings} />;
          })}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Wire up the route**

In `frontend/src/App.tsx`, add the import after `LlmUsageAdmin`:

```tsx
import LlmUsageAdmin from './pages/LlmUsageAdmin';
import SettingsAdmin from './pages/SettingsAdmin';
```

Add the route after `admin/llm-usage`:

```tsx
            <Route path="admin/llm-usage" element={<LlmUsageAdmin />} />
            <Route path="admin/settings" element={<SettingsAdmin />} />
```

- [ ] **Step 3: Add the nav entry**

In `frontend/src/components/Layout.tsx`, add `SlidersHorizontal` to the `lucide-react` import:

```tsx
import {
  LayoutDashboard, Users, TrendingUp, FileText, Settings, Search,
  Globe, LogOut, Zap, BookOpen, Clock, Terminal, Menu, X, GitCommit, Calendar, Coins,
  SlidersHorizontal,
} from 'lucide-react';
```

Add a nav item to the `Admin` section, after `LLM-Nutzung`:

```tsx
      { to: '/admin/llm-usage', label: 'LLM-Nutzung', icon: Coins },
      { to: '/admin/settings', label: 'Runtime-Settings', icon: SlidersHorizontal },
```

- [ ] **Step 4: Verify the build**

Run: `docker compose -f docker-compose.dev.yml exec frontend npm run build`
Expected: build succeeds with no TypeScript errors

- [ ] **Step 5: Manual check**

Open `http://localhost:5173/admin/settings`, change `crawl_concurrency` to a different value, save, confirm the "Override" badge appears and the value persists on page reload, then click reset and confirm it reverts to the default shown.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SettingsAdmin.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add runtime settings admin page"
```

---

## Final Verification

- [ ] Run the full backend suite: `docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/ -v` — expect all tests passing, no regressions in `test_schedule_router.py` or `test_analyser_client.py`.
- [ ] Run the frontend build: `docker compose -f docker-compose.dev.yml exec frontend npm run build` — expect a clean build.
- [ ] Trigger one real crawl+analysis cycle (or call `call_llm` indirectly via an existing pipeline) and confirm a new row appears in `llm_calls` and the `/admin/llm-usage` tiles update.
- [ ] Change a setting via `/admin/settings`, restart the backend container (`docker compose -f docker-compose.dev.yml restart backend`), and confirm the override survives (proves it isn't wiped by a "redeploy").
