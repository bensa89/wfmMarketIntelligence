# WFM Market Intelligence Hub — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully functional FastAPI backend with PostgreSQL persistence, HTTP Basic Auth, a manual crawl pipeline (httpx + BeautifulSoup → Markdown), and a Claude/Ollama-powered signal analyser.

**Architecture:** FastAPI app with SQLAlchemy ORM models (6 entities), Alembic migrations, and a modular pipeline: Crawler fetches URLs → Extractor converts HTML to Markdown → Deduplicator hashes content → Analyser calls LLM → Signals persisted. All endpoints secured with HTTP Basic Auth.

**Tech Stack:** Python 3.12 · FastAPI 0.115 · SQLAlchemy 2.0 (sync) · Alembic · PostgreSQL (psycopg2) · httpx · BeautifulSoup4 · markdownify · anthropic SDK · pytest · SQLite (tests only)

---

## File Map

```
backend/
├── app/
│   ├── main.py                     # FastAPI app, auth, router registration
│   ├── config.py                   # pydantic-settings config
│   ├── database.py                 # SQLAlchemy engine, session, Base
│   ├── models/
│   │   ├── __init__.py             # re-exports all models (needed for Alembic)
│   │   ├── company.py              # Company + CompanyType enum
│   │   ├── source.py               # Source + SourceType enum
│   │   ├── document.py             # Document
│   │   ├── signal.py               # Signal + SignalType enum
│   │   ├── digest.py               # WeeklyDigest
│   │   └── context.py              # InternalCompanyContext (singleton)
│   ├── schemas/
│   │   ├── company.py              # CompanyCreate, CompanyRead, CompanyUpdate
│   │   ├── source.py               # SourceCreate, SourceRead, SourceUpdate
│   │   ├── document.py             # DocumentRead
│   │   ├── signal.py               # SignalRead, SignalFilter
│   │   ├── digest.py               # DigestRead
│   │   └── context.py              # ContextRead, ContextUpdate
│   ├── routers/
│   │   ├── companies.py            # GET/POST /companies, GET/PUT /companies/:slug
│   │   ├── sources.py              # GET/POST /sources, PUT/DELETE /sources/:id
│   │   ├── documents.py            # GET /documents, GET /documents/:id
│   │   ├── signals.py              # GET /signals, GET /signals/:id
│   │   ├── digests.py              # GET /digests, GET /digests/:id, POST /digests/generate
│   │   ├── context.py              # GET /context, PUT /context
│   │   └── crawl.py                # POST /crawl/run, POST /crawl/run/:source_id
│   ├── crawler/
│   │   ├── fetcher.py              # fetch_url(url) → raw HTML + metadata
│   │   ├── extractor.py            # extract(html) → {title, markdown, hash}
│   │   └── pipeline.py             # run_crawl(source, db) orchestrates fetch+extract+dedup+analyse
│   └── analyser/
│       ├── client.py               # get_llm_client() → Claude or Ollama
│       ├── prompts.py              # build_analysis_prompt(markdown, context) → str
│       └── parser.py               # parse_llm_response(raw) → SignalData
├── tests/
│   ├── conftest.py                 # TestClient + SQLite test DB fixture
│   ├── test_companies.py
│   ├── test_sources.py
│   ├── test_documents.py
│   ├── test_signals.py
│   ├── test_context.py
│   ├── test_digests.py
│   ├── test_crawler.py
│   └── test_analyser.py
├── alembic/
│   ├── env.py                      # Alembic env (reads DATABASE_URL from config)
│   └── versions/                   # Migration files (generated)
├── alembic.ini
├── requirements.txt
└── Dockerfile
docker-compose.yml                  # prod: backend + frontend(nginx) + db
docker-compose.dev.yml              # dev: backend + vite devserver + db
.env.example
.gitignore
```

---

## Task 1: Monorepo scaffold — Docker Compose, env, gitignore

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Create `.env.example`**

```bash
# .env.example
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=claude
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
CLAUDE_MODEL=claude-haiku-4-5-20251001
DATABASE_URL=postgresql://wfm:wfm@db:5432/wfmintel
AUTH_USERNAME=admin
AUTH_PASSWORD=changeme
```

- [ ] **Step 2: Create `docker-compose.yml` (prod)**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: wfm
      POSTGRES_PASSWORD: wfm
      POSTGRES_DB: wfmintel
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wfm"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

- [ ] **Step 3: Create `docker-compose.dev.yml` (dev)**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: wfm
      POSTGRES_PASSWORD: wfm
      POSTGRES_DB: wfmintel
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wfm"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data_dev:
```

- [ ] **Step 4: Update `.gitignore`**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/
*.egg-info/
dist/
build/
test.db
node_modules/
.superpowers/
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml .env.example .gitignore
git commit -m "chore: add monorepo scaffold with docker-compose and env template"
```

---

## Task 2: Backend project setup — requirements, Dockerfile, directory structure

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
alembic==1.14.0
pydantic==2.10.3
pydantic-settings==2.6.1
httpx==0.28.1
beautifulsoup4==4.12.3
markdownify==0.14.1
anthropic==0.40.0
python-dotenv==1.0.1
pytest==8.3.4
pytest-mock==3.14.0
```

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create `backend/app/config.py`**

```python
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


settings = Settings()
```

- [ ] **Step 4: Create `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Create empty `backend/app/__init__.py` and `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`, `backend/app/routers/__init__.py`, `backend/app/crawler/__init__.py`, `backend/app/analyser/__init__.py`**

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/routers backend/app/crawler backend/app/analyser backend/tests
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/app/routers/__init__.py backend/app/crawler/__init__.py backend/app/analyser/__init__.py backend/tests/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "chore: add backend project structure, requirements, Dockerfile, config"
```

---

## Task 3: ORM Models

**Files:**
- Create: `backend/app/models/company.py`
- Create: `backend/app/models/source.py`
- Create: `backend/app/models/document.py`
- Create: `backend/app/models/signal.py`
- Create: `backend/app/models/digest.py`
- Create: `backend/app/models/context.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_models.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Company, Source, Document, Signal, WeeklyDigest, InternalCompanyContext
from app.models.company import CompanyType
from app.models.source import SourceType
from app.models.signal import SignalType


