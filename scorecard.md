# Fachliche Anforderung zur Umsetzung einer Competitor Scorecard im WFM Intelligence Tool

## Kontext

Wir entwickeln ein WFM Competitive Intelligence Tool für die strukturierte Beobachtung von Wettbewerbern im Workforce-Management-Softwaremarkt.

Das System erfasst bereits **Signals** aus verschiedenen Quellen und erstellt darauf basierend **Assessments** durch einen spezialisierten KI-Analysten. Diese Assessments klassifizieren Signale fachlich und strategisch, ordnen sie WFM-Capabilities zu und berechnen bereits einen deterministischen **Movement Score**.

Die neue Anforderung ist, auf Basis dieser bestehenden Logik eine **Competitor Scorecard** zu implementieren, die pro Wettbewerber einen konsistenten, nachvollziehbaren und aggregierten Überblick über dessen Stärke, Aktivität und strategische Bewegungen liefert.

Wichtig:
- Die Scorecard soll **nicht direkt auf Rohsignalen** basieren.
- Die Scorecard soll **auf Assessments** basieren.
- Assessments sind die zentrale fachliche Bewertungsinstanz.
- Die Scorecard soll so gebaut sein, dass sie sowohl für Product Strategy, Market Intelligence als auch Leadership Reporting nutzbar ist.

---

## Bestehendes fachliches Modell

### 1. Signals
Ein Signal ist eine strukturierte Beobachtung zu einem Wettbewerber, z. B.:
- Produktankündigung
- Release
- Event-Auftritt
- Whitepaper
- Hiring-Signal
- Partnerschaft
- Integration
- Markt-Expansion
- Positionierungsänderung

Jedes Signal enthält bereits u. a.:
- `signal_type`
- `title`
- `summary`
- `why_it_matters`
- `relevance_score`
- `confidence_score`

### 2. Assessments
Signals oberhalb eines konfigurierbaren Relevanz-Schwellenwerts werden an einen spezialisierten KI-Analysten übergeben.

Dieser erzeugt ein `SignalAssessment` mit aktuell folgenden Feldern:
- `capability_primary`
- `capability_secondary`
- `signal_class`
- `evidence_strength` (1–5)
- `visibility_impact` (`low | medium | high`)
- `strategic_intent_guess`
- `gameplay_tags`
- `assessment_summary`
- `implication_for_us`
- `watch_items`
- `confidence` (0–1)

### 3. Movement Score
Aus dem Assessment wird bereits deterministisch ein `movement_score` (0–100) berechnet.

Aktuelle Formel:
- `Score = (relevance × 35) + (confidence × 20) + (evidence_strength × 6) + visibility_bonus`
- `visibility_bonus`: `low=0`, `medium=8`, `high=15`
- `thought_leadership_signal`: zusätzlicher Abschlag `-10`

Movement Strength:
- `0–29 = weak`
- `30–59 = relevant`
- `60–79 = strong`
- `80–100 = market_shaping`

### 4. Capability-Modell
Es existiert ein Modell von 16 WFM-Capabilities.
Mehrere Assessments werden bereits über Zeiträume aggregiert (z. B. 30 / 90 / 180 Tage), um eine **Capability Strength Matrix** zu erzeugen.

Zusätzlich existiert ein **Wardley Evolution Band** pro Capability:
- `genesis`
- `product`
- `commodity`

---

## Zielbild der neuen Anforderung

Es soll eine **Competitor Scorecard** eingeführt werden, die aus bestehenden Assessments gespeist wird und pro Competitor ein kompaktes, aber belastbares KPI-Set bereitstellt.

Diese Scorecard soll:
1. die Stärke und Dynamik eines Wettbewerbers vergleichbar machen,
2. auf bestehenden Assessments aufbauen,
3. fachlich nachvollziehbar und auditierbar sein,
4. über definierte Zeiträume aggregierbar sein,
5. Trends und Benchmarks ermöglichen,
6. später für Dashboards, Ranking, Alerts und Reporting nutzbar sein.

---

## Fachliche Grundprinzipien

Die Lösung muss folgenden Prinzipien folgen:

1. **Assessment-first**
   - Rohsignale sind Input.
   - Assessments sind die bewertete Wahrheitsschicht.
   - Nur Assessments fließen in Scorecards ein.

2. **Deterministisch und auditierbar**
   - Aggregationen und Scores müssen nachvollziehbar berechnet werden.
   - Für jeden KPI muss zurückverfolgbar sein, welche Assessments beigetragen haben.

