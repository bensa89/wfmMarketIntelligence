# WFM Market Intelligence Hub — Design Spec
**Date:** 2026-04-16  
**Status:** Approved

---

## 1. Produktziel

Internes Tool zur kontinuierlichen Beobachtung von 5 definierten Wettbewerbern und 2 Markt-/Branchenwebseiten. Das System erkennt neue externe Signale, speichert sie strukturiert, bewertet sie relativ zum eigenen Unternehmenskontext und stellt die Erkenntnisse in einem klaren internen Frontend dar.

**Kernprinzip:** Nicht nur News sammeln, sondern Relevanz bewerten — mit Bezug auf den internen Company Context.

---

## 2. Architektur

### Stack
- **Backend:** Python 3.12 · FastAPI · SQLAlchemy · Alembic
- **Frontend:** React 18 · TypeScript · Vite
- **Datenbank:** PostgreSQL
- **Crawling:** httpx + BeautifulSoup4 + markdownify
- **LLM:** Claude API (Anthropic, Default) / Ollama (konfigurierbar per ENV)
- **Auth:** HTTP Basic Auth (FastAPI)
- **Deployment:** Docker Compose (lokal macOS → LXC Proxmox)

### Services (Docker Compose)
```
backend    FastAPI :8000
frontend   Nginx :80 (prod) / Vite :5173 (dev)
db         PostgreSQL :5432
```

### Datenfluss
```
Admin triggert Crawl (POST /api/crawl/run)
  → Crawler holt konfigurierte URLs (httpx)
  → Extractor bereinigt HTML → Markdown (markdownify)
  → Deduplicator prüft content_hash (SHA-256)
  → Neue Dokumente in DB gespeichert
  → Analyser sendet Dokument + Company Context an LLM
  → LLM gibt strukturiertes Signal zurück (JSON)
  → Signal in DB persistiert
  → Frontend zeigt Signale gefiltert und sortiert
```

### ENV-Konfiguration
```
ANTHROPIC_API_KEY
LLM_PROVIDER=claude|ollama
OLLAMA_BASE_URL=http://localhost:11434
DATABASE_URL=postgresql://user:pass@db:5432/wfmintel
AUTH_USERNAME
AUTH_PASSWORD
```

---

## 3. Datenmodell

### Company
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID PK | |
| name | string | |
| slug | string unique | URL-freundlicher Bezeichner |
| type | enum | `competitor` \| `market_source` |
| description | text | |
| website | string | |
| created_at | timestamp | |

### Source
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID PK | |
| company_id | FK → Company | |
| url | string unique | Zu crawlende URL |
| label | string | z.B. "News", "Blog", "Presse" |
| source_type | enum | `news` \| `blog` \| `product` \| `press` \| `jobs` |
| is_active | bool | |
| last_crawled_at | timestamp? | |
| created_at | timestamp | |

### Document
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID PK | |
| source_id | FK → Source | |
| url | string unique | Konkrete Dokument-URL |
| title | string | |
| content_markdown | text | Bereinigter Inhalt als Markdown ✨ |
| content_raw_html | text | Original-HTML |
| published_at | timestamp? | |
| crawled_at | timestamp | |
| content_hash | string | SHA-256 für Duplikatserkennung |
| is_analysed | bool | |

### Signal
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID PK | |
| document_id | FK → Document | Vollständige Rückverfolgbarkeit |
| company_id | FK → Company | |
| title | string | |
| signal_type | enum | s.u. |
| topic | string | |
| summary | text | KI-generierte Zusammenfassung |
| why_it_matters | text | Bewertung aus Unternehmenssicht |
| relevance_score | float 0–1 | |
| confidence_score | float 0–1 | |
| published_at | timestamp? | |
| created_at | timestamp | |

**Signal-Typen:**
`product_update` · `ai_announcement` · `partnership` · `positioning_change` · `target_market_change` · `event_or_thought_leadership` · `hiring_signal` · `other`

### WeeklyDigest
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID PK | |
| week_start | date | |
| week_end | date | |
| summary | text | KI-generierte Wochenzusammenfassung |
| key_signals | JSON | Array von Signal-IDs |
| generated_at | timestamp | |
| is_published | bool | |

### InternalCompanyContext
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID PK | |
| company_name | string | |
| short_description | text | |
| target_industries | JSON | Array of strings |
| target_segments | JSON | Array of strings |
| core_capabilities | JSON | Array of strings |
| strategic_priorities | JSON | Array of strings |
| differentiators | JSON | Array of strings |
| relevant_competitive_areas | JSON | Array of strings |
| non_focus_areas | JSON | Array of strings |
| updated_at | timestamp | |