@pytest.fixture(scope="function")
def db():
    engine = create_engine("sqlite:///./test_models.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    import os; os.remove("test_models.db") if os.path.exists("test_models.db") else None


def test_company_creation(db):
    company = Company(name="ATOSS", slug="atoss", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    assert company.id is not None
    assert len(company.id) == 36


def test_source_belongs_to_company(db):
    company = Company(name="ATOSS", slug="atoss", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    source = Source(company_id=company.id, url="https://atoss.com/news", source_type=SourceType.news)
    db.add(source)
    db.commit()
    assert source.company_id == company.id


def test_document_content_hash(db):
    company = Company(name="ATOSS", slug="atoss2", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    source = Source(company_id=company.id, url="https://atoss.com/blog", source_type=SourceType.blog)
    db.add(source)
    db.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/blog/post-1",
        title="Test Post",
        content_markdown="# Test",
        content_hash="abc123",
    )
    db.add(doc)
    db.commit()
    assert doc.is_analysed is False


def test_signal_linked_to_document(db):
    company = Company(name="ATOSS", slug="atoss3", type=CompanyType.competitor)
    db.add(company)
    db.commit()
    source = Source(company_id=company.id, url="https://atoss.com/press", source_type=SourceType.press)
    db.add(source)
    db.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/press/1", content_hash="x")
    db.add(doc)
    db.commit()
    signal = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="New AI Feature",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
    )
    db.add(signal)
    db.commit()
    assert signal.document_id == doc.id


def test_context_singleton_fields(db):
    ctx = InternalCompanyContext(
        company_name="WFM Corp",
        target_industries=["Retail", "Logistics"],
    )
    db.add(ctx)
    db.commit()
    assert ctx.target_industries == ["Retail", "Logistics"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_models.py -v
```
Expected: `ImportError` or `ModuleNotFoundError` — models don't exist yet.

- [ ] **Step 3: Create `backend/app/models/company.py`**

```python
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class CompanyType(str, enum.Enum):
    competitor = "competitor"
    market_source = "market_source"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    type = Column(SAEnum(CompanyType), nullable=False)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sources = relationship("Source", back_populates="company", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="company")
```

- [ ] **Step 4: Create `backend/app/models/source.py`**

```python
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class SourceType(str, enum.Enum):
    news = "news"
    blog = "blog"
    product = "product"
    press = "press"
    jobs = "jobs"


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    url = Column(String(2000), unique=True, nullable=False)
    label = Column(String(255), nullable=True)
    source_type = Column(SAEnum(SourceType), nullable=False, default=SourceType.news)
    is_active = Column(Boolean, default=True)
    last_crawled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="sources")
    documents = relationship("Document", back_populates="source")
```

- [ ] **Step 5: Create `backend/app/models/document.py`**

```python
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

    source = relationship("Source", back_populates="documents")
    signals = relationship("Signal", back_populates="document")
```

- [ ] **Step 6: Create `backend/app/models/signal.py`**

```python
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class SignalType(str, enum.Enum):
    product_update = "product_update"
    ai_announcement = "ai_announcement"
    partnership = "partnership"
    positioning_change = "positioning_change"
    target_market_change = "target_market_change"
    event_or_thought_leadership = "event_or_thought_leadership"
    hiring_signal = "hiring_signal"
    other = "other"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    title = Column(String(500), nullable=False)
    signal_type = Column(SAEnum(SignalType), nullable=False)
    topic = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    why_it_matters = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="signals")
    company = relationship("Company", back_populates="signals")
```

- [ ] **Step 7: Create `backend/app/models/digest.py`**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, Date
from sqlalchemy.types import JSON
from app.database import Base


class WeeklyDigest(Base):
    __tablename__ = "weekly_digests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    summary = Column(Text, nullable=True)
    key_signals = Column(JSON, default=list)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_published = Column(Boolean, default=False)
```

- [ ] **Step 8: Create `backend/app/models/context.py`**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.types import JSON
from app.database import Base


class InternalCompanyContext(Base):
    __tablename__ = "internal_company_context"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(255), nullable=True)
    short_description = Column(Text, nullable=True)
    target_industries = Column(JSON, default=list)
    target_segments = Column(JSON, default=list)
    core_capabilities = Column(JSON, default=list)
    strategic_priorities = Column(JSON, default=list)
    differentiators = Column(JSON, default=list)
    relevant_competitive_areas = Column(JSON, default=list)
    non_focus_areas = Column(JSON, default=list)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 9: Update `backend/app/models/__init__.py`**

```python
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.digest import WeeklyDigest
from app.models.context import InternalCompanyContext

__all__ = [
    "Company", "CompanyType",
    "Source", "SourceType",
    "Document",
    "Signal", "SignalType",
    "WeeklyDigest",
    "InternalCompanyContext",
]
```

- [ ] **Step 10: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_models.py -v
```
Expected: 5 passed.

- [ ] **Step 11: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add SQLAlchemy ORM models for all 6 entities"
```

---

## Task 4: Alembic migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (first migration generated)

- [ ] **Step 1: Initialise Alembic inside `backend/`**

```bash
cd backend && alembic init alembic
```
Expected: creates `alembic/` directory and `alembic.ini`.

- [ ] **Step 2: Edit `backend/alembic.ini` — set sqlalchemy.url placeholder**

In `alembic.ini`, find and replace the line:
```
sqlalchemy.url = driver://user:pass@localhost/dbname
```
with:
```
sqlalchemy.url = postgresql://wfm:wfm@localhost:5432/wfmintel
```
(This is overridden by `env.py` at runtime; the value here is just a fallback.)

- [ ] **Step 3: Replace `backend/alembic/env.py` entirely**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — ensures all models are registered

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Start the database (requires Docker)**

```bash
docker compose -f docker-compose.dev.yml up db -d
```
Expected: PostgreSQL container starts on port 5432.

- [ ] **Step 5: Generate and run initial migration**

```bash
cd backend && alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
Expected: migration file created in `alembic/versions/`, all 6 tables created.

- [ ] **Step 6: Verify tables exist**

```bash
docker exec $(docker ps -qf "name=db") psql -U wfm -d wfmintel -c "\dt"
```
Expected output includes: `companies`, `sources`, `documents`, `signals`, `weekly_digests`, `internal_company_context`.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/ backend/alembic.ini
git commit -m "feat: add Alembic migrations with initial schema"
```