3. **Qualitative Information wird strukturiert quantifiziert**
   - Qualitative Analystenbewertung muss in standardisierte Scoring-Logik überführt werden.
   - Scores müssen verständlich bleiben.

4. **Zeitbezug ist Pflicht**
   - Scorecards müssen für definierte Zeitfenster berechnet werden können.
   - Ältere Assessments sollen an Gewicht verlieren oder explizit aus dem Zeitraum fallen.

5. **Mehrdimensional statt eindimensional**
   - Kein einzelner Gesamtscore ohne Zerlegung.
   - Es braucht Dimensionen mit jeweils eigenen KPIs.

6. **Geeignet für Competitive Intelligence**
   - Auch unvollständige, noisy, indirekte Marktinformationen müssen sinnvoll verarbeitet werden.
   - Confidence und Evidence Strength müssen starken Einfluss auf die Gewichtung haben.

---

## Fachliche Anforderung: Scorecard-Dimensionen

Die Scorecard soll zunächst aus folgenden Dimensionen bestehen:

### 1. Capability Strength
Frage:
- In welchen WFM-Capabilities zeigt der Wettbewerber die stärkste strategische Bewegung und Substanz?

Ziel:
- Sichtbar machen, in welchen Produkt-/Lösungsbereichen ein Competitor besonders stark ist oder gerade stark investiert.

Primäre Inputs:
- `capability_primary`
- `capability_secondary`
- `movement_score`
- `movement_strength`
- `evidence_strength`
- optional Wardley-Kontext

---

### 2. Activity
Frage:
- Wie viel relevante Wettbewerbsaktivität ist im gewählten Zeitraum sichtbar?

Ziel:
- Quantifizieren, wie aktiv ein Wettbewerber insgesamt ist.

Primäre Inputs:
- Anzahl Assessments
- Verteilung nach `signal_class`
- `movement_score`
- `evidence_strength`

---

### 3. Market Impact
Frage:
- Wie sichtbar und strategisch wirksam sind die Bewegungen des Wettbewerbers im Markt?

Ziel:
- Zwischen bloßer Aktivität und marktprägenden Moves unterscheiden.

Primäre Inputs:
- `visibility_impact`
- `movement_score`
- `movement_strength`
- `signal_class`
- optional spätere Buyer-/ICP-Relevanz

---

### 4. Customer Proof
Frage:
- Welche Signale deuten auf echte Marktvalidierung, Kundenwirkung oder umsetzungsnahe Substanz hin?

Ziel:
- Nicht nur Kommunikation, sondern belastbare Marktwirkung sichtbarer machen.

Primäre Inputs:
- bestimmte `signal_class`-Typen, z. B. Produktisierung, Implementierungsnähe, Ecosystem Moves, Referenz-/Kundensignale
- `evidence_strength`
- `confidence`

---

### 5. Momentum (optional, aber fachlich vorbereiten)
Frage:
- Beschleunigt oder verlangsamt sich der Wettbewerber im Zeitverlauf?

Ziel:
- Trend und Dynamik sichtbar machen.

Primäre Inputs:
- Veränderung gegenüber Vorperiode
- Entwicklung von Anzahl, Stärke und Verteilung der Assessments

---

## Fachliche Anforderung: Mindest-Erweiterungen am Assessment-Modell

Das bestehende Assessment-Modell ist bereits sehr gut, muss aber um wenige strukturierende Felder erweitert werden, damit eine robuste Scorecard berechnet werden kann.

Bitte ergänze das fachliche Assessment-Modell mindestens um:

- `dimension_targets`: Liste der Scorecard-Dimensionen, auf die dieses Assessment einzahlt
- `kpi_targets`: Liste konkreter KPI-IDs, auf die dieses Assessment einzahlt
- `assessment_weight`: optionaler Gewichtungsfaktor, falls ein Assessment manuell oder regelbasiert stärker/schwächer gewichtet wird
- `valid_from`
- `valid_until`
- `assessment_age_days` oder Berechnungslogik dafür
- optional vorbereitend: `buyer_relevance` (1–5), auch wenn dies initial noch nicht befüllt wird

Wichtig:
- Ein Assessment darf auf mehrere Dimensionen einzahlen.
- Beispiel: Ein Produkt-Launch in `ai_copilot` kann gleichzeitig auf `capability_strength`, `activity` und `market_impact` einzahlen.

---

## Fachliche Anforderung: KPI-Logik

Es soll **kein rein freier Gesamtscore** entstehen, sondern eine fachlich strukturierte KPI-Logik.

