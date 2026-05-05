Erweitere mein bestehendes Produkt „WFM Market Intelligence Hub“ um einen relativen Capability-Strength-Layer für Wettbewerber.

Kontext:
Im bestehenden System gibt es bereits:
- Company
- Source
- Document
- Signal
- SignalAssessment
- CompetitorSummary
- Executive Overview
- Competitor Workspace
- Signals Feed

In der Competitor-Ansicht existiert bereits eine „Capability Activity“-Übersicht auf Basis der letzten Assessments und Moves.

Ziel dieser Erweiterung:
Wir wollen zusätzlich modellieren und sichtbar machen, welcher Wettbewerber in welcher Capability im Vergleich zu den anderen aktuell am stärksten ist.

Wichtig:
- Es geht um eine modellierte relative Einschätzung auf Basis verfügbarer Evidenz.
- Es ist KEIN objektiver Marktanteils- oder Wahrheitsscore.
- Score, Rank und Confidence müssen immer gemeinsam dargestellt werden.
- Activity / Momentum und Strength müssen getrennt modelliert werden.

## Produktziele

Die Erweiterung soll diese Fragen beantworten:
- Welcher Wettbewerber ist in welcher Capability aktuell am stärksten?
- Wer ist Leader, wer Strong, wer Emerging, wer Weakly evidenced?
- Wie unterscheidet sich aktuelle Stärke von aktuellem Momentum?
- In welchen Bereichen ist ein Wettbewerber führend, obwohl er gerade wenig Activity zeigt?
- In welchen Bereichen zeigt ein Wettbewerber starkes Momentum, ist aber noch nicht führend?
- Welche Capability-Zonen sind insgesamt stark umkämpft?

## Neue Kernidee

Wir führen einen neuen Aggregations-Layer ein:
`CompetitorCapabilityBenchmark`

Dieser Layer bewertet pro Competitor und Capability die relative Stärke auf Basis von Signals, Assessments und Marktevidenz.

## Neues Datenmodell

Bitte ergänze das bestehende Modell um eine neue Entität:

### CompetitorCapabilityBenchmark
Felder:
- id
- company_id
- capability_key
- period_type (30d | 90d | 180d)
- period_start
- period_end
- capability_depth_score (0-5)
- execution_momentum_score (0-5)
- market_proof_score (0-5)
- strategic_focus_score (0-5)
- evidence_coverage_score (0-5)
- relative_strength_score (0-100)
- peer_rank
- peer_percentile
- tier (leader | strong | emerging | weakly_evidenced)
- confidence (0-1)
- summary_reason
- source_signal_count
- created_at
- updated_at

Falls du eine zusätzliche Snapshot- oder History-Tabelle brauchst, kannst du das ergänzen.

## Capability-Modell

Verwende weiterhin die bestehende WFM Capability-Taxonomie, z. B.:
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

## Bewertungsdimensionen

Bitte implementiere pro Competitor und Capability diese fünf Dimensionen:

1. Capability Depth
Wie stark ist die Capability funktional und produktseitig belegt?
Beispiele:
- reale Produktfeatures
- dokumentierte Workflows
- wiederholte Produktverbesserungen
- sichtbare Capability-Tiefe

2. Execution Momentum
Wie stark bewegt sich der Wettbewerber in letzter Zeit in dieser Capability?
Beispiele:
- neue Releases
- wiederholte Assessments
- starke oder market_shaping moves

3. Market Proof
Wie stark ist die Capability extern belegt?
Beispiele:
- Kundenfälle
- Referenzen
- Analystenerwähnungen
- Partner-/Ökosystemsignale
- sichtbare Marktadoption

4. Strategic Focus
Wie sehr wirkt diese Capability wie ein echter Schwerpunkt des Wettbewerbers?
Beispiele:
- wiederholte Messaging-Signale
- konsistente Positionierung
- Häufung in Produktkommunikation
- Priorisierung auf Produktseiten, Events oder Kampagnen

5. Evidence Coverage
Wie belastbar ist die Gesamteinschätzung?
Beispiele:
- Anzahl hochwertiger Signale
- Konsistenz der Evidenz
- Frische der Daten
- Breite der Quellenbasis

## Wichtige Modell-Regeln

- Strength und Momentum sind getrennt.
- Ein Competitor kann hohe Strength, aber niedriges Momentum haben.
- Ein Competitor kann hohes Momentum, aber geringe Strength haben.
- Wenig Daten dürfen nicht automatisch als Schwäche interpretiert werden; stattdessen muss Evidence Coverage bzw. Confidence sinken.
- Reines Messaging ohne Produkt- oder Marktbelege darf Strategic Focus erhöhen, aber Capability Depth nicht künstlich aufblasen.
- Confidence und relative_strength_score dürfen nicht verwechselt werden.
- Falls Datenlage zu dünn ist, soll eher „weakly_evidenced“ statt „weak competitor“ angezeigt werden.