---

## Task 5: Test infrastructure (conftest.py)

**Files:**
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db

TEST_DB_PATH = "./test_app.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    # Import here to avoid circular import before app is configured
    os.environ.setdefault("AUTH_USERNAME", "testuser")
    os.environ.setdefault("AUTH_PASSWORD", "testpass")
    os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, auth=("testuser", "testpass")) as c:
        yield c

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: add shared test fixtures with SQLite in-memory DB"
```

---

## Task 6: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/company.py`
- Create: `backend/app/schemas/source.py`
- Create: `backend/app/schemas/document.py`
- Create: `backend/app/schemas/signal.py`
- Create: `backend/app/schemas/digest.py`
- Create: `backend/app/schemas/context.py`
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Create `backend/app/schemas/company.py`**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.company import CompanyType


class CompanyCreate(BaseModel):
    name: str
    slug: str
    type: CompanyType
    description: Optional[str] = None
    website: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None


class CompanyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    slug: str
    type: CompanyType
    description: Optional[str]
    website: Optional[str]
    created_at: datetime
```

- [ ] **Step 2: Create `backend/app/schemas/source.py`**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.source import SourceType


class SourceCreate(BaseModel):
    company_id: str
    url: str
    label: Optional[str] = None
    source_type: SourceType = SourceType.news
    is_active: bool = True


class SourceUpdate(BaseModel):
    label: Optional[str] = None
    source_type: Optional[SourceType] = None
    is_active: Optional[bool] = None


class SourceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    url: str
    label: Optional[str]
    source_type: SourceType
    is_active: bool
    last_crawled_at: Optional[datetime]
    created_at: datetime
```

- [ ] **Step 3: Create `backend/app/schemas/document.py`**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    source_id: str
    url: str
    title: Optional[str]
    content_markdown: Optional[str]
    published_at: Optional[datetime]
    crawled_at: datetime
    content_hash: Optional[str]
    is_analysed: bool
```

- [ ] **Step 4: Create `backend/app/schemas/signal.py`**

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
    published_at: Optional[datetime]
    created_at: datetime
```

- [ ] **Step 5: Create `backend/app/schemas/digest.py`**

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class DigestRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    week_start: date
    week_end: date
    summary: Optional[str]
    key_signals: List[str]
    generated_at: datetime
    is_published: bool
```

- [ ] **Step 6: Create `backend/app/schemas/context.py`**

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ContextUpdate(BaseModel):
    company_name: Optional[str] = None
    short_description: Optional[str] = None
    target_industries: Optional[List[str]] = None
    target_segments: Optional[List[str]] = None
    core_capabilities: Optional[List[str]] = None
    strategic_priorities: Optional[List[str]] = None
    differentiators: Optional[List[str]] = None
    relevant_competitive_areas: Optional[List[str]] = None
    non_focus_areas: Optional[List[str]] = None


class ContextRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_name: Optional[str]
    short_description: Optional[str]
    target_industries: List[str]
    target_segments: List[str]
    core_capabilities: List[str]
    strategic_priorities: List[str]
    differentiators: List[str]
    relevant_competitive_areas: List[str]
    non_focus_areas: List[str]
    updated_at: datetime
```

- [ ] **Step 7: Update `backend/app/schemas/__init__.py`**

```python
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate
from app.schemas.document import DocumentRead
from app.schemas.signal import SignalRead
from app.schemas.digest import DigestRead
from app.schemas.context import ContextRead, ContextUpdate
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic v2 schemas for all entities"
```

---

## Task 7: FastAPI app + HTTP Basic Auth

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_auth.py`

```python
def test_unauthenticated_request_is_rejected(client):
    from fastapi.testclient import TestClient
    from app.main import app
    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/companies")
    assert response.status_code == 401


def test_authenticated_request_succeeds(client):
    response = client.get("/api/companies")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```
Expected: `ImportError` — `app.main` doesn't exist yet.

- [ ] **Step 3: Create `backend/app/main.py`**

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import secrets
from app.config import settings

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.auth_username)
    correct_password = secrets.compare_digest(credentials.password, settings.auth_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


app = FastAPI(
    title="WFM Market Intelligence Hub",
    version="1.0.0",
    dependencies=[Depends(verify_credentials)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import companies, sources, documents, signals, digests, context, crawl  # noqa: E402

app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(digests.router, prefix="/api/digests", tags=["digests"])
app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Create stub routers** (so main.py can import them — real implementation in later tasks)

Create `backend/app/routers/companies.py`:
```python
from fastapi import APIRouter
router = APIRouter()
```
Repeat the same stub content for: `sources.py`, `documents.py`, `signals.py`, `digests.py`, `context.py`, `crawl.py`.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/routers/
git commit -m "feat: add FastAPI app with HTTP Basic Auth and router stubs"
```

---

## Task 8: Companies router

**Files:**
- Modify: `backend/app/routers/companies.py`
- Create: `backend/tests/test_companies.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_companies.py`

```python
def test_list_companies_empty(client):
    response = client.get("/api/companies")
    assert response.status_code == 200
    assert response.json() == []


def test_create_company(client):
    payload = {"name": "ATOSS", "slug": "atoss", "type": "competitor", "website": "https://atoss.com"}
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "atoss"
    assert data["type"] == "competitor"
    assert "id" in data


def test_create_duplicate_slug_fails(client):
    payload = {"name": "ATOSS", "slug": "atoss-dup", "type": "competitor"}
    client.post("/api/companies", json=payload)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 409


def test_get_company_by_slug(client):
    client.post("/api/companies", json={"name": "ATOSS", "slug": "atoss-get", "type": "competitor"})
    response = client.get("/api/companies/atoss-get")
    assert response.status_code == 200
    assert response.json()["slug"] == "atoss-get"


def test_get_nonexistent_company(client):
    response = client.get("/api/companies/nonexistent")
    assert response.status_code == 404


def test_update_company(client):
    client.post("/api/companies", json={"name": "ATOSS", "slug": "atoss-upd", "type": "competitor"})
    response = client.put("/api/companies/atoss-upd", json={"description": "WFM vendor"})
    assert response.status_code == 200
    assert response.json()["description"] == "WFM vendor"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_companies.py -v
```
Expected: all fail with 404/422 — router is still a stub.

