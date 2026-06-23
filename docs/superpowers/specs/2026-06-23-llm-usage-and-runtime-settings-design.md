# LLM Token-Usage-Tracking & Runtime-Settings — Design

## Problem

1. Es gibt keine Sichtbarkeit, wie viele Tokens/Kosten die LLM-Aufrufe (Claude/Ollama/Opencode) über alle Pipelines (Analyser, Assessor, Synthesizer, Digester, Searcher-Query-Generator) verursachen.
2. Tuning-Settings (Modellwahl, Thresholds, Concurrency) liegen aktuell nur in `.env` / GitHub-Variablen. Um sie zu ändern, ist ein Redeploy nötig. Da häufig deployed wird, dürfen Laufzeit-Änderungen nicht durch das nächste Deployment überschrieben werden.

Beide Features bekommen einen eigenen Tab im Admin-Bereich, sind aber unabhängig implementierbar.

## Feature 1: Token-Usage-Tracking

### Datenmodell

Neue Tabelle `llm_call` (`backend/app/models/llm_call.py`):

| Spalte | Typ | Hinweis |
|---|---|---|
| id | PK | |
| created_at | datetime (UTC) | |
| caller | string | Wert aus `call_llm(caller=...)`, z.B. "analyser", "assessor", "synthesizer" |
| provider | string | "claude" \| "ollama" \| "opencode" |
| model | string | z.B. "claude-haiku-4-5-20251001" |
| input_tokens | int | |
| output_tokens | int | |
| estimated | bool | true, falls der Provider keine exakten Counts liefert (Fallback-Schätzung über Zeichenlänge) |
| duration_ms | int | bereits heute lokal gemessen in `call_llm`, nur noch persistiert |

Neue Tabelle `llm_model_price` (`backend/app/models/llm_model_price.py`):

| Spalte | Typ | Hinweis |
|---|---|---|
| model | string, PK | |
| input_price_per_1m | float | USD pro 1M Input-Tokens |
| output_price_per_1m | float | USD pro 1M Output-Tokens |

Kosten werden **nicht** beim Call eingefroren, sondern bei jeder Anzeige live aus der aktuellen `llm_model_price`-Tabelle berechnet (`tokens / 1_000_000 * price`). Modelle ohne Preiseintrag zeigen Kosten als "—" an (z.B. lokales Ollama = 0, falls nicht hinterlegt).

### Erfassung

`call_llm()` in `backend/app/analyser/client.py` ist der einzige Aufrufpunkt für alle Provider. Nach jedem Call:

- **Claude**: `message.usage.input_tokens` / `message.usage.output_tokens` — exakt.
- **Ollama**: Response enthält bei `stream: False` bereits `prompt_eval_count` / `eval_count` — exakt.
- **Opencode** (Streaming, OpenAI-kompatibel): Request bekommt `stream_options={"include_usage": True}`; letzter Chunk enthält ggf. `usage`. Liefert der Provider das nicht, wird die Tokenzahl aus `len(prompt) / 4` (Input) und `len(response) / 4` (Output) geschätzt und `estimated=True` gesetzt.

Der `LlmCall`-Row wird direkt in `call_llm()` über eine kurzlebige `SessionLocal()`-Instanz geschrieben (analog zu anderen Modulen, die ad-hoc Sessions öffnen). Schreibfehler dürfen den eigentlichen LLM-Call nicht crashen lassen — Logging-Fehler werden abgefangen und nur als `logger.warning` ausgegeben.

### API

Neuer Router `backend/app/routers/llm_usage.py`, mit Auth wie alle anderen `/api/`-Routen:

- `GET /api/llm-usage/summary?range=today|7d|30d` → Gesamtsumme Tokens + Kosten für den Zeitraum, je für `range` und für "all time".
- `GET /api/llm-usage/timeseries?range=30d` → Tagesweise Tokens/Kosten für Chart.
- `GET /api/llm-usage/breakdown?range=30d` → Aufschlüsselung nach `caller` × `provider` × `model` mit Summen.
- `GET /api/llm-usage/prices` / `PUT /api/llm-usage/prices/{model}` → Preistabelle lesen/editieren.

### Frontend

Neue Seite `frontend/src/pages/LlmUsageAdmin.tsx`, eingebunden in die Admin-Navigation neben `LogsAdmin.tsx`:

- Kacheln: Tokens & Kosten für heute / 7 Tage / 30 Tage / gesamt.
- Zeitverlauf-Chart (Tokens oder Kosten, Zeitraum umschaltbar) — wiederverwendet vorhandene Chart-Komponenten aus dem Dashboard.
- Breakdown-Tabelle nach Caller/Provider/Modell, sortierbar.
- Editierbare Preistabelle (Modell, Input-$/1M, Output-$/1M).

## Feature 2: Runtime-Settings

### Überschreibbare Felder

Aus `backend/app/config.py` werden folgende Felder DB-overridable (Tuning/Verhalten, keine Secrets):