> **Singleton:** Es gibt immer genau einen InternalCompanyContext-Eintrag. `PUT /api/context` überschreibt diesen. Beim ersten Start wird ein leerer Eintrag angelegt.

---

## 4. API-Endpunkte

```
GET    /api/companies
POST   /api/companies
GET    /api/companies/:slug
PUT    /api/companies/:slug

GET    /api/sources
POST   /api/sources
PUT    /api/sources/:id
DELETE /api/sources/:id

GET    /api/documents
GET    /api/documents/:id

GET    /api/signals
GET    /api/signals/:id
GET    /api/signals?company=:slug&type=:type&min_relevance=0.5&from=2026-01-01

GET    /api/digests
GET    /api/digests/:id
POST   /api/digests/generate

GET    /api/context
PUT    /api/context

POST   /api/crawl/run          # Manueller Crawl-Trigger (alle aktiven Sources)
POST   /api/crawl/run/:source_id  # Einzelne Source crawlen
```

Alle Endpunkte gesichert via HTTP Basic Auth.

---

## 5. KI-Analyse

### LLM-Aufruf pro Dokument
Das Analyser-Modul sendet an das konfigurierte LLM:
1. Den Markdown-Inhalt des Dokuments
2. Den vollständigen InternalCompanyContext

### Erwartetes Output-Schema (JSON)
```json
{
  "title": "string",
  "signal_type": "product_update|...",
  "topic": "string",
  "summary": "string (2-3 Sätze)",
  "why_it_matters": "string (aus Sicht unseres Unternehmens)",
  "relevance_score": 0.0–1.0,
  "confidence_score": 0.0–1.0
}
```

### LLM-Provider-Switching
```python
# config.py
LLM_PROVIDER = "claude"  # oder "ollama"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"  # Default: kostengünstig
OLLAMA_MODEL = "llama3"
```

---

## 6. Frontend-Seiten

| Route | Seite | Inhalt |
|-------|-------|--------|
| `/` | Dashboard | KPI-Cards, neueste Signale (alle Quellen), Filter |
| `/competitors` | Competitor List | Liste aller Wettbewerber mit Signal-Count |
| `/competitors/:slug` | Competitor Detail | Alle Signale eines Wettbewerbers, Timeline |
| `/trends` | Market Trends | Signale aus market_source-Quellen, Themen-Cluster |
| `/digest` | Weekly Digest | Wochenübersichten, generierbar per Button |
| `/admin/sources` | Sources Admin | CRUD für Companies + Sources, Crawl-Trigger |
| `/context` | Company Context | Anzeige + Bearbeitung des InternalCompanyContext |

### UI-Prinzipien
- Dark Theme
- Datendicht, keine Marketing-Ästhetik
- Signal-Cards: Typ-Farbe · Relevance-Score (grün ≥0.7 / gelb ≥0.4 / rot <0.4)
- Filterbar nach: Wettbewerber · Signaltyp · Zeitraum · Mindestrelevanz
- Drilldown: Signal → Dokument → Markdown-Rohinhalt

---

## 7. Projektstruktur

```
wfmMarketIntelligence/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/          # company, source, document, signal, digest, context
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── routers/         # companies, sources, documents, signals, digests, context, crawl
│   │   ├── crawler/         # fetcher, extractor, deduplicator
│   │   └── analyser/        # client, prompts, parser
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, CompetitorList, CompetitorDetail, MarketTrends, WeeklyDigest, SourcesAdmin, CompanyContext
│   │   ├── components/      # SignalCard, FilterBar, RelevanceScore, MarkdownViewer
│   │   ├── api/             # client.ts (fetch wrapper mit Basic Auth)
│   │   └── types/           # TypeScript interfaces
│   ├── vite.config.ts
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml        # Prod
├── docker-compose.dev.yml    # Dev
├── .env.example
└── .gitignore
```

---

## 8. Deployment

### Lokal (macOS)
```bash
cp .env.example .env        # API Keys + Auth eintragen
docker compose -f docker-compose.dev.yml up
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

### Proxmox LXC
```bash
docker compose up -d
# Frontend via Nginx auf Port 80
# Optionaler Reverse Proxy (Nginx/Traefik) für HTTPS
```

---

## 9. V1 Scope-Grenzen (bewusst ausgeklammert)

- Kein automatisches Scheduling (manueller Crawl-Trigger)
- Kein Rich-Text-Editor für Company Context (JSON-Felder via einfachem Formular)
- Keine Benutzerverwaltung (ein Admin-Account via ENV)
- Kein Playwright / JS-Rendering (httpx reicht für Gatsby/SSR-Seiten)
- Keine interne Knowledge Base / Obsidian-Integration (Architektur vorbereitet)