- [ ] **Step 3: Implement `backend/app/routers/companies.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate

router = APIRouter()


@router.get("", response_model=List[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    existing = db.query(Company).filter(Company.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{slug}", response_model=CompanyRead)
def get_company(slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{slug}", response_model=CompanyRead)
def update_company(slug: str, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_companies.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/companies.py backend/tests/test_companies.py
git commit -m "feat: add companies CRUD router"
```

---

## Task 9: Sources router

**Files:**
- Modify: `backend/app/routers/sources.py`
- Create: `backend/tests/test_sources.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_sources.py`

```python
import pytest


@pytest.fixture
def company(client):
    r = client.post("/api/companies", json={"name": "ATOSS", "slug": "atoss-src", "type": "competitor"})
    return r.json()


def test_list_sources_empty(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    assert response.json() == []


def test_create_source(client, company):
    payload = {"company_id": company["id"], "url": "https://atoss.com/news", "source_type": "news", "label": "News"}
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://atoss.com/news"
    assert data["is_active"] is True


def test_create_duplicate_url_fails(client, company):
    payload = {"company_id": company["id"], "url": "https://atoss.com/dup", "source_type": "blog"}
    client.post("/api/sources", json=payload)
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 409


def test_update_source(client, company):
    r = client.post("/api/sources", json={"company_id": company["id"], "url": "https://atoss.com/blog", "source_type": "blog"})
    source_id = r.json()["id"]
    response = client.put(f"/api/sources/{source_id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_delete_source(client, company):
    r = client.post("/api/sources", json={"company_id": company["id"], "url": "https://atoss.com/del", "source_type": "press"})
    source_id = r.json()["id"]
    response = client.delete(f"/api/sources/{source_id}")
    assert response.status_code == 204
    response = client.get("/api/sources")
    assert all(s["id"] != source_id for s in response.json())


def test_filter_sources_by_company(client, company):
    client.post("/api/sources", json={"company_id": company["id"], "url": "https://atoss.com/jobs", "source_type": "jobs"})
    response = client.get(f"/api/sources?company_id={company['id']}")
    assert response.status_code == 200
    assert all(s["company_id"] == company["id"] for s in response.json())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_sources.py -v
```
Expected: all fail — stub router.

- [ ] **Step 3: Implement `backend/app/routers/sources.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate

router = APIRouter()


@router.get("", response_model=List[SourceRead])
def list_sources(company_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Source)
    if company_id:
        query = query.filter(Source.company_id == company_id)
    return query.all()


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="URL already exists")
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.put("/{source_id}", response_model=SourceRead)
def update_source(source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_sources.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/sources.py backend/tests/test_sources.py
git commit -m "feat: add sources CRUD router"
```

---

## Task 10: Documents router

**Files:**
- Modify: `backend/app/routers/documents.py`
- Create: `backend/tests/test_documents.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_documents.py`

```python
import pytest
from app.models.document import Document


@pytest.fixture
def seed_document(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    company = Company(name="ATOSS", slug="atoss-doc", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/docs", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/docs/post-1",
        title="Test Post",
        content_markdown="## Hello",
        content_hash="abc123def456",
    )
    db_session.add(doc)
    db_session.commit()
    return doc


def test_list_documents(client, seed_document):
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_document_by_id(client, seed_document):
    response = client.get(f"/api/documents/{seed_document.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Post"
    assert response.json()["content_markdown"] == "## Hello"


def test_get_nonexistent_document(client):
    response = client.get("/api/documents/nonexistent-id")
    assert response.status_code == 404


def test_filter_documents_by_source(client, seed_document):
    response = client.get(f"/api/documents?source_id={seed_document.source_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["source_id"] == seed_document.source_id
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_documents.py -v
```
Expected: all fail.

- [ ] **Step 3: Implement `backend/app/routers/documents.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentRead

router = APIRouter()


@router.get("", response_model=List[DocumentRead])
def list_documents(source_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Document)
    if source_id:
        query = query.filter(Document.source_id == source_id)
    return query.order_by(Document.crawled_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_documents.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/documents.py backend/tests/test_documents.py
git commit -m "feat: add documents read-only router"
```

---

## Task 11: Signals router

**Files:**
- Modify: `backend/app/routers/signals.py`
- Create: `backend/tests/test_signals.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_signals.py`

```python
import pytest
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType


@pytest.fixture
def seed_signals(db_session):
    company = Company(name="ATOSS", slug="atoss-sig", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/sigs", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/sigs/1", content_hash="h1")
    db_session.add(doc)
    db_session.commit()
    s1 = Signal(document_id=doc.id, company_id=company.id, title="AI Feature", signal_type=SignalType.ai_announcement, relevance_score=0.9)
    s2 = Signal(document_id=doc.id, company_id=company.id, title="Partnership", signal_type=SignalType.partnership, relevance_score=0.5)
    db_session.add_all([s1, s2])
    db_session.commit()
    return company, s1, s2


def test_list_signals(client, seed_signals):
    response = client.get("/api/signals")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_by_company(client, seed_signals):
    company, _, _ = seed_signals
    response = client.get(f"/api/signals?company_id={company.id}")
    assert response.status_code == 200
    assert all(s["company_id"] == company.id for s in response.json())


def test_filter_by_signal_type(client, seed_signals):
    response = client.get("/api/signals?signal_type=ai_announcement")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["signal_type"] == "ai_announcement"


def test_filter_by_min_relevance(client, seed_signals):
    response = client.get("/api/signals?min_relevance=0.8")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["relevance_score"] >= 0.8


def test_get_signal_by_id(client, seed_signals):
    _, s1, _ = seed_signals
    response = client.get(f"/api/signals/{s1.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "AI Feature"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_signals.py -v
```
Expected: all fail.

- [ ] **Step 3: Implement `backend/app/routers/signals.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.signal import Signal, SignalType
from app.schemas.signal import SignalRead

router = APIRouter()


@router.get("", response_model=List[SignalRead])
def list_signals(
    company_id: Optional[str] = None,
    signal_type: Optional[SignalType] = None,
    min_relevance: Optional[float] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Signal)
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_relevance is not None:
        query = query.filter(Signal.relevance_score >= min_relevance)
    return query.order_by(Signal.created_at.desc()).all()


@router.get("/{signal_id}", response_model=SignalRead)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_signals.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/signals.py backend/tests/test_signals.py
git commit -m "feat: add signals read router with filters"
```

