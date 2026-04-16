# WFM Market Intelligence Hub — Claude.md

## Project Overview
Internal competitive intelligence tool. Crawls competitor/market websites → extracts Markdown → deduplicates → analyzes with Claude/Ollama → persists structured signals scored against internal company context.

## Tech Stack
- Python 3.12, FastAPI, SQLAlchemy 2.0 (sync), Alembic, PostgreSQL
- httpx + BeautifulSoup4 + markdownify for crawling
- Anthropic SDK / Ollama for LLM analysis
- pytest + SQLite (tests), Docker Compose (dev + prod)
- Frontend: React 18 + TypeScript + Vite (not yet built)

## Key Commands
```bash
# Dev stack
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Tests
cd backend && python -m pytest tests/ -v

# Migrations
cd backend && alembic revision --autogenerate -m "description"
cd backend && alembic upgrade head
```

## Architecture
- `backend/app/main.py` — FastAPI app, HTTP Basic Auth (global dep), CORS, router mounts
- `backend/app/models/` — 6 entities: Company, Source, Document, Signal, WeeklyDigest, InternalCompanyContext
- `backend/app/schemas/` — Pydantic v2 schemas (Create/Read/Update per entity)
- `backend/app/routers/` — CRUD endpoints under `/api/`
- `backend/app/crawler/` — fetcher (httpx), extractor (HTML→Markdown+SHA256 hash), pipeline (dedup + orchestration)
- `backend/app/analyser/` — client (Claude/Ollama switch), prompts, parser (JSON→SignalData), pipeline (doc→signal)
- `backend/app/database.py` — SQLAlchemy engine, SessionLocal, Base, get_db
- `backend/app/config.py` — pydantic-settings from .env

## API Endpoints
All under `/api/`, all require HTTP Basic Auth:
- Companies: GET/POST, GET/PUT by slug
- Sources: GET/POST, PUT/DELETE by id, filter by company_id
- Documents: GET list (filter by source_id), GET by id (read-only)
- Signals: GET list (filter by company_id, signal_type, min_relevance), GET by id
- Digests: GET list, GET by id, POST /generate
- Context: GET (singleton auto-create), PUT (partial update)
- Crawl: POST /run (all active sources), POST /run/:source_id

## Data Flow
1. Admin triggers crawl → `POST /api/crawl/run`
2. Fetcher gets HTML via httpx
3. Extractor cleans HTML → Markdown, computes SHA-256 hash
4. Deduplicator: if hash exists, skip; else save Document
5. Analyser: sends Markdown + InternalCompanyContext to LLM
6. Parser: extracts SignalData JSON → persists Signal with relevance/confidence scores

## Models
- Company (slug unique, type: competitor|market_source)
- Source (url unique, belongs to Company, type: news|blog|product|press|jobs)
- Document (url unique, content_hash for dedup, is_analysed flag)
- Signal (8 types, relevance/confidence scores, linked to Document + Company)
- WeeklyDigest (aggregation of weekly top signals)
- InternalCompanyContext (singleton: target_industries, capabilities, differentiators, etc.)

## Environment
- DB port exposed on 5435 (host), 5432 (container-internal)
- `ANTHROPIC_API_KEY` required for Claude analysis
- `LLM_PROVIDER=claude|ollama` switches LLM backend

## Testing
- conftest.py uses SQLite with function-scoped fixtures
- `db_session` fixture for direct DB access, `client` fixture for API tests with auth
- 51 tests across: models, auth, companies, sources, documents, signals, context, digests, crawler, analyser, crawl_router

## Known Issues
- NUL bytes in HTML content: stripped in extractor.py and pipeline.py
- Alembic env.py reads DATABASE_URL from app config, not alembic.ini
- Crawl pipeline calls analyser inline; LLM errors cause 500 (should add try/except)