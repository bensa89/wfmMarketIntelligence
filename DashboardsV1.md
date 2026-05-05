Baue die V1-Frontend- und Backend-Erweiterung für mein bestehendes Produkt „WFM Market Intelligence Hub“.

Ziel:
Wir konzentrieren uns in V1 auf genau drei User-Ebenen:
1. Executive Overview
2. Competitor Workspace
3. Signals Feed

Es geht NICHT um eine vollständige Wardley-Map-Visualisierung in V1.
Stattdessen soll eine klare Intelligence-Schicht entstehen, die aus bestehenden Signals strukturierte Bewertungen und Aggregationen ableitet, damit diese drei Ansichten sauber funktionieren.

## Bestehendes Datenmodell

Aktuell existieren folgende Kern-Entitäten:

Company
- id, name, slug (unique)
- type: competitor | market_source
- description, website, created_at

Source
- id, url (unique), label
- source_type: news | blog | product | press | jobs
- is_active, crawl_status: new | known | changed
- content_hash, last_crawled_at, last_changed_at
- company_id

Document
- id, url (unique), title
- content_markdown, content_raw_html
- published_at, crawled_at
- content_hash, is_analysed, from_search
- source_id

Signal
- id, title
- signal_type: product_update | ai_announcement | partnership | positioning_change | target_market_change | event_or_thought_leadership | hiring_signal | other
- topic, summary, why_it_matters
- relevance_score, confidence_score
- published_at, created_at
- search_vector
- document_id
- company_id

Weitere Entitäten für Crawling existieren ebenfalls:
- CrawlRun
- CrawlRunSource
- DiscoveredPage
- CrawlBriefing
- WeeklyDigest
- InternalCompanyContext

Wichtig:
Signal referenziert sowohl Company als auch Document.
Dadurch ist schnelle Filterung und gleichzeitig Traceability zur Quelle möglich.

## Aufgabe

Erweitere dieses bestehende Modell so, dass daraus die drei V1-Ansichten gebaut werden können:
1. Executive Overview
2. Competitor Workspace
3. Signals Feed

Die neue Lösung soll:
- das bestehende Modell respektieren,
- nur gezielt ergänzen,
- sauber in Backend und Frontend integrierbar sein,
- LLM-basierte Bewertung für Signals ermöglichen,
- aber mit validierten, strukturierten Ergebnissen arbeiten.

## Produktlogik

Wir brauchen in V1 eine zusätzliche Intelligence-Schicht auf dem Signal.

Ein Signal ist das Rohereignis.
Ein Assessment ist die interpretierte Sicht auf das Signal.

Das System soll aus jedem Signal eine strukturierte Bewertung erzeugen, damit wir:
- Signals im Feed sauber filtern,
- Competitor-Muster erkennen,
- im Executive Overview Top Movers, Trends, Risiken und Chancen darstellen können.

## V1-Datenmodell: bitte ergänzen

Führe folgende zusätzliche Entitäten oder Modelle ein:

### 1) SignalAssessment
Ein strukturierter, durch Regeln + LLM erzeugter Analyse-Layer pro Signal.

Felder:
- id
- signal_id
- company_id
- capability_primary
- capability_secondary (JSON array)
- signal_class
- evidence_strength (1-5)
- visibility_impact (low|medium|high)
- strategic_weight (integer)
- movement_score (integer)
- movement_strength (weak|relevant|strong|market_shaping)
- confidence (float 0-1)
- strategic_intent_guess
- gameplay_tags (JSON array)
- assessment_summary
- implication_for_us
- watch_items (JSON array)
- created_at
- updated_at

### 2) CompetitorSummary
Eine aggregierte Sicht pro Wettbewerber und Zeitraum.

Felder:
- id
- company_id
- period_type (7d|30d|90d|quarter)
- period_start
- period_end
- strategic_posture
- positioning_summary
- top_capabilities (JSON array)
- capability_assessment (JSON array)
- top_risks (JSON array)
- top_opportunities (JSON array)
- watchpoints (JSON array)
- avg_movement_score
- signal_count
- created_at
- updated_at

### 3) CapabilityDefinition
Kann zunächst auch als statische TypeScript-Konstante implementiert werden.
Wenn du es als DB-Modell brauchst, ist das okay, aber in V1 reicht auch Code-first.

Capabilities für V1:
- demand_forecasting
- shift_scheduling
- intraday_management
- time_attendance
- compliance_rules
- employee_self_service
- manager_experience
- mobile_experience
- analytics_insights
- ai_copilot
- workflow_automation
- integration_hub
- platform_ecosystem
- vertical_solutions
- data_foundation
- optimization_engine