---

## Task 12: Context router (singleton)

**Files:**
- Modify: `backend/app/routers/context.py`
- Create: `backend/tests/test_context.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_context.py`

```python
def test_get_context_creates_empty_singleton_on_first_call(client):
    response = client.get("/api/context")
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] is None
    assert data["target_industries"] == []


def test_update_context(client):
    payload = {
        "company_name": "WFM Corp",
        "target_industries": ["Retail", "Logistics"],
        "core_capabilities": ["WFM", "Analytics"],
    }
    response = client.put("/api/context", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "WFM Corp"
    assert data["target_industries"] == ["Retail", "Logistics"]


def test_context_is_singleton(client):
    client.put("/api/context", json={"company_name": "Corp A"})
    client.put("/api/context", json={"company_name": "Corp B"})
    response = client.get("/api/context")
    assert response.json()["company_name"] == "Corp B"


def test_partial_update_preserves_fields(client):
    client.put("/api/context", json={"company_name": "WFM", "target_industries": ["Retail"]})
    client.put("/api/context", json={"core_capabilities": ["Planning"]})
    response = client.get("/api/context")
    assert response.json()["company_name"] == "WFM"
    assert response.json()["core_capabilities"] == ["Planning"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_context.py -v
```
Expected: all fail.

- [ ] **Step 3: Implement `backend/app/routers/context.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.context import InternalCompanyContext
from app.schemas.context import ContextRead, ContextUpdate

router = APIRouter()


def _get_or_create_context(db: Session) -> InternalCompanyContext:
    ctx = db.query(InternalCompanyContext).first()
    if not ctx:
        ctx = InternalCompanyContext()
        db.add(ctx)
        db.commit()
        db.refresh(ctx)
    return ctx


@router.get("", response_model=ContextRead)
def get_context(db: Session = Depends(get_db)):
    return _get_or_create_context(db)


@router.put("", response_model=ContextRead)
def update_context(payload: ContextUpdate, db: Session = Depends(get_db)):
    ctx = _get_or_create_context(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ctx, field, value)
    db.commit()
    db.refresh(ctx)
    return ctx
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_context.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/context.py backend/tests/test_context.py
git commit -m "feat: add singleton context router"
```

---

## Task 13: Digests router

**Files:**
- Modify: `backend/app/routers/digests.py`
- Create: `backend/tests/test_digests.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_digests.py`

```python
import pytest
from datetime import date
from app.models.digest import WeeklyDigest


@pytest.fixture
def seed_digest(db_session):
    d = WeeklyDigest(
        week_start=date(2026, 4, 14),
        week_end=date(2026, 4, 20),
        summary="Big week in AI WFM.",
        key_signals=["signal-id-1", "signal-id-2"],
        is_published=True,
    )
    db_session.add(d)
    db_session.commit()
    return d


def test_list_digests(client, seed_digest):
    response = client.get("/api/digests")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_digest_by_id(client, seed_digest):
    response = client.get(f"/api/digests/{seed_digest.id}")
    assert response.status_code == 200
    assert response.json()["summary"] == "Big week in AI WFM."
    assert response.json()["key_signals"] == ["signal-id-1", "signal-id-2"]


def test_generate_digest(client):
    response = client.post("/api/digests/generate")
    assert response.status_code == 201
    data = response.json()
    assert "week_start" in data
    assert "week_end" in data
    assert isinstance(data["key_signals"], list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_digests.py -v
```
Expected: all fail.

- [ ] **Step 3: Implement `backend/app/routers/digests.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta
from app.database import get_db
from app.models.digest import WeeklyDigest
from app.models.signal import Signal
from app.schemas.digest import DigestRead

router = APIRouter()


@router.get("", response_model=List[DigestRead])
def list_digests(db: Session = Depends(get_db)):
    return db.query(WeeklyDigest).order_by(WeeklyDigest.week_start.desc()).all()


@router.get("/{digest_id}", response_model=DigestRead)
def get_digest(digest_id: str, db: Session = Depends(get_db)):
    digest = db.query(WeeklyDigest).filter(WeeklyDigest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest


@router.post("/generate", response_model=DigestRead, status_code=status.HTTP_201_CREATED)
def generate_digest(db: Session = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    signals = (
        db.query(Signal)
        .filter(Signal.created_at >= week_start)
        .order_by(Signal.relevance_score.desc())
        .limit(10)
        .all()
    )
    key_signal_ids = [s.id for s in signals]

    summary_parts = []
    for s in signals[:5]:
        summary_parts.append(f"- {s.title} ({s.signal_type.value}, relevance: {s.relevance_score:.1f})")
    summary = f"Week {week_start} – {week_end}. Top signals:\n" + "\n".join(summary_parts) if summary_parts else f"No signals for week {week_start}."

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
    return digest
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_digests.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/digests.py backend/tests/test_digests.py
git commit -m "feat: add digests router with weekly generation"
```

---

## Task 14: Crawler — Fetcher + Extractor

**Files:**
- Create: `backend/app/crawler/fetcher.py`
- Create: `backend/app/crawler/extractor.py`
- Create: `backend/tests/test_crawler.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_crawler.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from app.crawler.fetcher import fetch_url, FetchResult
from app.crawler.extractor import extract_content, ExtractionResult


def test_fetch_url_returns_html_on_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test Page</title></head><body><p>Hello</p></body></html>"
    mock_response.url = "https://example.com/page"

    with patch("app.crawler.fetcher.httpx.get", return_value=mock_response):
        result = fetch_url("https://example.com/page")

    assert isinstance(result, FetchResult)
    assert result.html == mock_response.text
    assert result.final_url == "https://example.com/page"
    assert result.status_code == 200


def test_fetch_url_returns_none_on_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = Exception("404")

    with patch("app.crawler.fetcher.httpx.get", side_effect=Exception("Connection error")):
        result = fetch_url("https://example.com/broken")

    assert result is None


def test_extract_content_from_html():
    html = """
    <html>
      <head><title>ATOSS News</title></head>
      <body>
        <nav>Navigation</nav>
        <main>
          <h1>New AI Feature Released</h1>
          <p>ATOSS released a new AI-powered scheduling module today.</p>
        </main>
        <footer>Footer</footer>
      </body>
    </html>
    """
    result = extract_content(html, url="https://atoss.com/news/ai")
    assert isinstance(result, ExtractionResult)
    assert result.title == "ATOSS News"
    assert "AI-powered scheduling" in result.markdown
    assert len(result.content_hash) == 64  # SHA-256 hex digest


def test_extract_sets_hash_based_on_content():
    html1 = "<html><body><p>Content A</p></body></html>"
    html2 = "<html><body><p>Content B</p></body></html>"
    r1 = extract_content(html1, url="https://example.com/1")
    r2 = extract_content(html2, url="https://example.com/2")
    assert r1.content_hash != r2.content_hash


def test_extract_same_content_same_hash():
    html = "<html><body><p>Same content</p></body></html>"
    r1 = extract_content(html, url="https://example.com/a")
    r2 = extract_content(html, url="https://example.com/b")
    assert r1.content_hash == r2.content_hash
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_crawler.py -v
```
Expected: `ImportError` — crawler modules don't exist.