Bitte definiere ein erstes KPI-Set je Dimension.

### Für Capability Strength
Beispielhafte KPI-Typen:
- Stärke pro Capability
- Anzahl starker Moves pro Capability
- Anteil market-shaping Moves
- gewichteter Capability Score im Zeitraum

### Für Activity
Beispielhafte KPI-Typen:
- Anzahl relevanter Assessments
- Anzahl starker Assessments
- Diversity der Signal-Klassen
- gewichtete Aktivitätsstärke

### Für Market Impact
Beispielhafte KPI-Typen:
- Anzahl High-Visibility Assessments
- gewichteter Sichtbarkeits-Impact
- Anteil market-shaping Moves
- strategische Move-Qualität

### Für Customer Proof
Beispielhafte KPI-Typen:
- Anzahl customer-/ecosystem-naher Signale
- gewichtete Belegstärke
- Anteil hoher Evidence Strength
- Validierungsnähe

### Für Momentum
Beispielhafte KPI-Typen:
- Delta zur Vorperiode
- Beschleunigung starker Moves
- steigende/fallende Capability-Dynamik

---

## Fachliche Anforderung: Aggregationslogik

Die Scorecard soll über konfigurierbare Zeiträume berechnet werden:
- 30 Tage
- 90 Tage
- 180 Tage

Dabei sollen mindestens folgende Regeln gelten:

1. **Assessments innerhalb des Zeitraums werden aggregiert**
2. **Neue Assessments haben höheres Gewicht als alte**, entweder durch:
   - expliziten Zeitraum-Schnitt
   - oder zusätzliche Decay-Logik
3. **Hohe Evidence Strength verstärkt den Beitrag**
4. **Hohe Analysten-Confidence verstärkt den Beitrag**
5. **High Visibility erhöht Marktwirkungs-Scores**
6. **Thought Leadership Signale dürfen nicht dieselbe Wirkung haben wie echte Produktmoves**
7. **Negative oder schwache Signale dürfen Scores senken oder nur schwach beitragen**
8. **Die Aggregation muss für jedes Ergebnis die beitragenden Assessments referenzierbar machen**

---

## Fachliche Anforderung: Ergebnisobjekte

Bitte implementiere fachliche Datenmodelle für mindestens:

1. `Signal`
2. `SignalAssessment`
3. `CapabilityKPIResult`
4. `ScorecardDimensionResult`
5. `CompetitorScorecard`
6. `CompetitorBenchmarkView`

Die `CompetitorScorecard` soll mindestens enthalten:
- `competitor_id`
- `period`
- `generated_at`
- `overall_score`
- `overall_trend`
- `dimension_scores`
- `top_capabilities`
- `top_moves`
- `risk_flags`
- `watchpoints`
- `benchmark_position`
- Referenzen auf beitragende Assessments

---

## Fachliche Anforderung: Benchmarking

Zusätzlich zur Einzel-Scorecard soll eine Benchmarking-Sicht möglich sein.

Diese soll mindestens beantworten:
- Wer ist im gewählten Zeitraum insgesamt am stärksten?
- Wer dominiert welche Capability?
- Wer hat das höchste Momentum?
- Wo sind wir besonders bedroht?
- Welche Wettbewerber bewegen eine Capability aktiv Richtung nächste Wardley-Stufe?

---

## Fachliche Anforderung: Explainability / Auditierbarkeit

Ein zentrales Ziel ist fachliche Nachvollziehbarkeit.

Daher muss die Lösung:
- für jeden Score offenlegen, welche Assessments beigetragen haben,
- die Berechnungslogik dokumentieren,
- Scorebestandteile je Dimension ausweisen,
- Trends zur Vorperiode berechnen können,
- und für einzelne Competitoren ein „Why this score?“ liefern.


---

## Zusätzliche fachliche Leitlinien

Bitte beachte bei der Konzeption besonders:

- Das System ist ein Competitive-Intelligence-System, kein klassisches BI-System.
- Unvollständige Informationen sind normal.
- Deshalb müssen Confidence, Evidence Strength und Recency explizit berücksichtigt werden.
- Die Scorecard soll eher **strategische Richtung und Bewegungsstärke** zeigen als absolute Marktanteile behaupten.
- Das Modell soll für Leadership verständlich, für Analysten nachvollziehbar und für Produktteams handlungsleitend sein.
- Die Lösung soll später UI-seitig in Cards, Matrix Views, Capability Heatmaps und Competitor Profile eingebettet werden können.