## Scoring-Vorschlag

Bitte entwickle eine robuste, nachvollziehbare Formel.

Empfohlene Gewichte:
- capability_depth_score: 35%
- execution_momentum_score: 25%
- market_proof_score: 20%
- strategic_focus_score: 10%
- evidence_coverage_score: 10%

Leite daraus einen `relative_strength_score` von 0 bis 100 ab.

Danach berechne pro Capability:
- peer_rank
- peer_percentile

Dann leite einen Tier-Wert ab:
- leader
- strong
- emerging
- weakly_evidenced

Bitte begründe die Schwellenwerte.

## LLM + Regeln

Nutze einen hybriden Ansatz:
- deterministische Voraggregation aus bestehenden Signals und SignalAssessments
- optional LLM für qualitative Summary / summary_reason
- optional LLM für Konfliktfälle oder dünne Evidenz

Das LLM soll NICHT den kompletten numerischen Score frei erfinden.
Der Score soll primär aus Regeln und Aggregationen entstehen.

Das LLM darf unterstützen bei:
- summary_reason
- qualitative capability interpretation
- tie-breaker reasoning
- competitor comparison phrasing

## Benötigte Services

Bitte implementiere oder skizziere:

1. BenchmarkAggregationService
- aggregiert Signals + Assessments pro Competitor/Capability/Zeitraum
- berechnet Teil-Scores
- berechnet finalen Strength Score
- berechnet Peer Rank und Peer Percentile
- speichert Benchmarks

2. BenchmarkQueryService
- liefert Overview-Matrix
- liefert Competitor Detail Strengths
- liefert Capability-specific leaderboard
- liefert stärkste Wettbewerber pro Capability

3. Optional BenchmarkSummaryLLMService
- erzeugt `summary_reason`
- gibt kurze qualitative Begründung zurück

## API-Endpunkte

Bitte ergänze sinnvolle Endpunkte wie:

- GET /benchmark/overview
  Antwort:
  - capabilities[]
  - competitors[]
  - matrix[] mit score, rank, confidence, tier

- GET /benchmark/competitors/:slug
  Antwort:
  - competitor
  - capability_benchmarks[]
  - strongest_capabilities[]
  - weakest_evidenced_capabilities[]
  - trend_vs_previous_period[]

- GET /benchmark/capabilities/:key
  Antwort:
  - leaderboard[]
  - benchmark_distribution
  - strongest_competitor
  - fastest_riser

- POST /benchmark/recompute
  - recompute all benchmarks

- POST /benchmark/recompute/:companyId
  - recompute one competitor

## Frontend-Ziel

Erweitere die Competitor-Übersichtsseite um eine klare Vergleichsansicht.

### Neue UI-Module auf der Competitor Overview Page

1. Capability Strength Matrix
- Spalten = Capabilities
- Zeilen = Competitors
- Zellen zeigen:
  - relative_strength_score
  - color intensity
  - tier badge
  - tooltip mit confidence und reason
- Klick auf Zelle => Drilldown zur Capability oder Competitor-Detailseite

2. Top-in-Category Panel
- pro Capability anzeigen:
  - strongest competitor
  - score
  - confidence
  - optional trend arrow

3. Overall Peer Snapshot
- kleine Gesamtrangliste über alle Capabilities
- aber weniger prominent als die capability-spezifische Matrix

4. Capability Leaderboard Drawer
- zeigt bei Klick die sortierte Liste aller Wettbewerber innerhalb einer Capability
- inklusive score, rank, confidence, momentum, summary_reason

## Erweiterung der Competitor Detail Page

Ergänze zusätzlich zur bestehenden Capability Activity View ein neues Panel:
`Relative Capability Strength`

Dieses Panel soll pro Capability zeigen:
- score
- rank among peers
- tier
- confidence
- delta vs previous period
- short reason

Bitte trenne visuell:
- Activity / recent moves
- Relative strength
- Momentum trend

## UX-Anforderungen

- Die Matrix muss auch mit 5-8 Wettbewerbern gut lesbar bleiben.
- Hover / click muss Explainability zeigen.
- Schwache Evidenz darf nicht wie schwache Marktposition aussehen.
- Nutze klare Farbskalen und Badges.
- Clarity over decoration.
- Overview -> Drilldown -> Evidence muss erhalten bleiben.