- [ ] **Step 3: Create `backend/app/crawler/fetcher.py`**

```python
from dataclasses import dataclass
from typing import Optional
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


@dataclass
class FetchResult:
    html: str
    final_url: str
    status_code: int


def fetch_url(url: str, timeout: int = 15) -> Optional[FetchResult]:
    try:
        response = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return FetchResult(html=response.text, final_url=str(response.url), status_code=response.status_code)
    except Exception:
        return None
```

- [ ] **Step 4: Create `backend/app/crawler/extractor.py`**

```python
import hashlib
from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup
from markdownify import markdownify


@dataclass
class ExtractionResult:
    title: Optional[str]
    markdown: str
    content_hash: str


def extract_content(html: str, url: str = "") -> ExtractionResult:
    soup = BeautifulSoup(html, "html.parser")

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("body") or soup

    markdown = markdownify(str(main), heading_style="ATX", strip=["a"]).strip()
    markdown = "\n".join(line for line in markdown.splitlines() if line.strip())

    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    return ExtractionResult(title=title, markdown=markdown, content_hash=content_hash)
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_crawler.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/crawler/fetcher.py backend/app/crawler/extractor.py backend/tests/test_crawler.py
git commit -m "feat: add crawler fetcher and HTML-to-markdown extractor"
```

---

## Task 15: Crawler Pipeline (deduplication + orchestration)

**Files:**
- Create: `backend/app/crawler/pipeline.py`
- Extend: `backend/tests/test_crawler.py`

- [ ] **Step 1: Add pipeline tests to** `backend/tests/test_crawler.py`

Append to the existing test file:

```python
from app.crawler.pipeline import run_crawl_source


def test_run_crawl_source_saves_new_document(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document

    company = Company(name="ATOSS", slug="atoss-pipe", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/pipe", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()

    mock_fetch = MagicMock(return_value=MagicMock(
        html="<html><head><title>Test</title></head><body><p>New content</p></body></html>",
        final_url="https://atoss.com/pipe",
        status_code=200,
    ))

    with patch("app.crawler.pipeline.fetch_url", mock_fetch):
        result = run_crawl_source(source, db_session, analyse=False)

    assert result["new_documents"] == 1
    doc = db_session.query(Document).first()
    assert doc is not None
    assert doc.content_markdown is not None
    assert doc.source_id == source.id


def test_run_crawl_source_skips_duplicate(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document

    company = Company(name="ATOSS", slug="atoss-dup2", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/dup2", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()

    html = "<html><head><title>Same</title></head><body><p>Same content</p></body></html>"
    mock_fetch = MagicMock(return_value=MagicMock(html=html, final_url="https://atoss.com/dup2", status_code=200))

    with patch("app.crawler.pipeline.fetch_url", mock_fetch):
        run_crawl_source(source, db_session, analyse=False)
        result = run_crawl_source(source, db_session, analyse=False)

    assert result["new_documents"] == 0
    assert db_session.query(Document).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_crawler.py::test_run_crawl_source_saves_new_document -v
```
Expected: `ImportError` — pipeline doesn't exist.

- [ ] **Step 3: Create `backend/app/crawler/pipeline.py`**

```python
from typing import Dict
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.source import Source
from app.models.document import Document
from app.crawler.fetcher import fetch_url
from app.crawler.extractor import extract_content


def run_crawl_source(source: Source, db: Session, analyse: bool = True) -> Dict:
    result = {"source_id": source.id, "new_documents": 0, "skipped": 0, "errors": 0}

    fetch_result = fetch_url(source.url)
    if fetch_result is None:
        result["errors"] += 1
        return result

    extraction = extract_content(fetch_result.html, url=fetch_result.final_url)

    existing = db.query(Document).filter(Document.content_hash == extraction.content_hash).first()
    if existing:
        result["skipped"] += 1
    else:
        doc = Document(
            source_id=source.id,
            url=fetch_result.final_url,
            title=extraction.title,
            content_markdown=extraction.markdown,
            content_raw_html=fetch_result.html,
            content_hash=extraction.content_hash,
            crawled_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        db.commit()
        result["new_documents"] += 1

        if analyse:
            from app.analyser.pipeline import analyse_document
            db.refresh(doc)
            analyse_document(doc, source.company_id, db)

    source.last_crawled_at = datetime.now(timezone.utc)
    db.commit()

    return result
```

- [ ] **Step 4: Run all crawler tests**

```bash
cd backend && python -m pytest tests/test_crawler.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/pipeline.py backend/tests/test_crawler.py
git commit -m "feat: add crawl pipeline with deduplication"
```

---

## Task 16: Analyser — LLM Client + Prompts + Parser