Jede Capability soll Metadaten haben:
- key
- label
- visibility_to_user
- strategic_weight
- default_evolution_band
- description

## Was die drei Views brauchen

### 1) Executive Overview
Soll in weniger als 60 Sekunden beantworten:
- Wer bewegt sich aktuell?
- In welchen Capabilities?
- Welche Risiken und Chancen sind neu?
- Welche Competitors sind Top Movers?

Benötigte Backend-Outputs:
- top_movers_last_7d
- top_movers_last_30d
- capability_heatmap
- recent_market_shaping_signals
- emerging_risks
- emerging_opportunities

### 2) Competitor Workspace
Soll pro Wettbewerber zeigen:
- strategische Haltung
- wichtigste Capability-Zonen
- letzte relevante Moves
- Chancen/Risiken
- beobachtenswerte Themen

Benötigte Backend-Outputs:
- competitor_profile
- competitor_summary_30d
- competitor_summary_90d
- recent_assessments
- capability_distribution
- timeline_of_moves

### 3) Signals Feed
Soll eine operative Arbeitsoberfläche sein.

Benötigte Funktionen:
- Filter nach competitor, capability, signal_type, movement_strength, confidence range, Zeitraum
- Sortierung nach published_at, movement_score, confidence
- Explainability pro Signal
- Link zurück zu Document / Source / Company
- Badge für weak / relevant / strong / market_shaping

Benötigte Backend-Outputs:
- paginated signal list
- joins zu assessment, company, source, document
- filter metadata
- explainability payload

## Bewertungslogik

Implementiere eine V1-Regel- und LLM-Kombination.

### Regelbasierte Vorbewertung
Nutze das vorhandene `signal_type`, `topic`, `summary`, `why_it_matters` und optional Document-Inhalte.

Regeln:
- product_update => eher product_capability_move
- ai_announcement => Produktmove oder positioning_move, je nach Evidenz
- partnership => ecosystem_move
- positioning_change => positioning_move
- target_market_change => positioning_move oder market_expansion_move
- event_or_thought_leadership => thought_leadership_signal
- hiring_signal => hiring_signal, geringe Evidenz
- other => weak_signal oder manuell klassifizieren

### Scoring
Leite movement_score aus mehreren Faktoren ab:
- relevance_score
- confidence_score
- evidence_strength
- visibility_impact
- strategic_weight
- marketing penalty

Definiere eine robuste, einfache Formel für V1.
Leite daraus movement_strength ab:
- weak
- relevant
- strong
- market_shaping

## LLM-Integration

Das LLM soll pro Signal ein strukturiertes Assessment erzeugen.
Wichtig:
- JSON-only response
- schema validation
- retry on invalid JSON
- niedrige Temperatur
- keine freien Essays

Erstelle dafür:
1. System Prompt für Signal Assessment
2. User Prompt Template für Signal Assessment
3. Aggregationsprompt für Competitor Summary

Das LLM soll bewerten:
- capability_primary
- capability_secondary
- signal_class
- evidence_strength
- visibility_impact
- strategic_intent_guess
- gameplay_tags
- assessment_summary
- implication_for_us
- watch_items
- confidence

## Erwartete technische Umsetzung

Baue oder skizziere konkret:

### Backend
- Datenmodelle / ORM-Modelle / SQL-Vorschläge
- Service für SignalAssessment
- Service für CompetitorSummary
- LLM Service Interface
- Prompt Builder
- Aggregation Service
- Query Layer für Dashboard-Views
- API Endpoints für:
  - GET /overview
  - GET /competitors/:slug
  - GET /signals
  - POST /signals/:id/assess
  - POST /competitors/:id/summarize

### Frontend
Bitte schlage eine klare React-Komponentenstruktur vor für:
- OverviewPage
- CompetitorPage
- SignalsPage

Bitte die UI so strukturieren:
- Overview → Context → Detail
- hohe Informationsdichte, aber klar priorisiert
- Drilldown-fähig
- Quellenbezug immer sichtbar
- Confidence und Explainability immer sichtbar

## Wichtig
- Nutze mein bestehendes Modell als Ausgangspunkt.
- Erfinde keine komplett neue Plattformarchitektur.
- Ergänze nur die V1-relevanten Modelle und Flows.
- Schreibe konkret, pragmatisch und umsetzungsnah.
- Wenn du Annahmen triffst, schreibe sie kurz dazu.
- Bevorzuge inkrementelles Refactoring gegenüber Full Rewrite.