`llm_provider`, `claude_model`, `ollama_base_url`, `ollama_model`, `opencode_model`, `opencode_base_url`, `discovery_depth`, `js_rendering_enabled`, `search_relevance_threshold`, `search_queries_per_company`, `assessment_threshold`, `crawl_concurrency`, `discovery_concurrency`, `analysis_concurrency`

Bleiben ausschließlich in `.env`/GitHub-Variablen (Secrets/Infra, nicht in der UI editierbar):

`database_url`, `auth_username`, `auth_password`, `anthropic_api_key`, `opencode_api_key`, `tavily_api_key`, `app_base_url`

### Datenmodell

Neue Tabelle `app_setting` (`backend/app/models/app_setting.py`):

| Spalte | Typ | Hinweis |
|---|---|---|
| key | string, PK | muss einer der 14 überschreibbaren Feldnamen sein |
| value | string | Rohwert, wird beim Laden in den passenden Python-Typ (str/int/float/bool) gemäß `Settings`-Annotation gecastet |
| updated_at | datetime | |

Existiert kein Row für einen Key, gilt der `.env`-Default aus `Settings`.

### Anwendungsmechanismus

Backend läuft mit einem einzigen uvicorn-Worker-Prozess (kein `--workers`-Flag in Dev- oder Prod-Dockerfile) — daher reicht ein In-Memory-Override ohne Multi-Prozess-Cache-Invalidierung.

- **Beim App-Start** (FastAPI startup hook in `main.py`): alle Rows aus `app_setting` laden, gecastet per `setattr(settings, row.key, casted_value)` auf das bestehende `settings`-Singleton (`backend/app/config.py`) anwenden.
- **Bei Änderung über die UI**: `PUT /api/admin/settings/{key}` schreibt/aktualisiert den `app_setting`-Row UND wendet den Wert sofort per `setattr` auf das laufende `settings`-Objekt an. Kein Neustart nötig.
- **Bei Reset**: `DELETE /api/admin/settings/{key}` löscht den Row und setzt `settings.<key>` per `setattr` zurück auf den `.env`/GitHub-Variablen-Default (neu aus einer frischen `Settings()`-Instanz gelesen).

Da die 16 bestehenden Call-Sites weiterhin einfach `settings.xxx` lesen, sind **keine Änderungen an Pipeline-Code** nötig — der Override ist transparent.

**Deployment-Sicherheit**: `app_setting` liegt in Postgres, nicht im Container. Jedes Redeploy lädt beim Start zuerst die frischen `.env`/GitHub-Variablen-Defaults in `Settings()`, dann überschreibt der Startup-Hook diese mit den `app_setting`-Werten aus der DB. Dadurch überlebt eine Laufzeit-Änderung jedes Deployment, solange dieselbe Datenbank verwendet wird.

### API

Neuer Router `backend/app/routers/settings_admin.py`:

- `GET /api/admin/settings` → Liste aller 14 Felder mit `{key, current_value, default_value, is_override}`.
- `PUT /api/admin/settings/{key}` → Body `{value}`, validiert gegen den erwarteten Typ/erlaubte Werte (z.B. `llm_provider` nur "claude"/"ollama"/"opencode"), schreibt DB + wendet sofort an.
- `DELETE /api/admin/settings/{key}` → Override entfernen, zurück zum Default.

### Frontend

Neue Seite `frontend/src/pages/SettingsAdmin.tsx`:

- Formular mit den 14 Feldern, passender Input-Typ pro Feld (Dropdown für `llm_provider`, Number-Input für Concurrency/Thresholds/`discovery_depth`, Toggle für `js_rendering_enabled`, Text für Modell-/URL-Felder).
- Pro Feld Anzeige, ob aktuell Default oder Override aktiv ist (z.B. Badge "Override" vs. "Default").
- "Zurücksetzen"-Button pro Feld → ruft `DELETE`.

## Testing

- Backend: pytest-Tests für `call_llm`-Token-Erfassung (gemockte Provider-Responses, prüft korrekte `LlmCall`-Rows inkl. `estimated`-Flag bei fehlendem Opencode-Usage), für die `llm-usage`-Endpunkte (Summary/Timeseries/Breakdown-Berechnung) und für die `settings`-Endpunkte (Override schreiben/anwenden/zurücksetzen, inkl. Validierung ungültiger Werte).
- Kein Frontend-Testaufwand über bestehende Konventionen hinaus (manuelles Durchklicken der neuen Admin-Seiten).

## Out of Scope

- Multi-Worker/Multi-Instanz-Settings-Sync (aktuell nicht relevant, da Single-Worker-Deployment).
- Verschlüsselung/Maskierung von Secrets in der UI (Secrets bleiben bewusst außerhalb der DB-Settings).
- Per-Company-Zuordnung von Token-Kosten (Tracking ist global/caller-basiert, nicht pro Company).