**Files:**
- Create: `backend/app/analyser/client.py`
- Create: `backend/app/analyser/prompts.py`
- Create: `backend/app/analyser/parser.py`
- Create: `backend/app/analyser/pipeline.py`
- Create: `backend/tests/test_analyser.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_analyser.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from app.analyser.prompts import build_analysis_prompt
from app.analyser.parser import parse_llm_response, SignalData
from app.models.signal import SignalType


def test_build_prompt_includes_markdown_and_context():
    context = {
        "company_name": "WFM Corp",
        "target_industries": ["Retail"],
        "core_capabilities": ["WFM", "Analytics"],
        "differentiators": ["Real-time planning"],
    }
    prompt = build_analysis_prompt(
        markdown="## New AI Feature\nATOSS releases AI scheduling.",
        context=context,
    )
    assert "WFM Corp" in prompt
    assert "ATOSS releases AI scheduling" in prompt
    assert "Retail" in prompt
    assert "Real-time planning" in prompt


def test_parse_valid_llm_response():
    raw = """
    {
      "title": "ATOSS AI Scheduling Launch",
      "signal_type": "ai_announcement",
      "topic": "AI in WFM",
      "summary": "ATOSS launched a new AI scheduling module.",
      "why_it_matters": "Directly competes with our core capability.",
      "relevance_score": 0.9,
      "confidence_score": 0.85
    }
    """
    result = parse_llm_response(raw)
    assert isinstance(result, SignalData)
    assert result.title == "ATOSS AI Scheduling Launch"
    assert result.signal_type == SignalType.ai_announcement
    assert result.relevance_score == 0.9


def test_parse_llm_response_with_json_in_markdown_fence():
    raw = """
    Here is my analysis:
    ```json
    {
      "title": "Partnership Announced",
      "signal_type": "partnership",
      "topic": "Ecosystem",
      "summary": "New SAP partnership.",
      "why_it_matters": "SAP is a key integration target for us.",
      "relevance_score": 0.7,
      "confidence_score": 0.8
    }
    ```
    """
    result = parse_llm_response(raw)
    assert result.title == "Partnership Announced"
    assert result.signal_type == SignalType.partnership


def test_parse_invalid_response_returns_fallback():
    result = parse_llm_response("This is not JSON at all.")
    assert isinstance(result, SignalData)
    assert result.signal_type == SignalType.other
    assert result.relevance_score == 0.1


def test_analyse_document_creates_signal(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType
    from app.models.document import Document
    from app.models.signal import Signal
    from app.analyser.pipeline import analyse_document

    company = Company(name="ATOSS", slug="atoss-anal", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/anal", source_type=SourceType.news)
    db_session.add(source)
    db_session.commit()
    doc = Document(source_id=source.id, url="https://atoss.com/anal/1", content_markdown="## AI Feature", content_hash="h_anal")
    db_session.add(doc)
    db_session.commit()

    mock_signal = SignalData(
        title="AI Feature",
        signal_type=SignalType.ai_announcement,
        topic="AI",
        summary="New AI feature.",
        why_it_matters="Competes with us.",
        relevance_score=0.9,
        confidence_score=0.85,
    )

    with patch("app.analyser.pipeline.call_llm", return_value='{"title":"AI Feature","signal_type":"ai_announcement","topic":"AI","summary":"New AI feature.","why_it_matters":"Competes.","relevance_score":0.9,"confidence_score":0.85}'):
        analyse_document(doc, company.id, db_session)

    signal = db_session.query(Signal).first()
    assert signal is not None
    assert signal.document_id == doc.id
    assert doc.is_analysed is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_analyser.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Create `backend/app/analyser/prompts.py`**

```python
from typing import Dict, Any


def build_analysis_prompt(markdown: str, context: Dict[str, Any]) -> str:
    ctx_str = f"""
Company: {context.get('company_name', 'N/A')}
Description: {context.get('short_description', 'N/A')}
Target Industries: {', '.join(context.get('target_industries', []))}
Target Segments: {', '.join(context.get('target_segments', []))}
Core Capabilities: {', '.join(context.get('core_capabilities', []))}
Strategic Priorities: {', '.join(context.get('strategic_priorities', []))}
Differentiators: {', '.join(context.get('differentiators', []))}
Relevant Competitive Areas: {', '.join(context.get('relevant_competitive_areas', []))}
Non-Focus Areas: {', '.join(context.get('non_focus_areas', []))}
""".strip()

    return f"""You are a market intelligence analyst for the following company:

{ctx_str}

Analyze the following competitor/market content and extract a structured signal.

CONTENT:
{markdown[:4000]}

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "title": "short descriptive title (max 100 chars)",
  "signal_type": one of: product_update | ai_announcement | partnership | positioning_change | target_market_change | event_or_thought_leadership | hiring_signal | other,
  "topic": "main topic or theme (max 60 chars)",
  "summary": "2-3 sentence factual summary of the content",
  "why_it_matters": "1-2 sentences explaining strategic relevance to our company specifically",
  "relevance_score": float between 0.0 (irrelevant) and 1.0 (highly relevant to us),
  "confidence_score": float between 0.0 (uncertain) and 1.0 (very confident in analysis)
}}

No markdown fences, no extra text. Only the JSON object."""
```

- [ ] **Step 4: Create `backend/app/analyser/parser.py`**

```python
import json
import re
from dataclasses import dataclass
from typing import Optional
from app.models.signal import SignalType


@dataclass
class SignalData:
    title: str
    signal_type: SignalType
    topic: Optional[str]
    summary: Optional[str]
    why_it_matters: Optional[str]
    relevance_score: float
    confidence_score: float


def parse_llm_response(raw: str) -> SignalData:
    try:
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)

        json_match2 = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match2:
            raw = json_match2.group(0)

        data = json.loads(raw)

        signal_type_str = data.get("signal_type", "other")
        try:
            signal_type = SignalType(signal_type_str)
        except ValueError:
            signal_type = SignalType.other

        return SignalData(
            title=str(data.get("title", "Untitled"))[:500],
            signal_type=signal_type,
            topic=data.get("topic"),
            summary=data.get("summary"),
            why_it_matters=data.get("why_it_matters"),
            relevance_score=float(data.get("relevance_score", 0.5)),
            confidence_score=float(data.get("confidence_score", 0.5)),
        )
    except Exception:
        return SignalData(
            title="Parse error",
            signal_type=SignalType.other,
            topic=None,
            summary=None,
            why_it_matters=None,
            relevance_score=0.1,
            confidence_score=0.1,
        )
```

- [ ] **Step 5: Create `backend/app/analyser/client.py`**

```python
from app.config import settings


def call_llm(prompt: str) -> str:
    if settings.llm_provider == "ollama":
        return _call_ollama(prompt)
    return _call_claude(prompt)


def _call_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_ollama(prompt: str) -> str:
    import httpx
    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"]
```

- [ ] **Step 6: Create `backend/app/analyser/pipeline.py`**

```python
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.signal import Signal
from app.models.context import InternalCompanyContext
from app.analyser.client import call_llm
from app.analyser.prompts import build_analysis_prompt
from app.analyser.parser import parse_llm_response


def analyse_document(doc: Document, company_id: str, db: Session) -> None:
    if not doc.content_markdown:
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
    )
    db.add(signal)

    doc.is_analysed = True
    db.commit()
```

- [ ] **Step 7: Run all analyser tests**

```bash
cd backend && python -m pytest tests/test_analyser.py -v
```
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/analyser/ backend/tests/test_analyser.py
git commit -m "feat: add LLM analyser with Claude/Ollama client, prompt builder, and parser"
```

---

## Task 17: Crawl router

**Files:**
- Modify: `backend/app/routers/crawl.py`
- Create: `backend/tests/test_crawl_router.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_crawl_router.py`

```python
import pytest
from unittest.mock import patch
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType


@pytest.fixture
def seed_source(db_session):
    company = Company(name="ATOSS", slug="atoss-crawl", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(company_id=company.id, url="https://atoss.com/crawl-test", source_type=SourceType.news, is_active=True)
    db_session.add(source)
    db_session.commit()
    return source


def test_crawl_all_sources(client, seed_source):
    mock_result = {"source_id": seed_source.id, "new_documents": 1, "skipped": 0, "errors": 0}
    with patch("app.routers.crawl.run_crawl_source", return_value=mock_result):
        response = client.post("/api/crawl/run")
    assert response.status_code == 200
    data = response.json()
    assert data["sources_processed"] == 1
    assert data["results"][0]["new_documents"] == 1


def test_crawl_single_source(client, seed_source):
    mock_result = {"source_id": seed_source.id, "new_documents": 2, "skipped": 0, "errors": 0}
    with patch("app.routers.crawl.run_crawl_source", return_value=mock_result):
        response = client.post(f"/api/crawl/run/{seed_source.id}")
    assert response.status_code == 200
    assert response.json()["new_documents"] == 2


def test_crawl_nonexistent_source(client):
    response = client.post("/api/crawl/run/nonexistent-id")
    assert response.status_code == 404


def test_crawl_skips_inactive_sources(client, db_session, seed_source):
    seed_source.is_active = False
    db_session.commit()
    with patch("app.routers.crawl.run_crawl_source") as mock_crawl:
        response = client.post("/api/crawl/run")
    mock_crawl.assert_not_called()
    assert response.json()["sources_processed"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_crawl_router.py -v
```
Expected: all fail — stub router.

- [ ] **Step 3: Implement `backend/app/routers/crawl.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models.source import Source
from app.crawler.pipeline import run_crawl_source

router = APIRouter()


@router.post("/run")
def crawl_all_sources(db: Session = Depends(get_db)) -> Dict[str, Any]:
    active_sources = db.query(Source).filter(Source.is_active == True).all()  # noqa: E712
    results = []
    for source in active_sources:
        result = run_crawl_source(source, db, analyse=True)
        results.append(result)
    return {"sources_processed": len(active_sources), "results": results}


@router.post("/run/{source_id}")
def crawl_single_source(source_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return run_crawl_source(source, db, analyse=True)
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && python -m pytest tests/test_crawl_router.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest -v
```
Expected: all tests pass (no failures).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/crawl.py backend/tests/test_crawl_router.py
git commit -m "feat: add crawl router wiring pipeline to API endpoints"
```

---

## Task 18: Push to GitHub + smoke test against real DB

- [ ] **Step 1: Push all commits to GitHub**

```bash
git push -u origin main
```

- [ ] **Step 2: Start the dev stack**

```bash
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY, AUTH_USERNAME=admin, AUTH_PASSWORD=yourpass
docker compose -f docker-compose.dev.yml up --build
```
Expected: backend starts on :8000, database on :5432.

- [ ] **Step 3: Run Alembic migrations inside the container**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```
Expected: migration applied.

- [ ] **Step 4: Smoke test the API**

```bash
# Health check
curl http://localhost:8000/api/health

# Auth check (should fail)
curl http://localhost:8000/api/companies
# Expected: {"detail":"Not authenticated"}

# Auth check (should succeed)
curl -u admin:yourpass http://localhost:8000/api/companies
# Expected: []

# Create a company
curl -u admin:yourpass -X POST http://localhost:8000/api/companies \
  -H "Content-Type: application/json" \
  -d '{"name":"ATOSS","slug":"atoss","type":"competitor","website":"https://atoss.com"}'

# Create a source
curl -u admin:yourpass -X POST http://localhost:8000/api/sources \
  -H "Content-Type: application/json" \
  -d '{"company_id":"<id from above>","url":"https://www.atoss.com/de","source_type":"product","label":"Homepage"}'

# Trigger crawl
curl -u admin:yourpass -X POST http://localhost:8000/api/crawl/run
```

- [ ] **Step 5: Check API docs**

Open `http://localhost:8000/docs` in browser — all endpoints should be listed and testable.

- [ ] **Step 6: Final commit if any fixes were needed**

```bash
git add -A && git commit -m "fix: smoke test corrections after integration run" # only if needed
git push
```

---

## Self-Review

**Spec Coverage Check:**

| Spec Requirement | Task |
|---|---|
| Source Management (5 competitors, 2 market, multiple URLs) | Tasks 8, 9 |
| Crawling / Ingestion (httpx, HTML→Markdown, hash dedup) | Tasks 14, 15 |
| KI-Analyse (summary, signal_type, topic, relevance, why_it_matters) | Task 16 |
| Signal types (all 8 defined) | Task 3 (SignalType enum) |
| Persistence (all 6 entities) | Tasks 3, 4 |
| Company Context (singleton, all 9 fields) | Tasks 3, 12 |
| Weekly Digest (aggregation, generate endpoint) | Tasks 3, 13 |
| HTTP Basic Auth | Task 7 |
| Claude API / Ollama switching | Task 16 |
| Markdown document storage | Task 14 (extractor) |
| Docker Compose (dev + prod) | Task 1 |

**All requirements covered. No placeholders. Types consistent across tasks.**
