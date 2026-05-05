# Competitor Capability Benchmark — Design Spec

## Überblick

Erweiterung des WFM Market Intelligence Hub um einen relativen Capability-Strength-Layer für Wettbewerber. Das System bewertet pro Competitor und Capability die relative Stärke auf Basis von Signals, Assessments und Marktevidenz.

### Kernprinzipien

- **Strength und Momentum sind getrennt.** Ein Competitor kann hohe Strength, aber niedriges Momentum haben und umgekehrt.
- **Wenig Daten ≠ Schwäche.** Stattdessen sinkt Evidence Coverage bzw. Confidence. Das Tier "weakly_evidenced" bedeutet "kaum Belege", nicht "schwach im Markt".
- **Score, Rank und Confidence werden immer gemeinsam dargestellt.**
- **Deterministisch First, LLM Second.** Scores entstehen primär aus Regeln und Aggregationen. Das LLM darf nur bei summary_reason, qualitativer Interpretation und Tie-Breakern helfen.

### Produktfragen

- Welcher Wettbewerber ist in welcher Capability aktuell am stärksten?
- Wer ist Leader, Strong, Emerging, Weakly evidenced?
- Wie unterscheidet sich aktuelle Stärke von aktuellem Momentum?
- In welchen Bereichen ist ein Wettbewerber führend, obwohl er gerade wenig Activity zeigt?
- In welchen Bereichen zeigt ein Wettbewerber starkes Momentum, ist aber noch nicht führend?
- Welche Capability-Zonen sind insgesamt stark umkämpft?

---

## Architektur

**Ansatz: On-demand Aggregation mit persistiertem Cache und Delta-Feldern**

- `BenchmarkAggregationService` aggregiert live aus `SignalAssessment`-Daten
- Ergebnisse werden in `CompetitorCapabilityBenchmark` persistiert (als Cache/Snapshot)
- Bei recompute wird `prev_period_strength_score` aus dem alten Record gesichert, bevor überschrieben wird
- Nach jedem erfolgreichen Crawl+Assessment wird automatisch `recompute_company` für die betroffene Company getriggert
- Manueller recompute über API möglich
- History kann als separate Tabelle später ergänzt werden (Out of Scope für MVP)

### Peer Group

Alle Unternehmen vom Typ `competitor` bilden automatisch die Peer Group. Keine konfigurierbaren Peer Groups.

---

## Datenmodell

### CompetitorCapabilityBenchmark

Neue Tabelle, Upsert auf `(company_id, capability_key, period_type)`.

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | UUID PK | Primärschlüssel |
| `company_id` | UUID FK → companies.id | Verweis auf das Unternehmen |
| `capability_key` | String(100) | Ein Wert aus der WFM Capability-Taxonomie |
| `period_type` | Enum: `30d`, `90d`, `180d` | Zeitraumtyp |
| `period_start` | Date | Beginn des Auswertezeitraums |
| `period_end` | Date | Ende des Auswertezeitraums |
| `capability_depth_score` | SmallInteger 0-5 | Funktionale Tiefe der Capability |
| `execution_momentum_score` | SmallInteger 0-5 | Aktuelle Bewegung in der Capability |
| `market_proof_score` | SmallInteger 0-5 | Externe Belege für die Capability |
| `strategic_focus_score` | SmallInteger 0-5 | Schwerpunkt-Charakter der Capability |
| `evidence_coverage_score` | SmallInteger 0-5 | Belastbarkeit der Gesamteinschätzung |
| `relative_strength_score` | Integer 0-100 | Gewichtet aggregierter Stärke-Score |
| `prev_period_strength_score` | Integer 0-100, nullable | Score des vorherigen Compute-Laufs |
| `strength_delta` | Integer, nullable | Aktual - Vorperiode |
| `peer_rank` | Integer, nullable | Rang unter allen Competitors (1 = höchster) |
| `peer_percentile` | Float, nullable | Perzentil unter allen Competitors |
| `tier` | Enum: `leader`, `strong`, `emerging`, `weakly_evidenced` | Kategorisierung |
| `confidence` | Float 0-1 | Vertrauenswürdigkeit der Einschätzung |
| `source_signal_count` | Integer | Anzahl der Signale, die in die Berechnung eingeflossen sind |
| `summary_reason` | Text, nullable | Kurze Begründung (LLM-generiert) |
| `created_at` | DateTime | Erstellungszeitpunkt |
| `updated_at` | DateTime | Letzte Aktualisierung |

**Unique Constraint:** `(company_id, capability_key, period_type)`

**Indizes:** `(company_id)`, `(capability_key, period_type)`, `(period_type, tier)`

---

## Scoring-Formel

### Gewichtung

| Dimension | Gewicht | Score-Bereich |
|-----------|---------|---------------|
| Capability Depth | 35% | 0-5 |
| Execution Momentum | 25% | 0-5 |
| Market Proof | 20% | 0-5 |
| Strategic Focus | 10% | 0-5 |
| Evidence Coverage | 10% | 0-5 |

### Formel

```
relative_strength_score = 
  (capability_depth_score × 0.35 +
   execution_momentum_score × 0.25 +
   market_proof_score × 0.20 +
   strategic_focus_score × 0.10 +
   evidence_coverage_score × 0.10) × (100 / 5)
```

Maximalscore: 100 (wenn alle Sub-Scores = 5).

### Sub-Score Herleitung (deterministisch)

Alle Sub-Scores basieren auf `SignalAssessment`-Daten des jeweiligen Zeitraums, gefiltert auf `capability_primary = <key>` und `company_id = <company_id>`.

#### 1. Capability Depth (0-5)

Wie stark ist die Capability funktional und produktseitig belegt?

Basis: Alle Assessments mit `capability_primary = <key>` im Zeitraum.

```
raw = 0
for each assessment:
  if signal_class == "product_capability_move": add 2.0
  elif signal_class in ("positioning_move", "ecosystem_move"): add 1.0
  elif signal_class in ("thought_leadership_signal", "hiring_signal", "weak_signal", "market_expansion_move"): add 0.5
  
  add (evidence_strength / 5) × 0.5  # normalisiert 0-0.5
  
  if movement_strength in ("market_shaping", "strong"): add 0.5

capability_depth_score = bin(raw / count, bins=[0,1,2,3,4,5])
```

- Reines Messaging (`positioning_move`) erhöht Capability Depth nur leicht (+1.0)
- Produkt-Belege (`product_capability_move`) erhöhen deutlich (+2.0)
- Normalisierung: wenn keine Assessments vorhanden → Score = 0

#### 2. Execution Momentum (0-5)

Wie stark bewegt sich der Wettbewerber aktuell in dieser Capability?

Drei Faktoren, gemittelt:

```
signal_density = bin(count, [(0,0), (1,1), (2-3,2), (4-6,3), (7-10,4), (11+,5)])
avg_momentum = mean(movement_score for assessments) / 20  # 0-100 → 0-5
strong_ratio = count(movement_strength in ("strong","market_shaping")) / total → × 5

execution_momentum_score = round(mean(signal_density, avg_momentum, strong_ratio))
```

#### 3. Market Proof (0-5)

Wie stark ist die Capability extern belegt?

Basis: Alle Assessments mit `capability_primary = <key>`.

```
raw = 0
for each assessment:
  if signal_class == "ecosystem_move": add 1.5  # Partnerschaften, Integrations-Signale
  elif signal_class == "product_capability_move" and has_external_evidence: add 1.0
  else: add 0.5  # Nur Produkt-Claim ohne externen Beleg
  
  if visibility_impact == "high": add 1.0
  elif visibility_impact == "medium": add 0.5
  
  if any gameplay_tag suggests customers/references/analyst: add 0.5

market_proof_score = bin(mean raw per assessment, bins=[0,1,2,3,4,5])
```

`has_external_evidence`: Heuristik auf Basis von `visibility_impact` und `gameplay_tags` (Keywords: customer, reference, analyst, partner, ecosystem, integration).

#### 4. Strategic Focus (0-5)

Wie sehr wirkt diese Capability wie ein echter Schwerpunkt?

Basis: Anteil der Assessments dieser Capability an Gesamt-Assessments der Company im Zeitraum.

```
share = count(assessments with capability_primary = <key>) / count(all assessments for company in period)
base_score = bin(share, [(<5%,0), (5-10%,1), (10-15%,2), (15-20%,3), (20-30%,4), (>30%,5)])
messaging_bonus = min(1, count(positioning_move in capability) / 3)  # +1 wenn ≥3 Positionierungs-Signale
strategic_focus_score = min(5, base_score + messaging_bonus)
```

#### 5. Evidence Coverage (0-5)

Wie belastbar ist die Gesamteinschätzung?

Drei Faktoren, **Minimum** (konservativ: der schwächste Faktor dominiert):

```
source_diversity = bin(distinct_document_count, [(0,0), (1,1), (2,2), (3,3), (4,4), (5+,5)])
avg_confidence_score = round(mean(confidence) × 5)  # 0-1 → 0-5
freshness = bin(ratio of assessments from last 30 days in period, [(0%,0), (1-25%,1), (25-50%,2), (50-75%,3), (75-90%,4), (>90%,5)])
evidence_coverage_score = min(source_diversity, avg_confidence_score, freshness)
```

### Tier-Zuordnung

| relative_strength_score | Tier | Farbe | Beschreibung |
|------------------------|------|------|-------------|
| ≥ 75 | `leader` | emerald-600 (#059669) | Deutlich führend |
| ≥ 55 | `strong` | blue-600 (#2563eb) | Stark positioniert |
| ≥ 30 | `emerging` | amber-500 (#f59e0b) | Aufstrebend |
| < 30 | `weakly_evidenced` | slate-200 (#e2e8f0) | Kaum Belege |

**Confidence-Korrektur:** Wenn `confidence < 0.4`, wird das Tier um eine Stufe heruntergestuft (leader→strong, strong→emerging, emerging→weakly_evidenced). Dies verhindert, dass dünne Datenlage als starke Position interpretiert wird. Die Korrektur greift auch bei hohen Scores: Ein Score von 80 mit confidence=0.3 wird zu "strong" statt "leader".

Ausnahme: Wenn `evidence_coverage_score < 2`, wird das Tier mindestens auf `weakly_evidenced` gesetzt, unabhängig vom berechneten Score. Dies stellt sicher, dass bei sehr dünnen Daten die Aussagekraft klar eingeschränkt wird.

### Confidence-Formel

```
confidence = min(1.0, 
  (source_signal_count / 8) × 0.5 + 
  (evidence_coverage_score / 5) × 0.3 + 
  avg_assessment_confidence × 0.2
)
```

- Mindestens 3 Signale erforderlich für `confidence > 0.4`
- `source_signal_count < 3` → Confidence auf 0.3 gedeckelt

### Peer Rank & Percentile

Nach Aggregation aller Companies des Typs `competitor`:
- `peer_rank`: Ranking nach `relative_strength_score` (1 = höchster Score)
- `peer_percentile`: `(1 - (rank - 1) / total_peers) × 100`
- Bei Gleichstand (tie): gleicher Rank, nächster Rank überspringt

---

## Backend

### Neue Dateien

```
backend/app/
├── models/
│   └── capability_benchmark.py    # CompetitorCapabilityBenchmark Modell
├── schemas/
│   └── benchmark.py              # Pydantic v2 Schemas
├── benchmark/
│   ├── __init__.py
│   ├── aggregation.py             # BenchmarkAggregationService
│   ├── queries.py                 # BenchmarkQueryService
│   ├── scoring.py                 # Sub-Score-Berechnungen (reine Funktionen)
│   ├── llm_summary.py             # BenchmarkSummaryLLMService (optional)
│   └── period.py                  # Zeitraum-Berechnung (period_type → dates)
├── routers/
│   └── benchmark.py              # API-Router /api/benchmark/
```

### Model: CompetitorCapabilityBenchmark

```python
class PeriodTypeEnum(str, Enum):
    d30 = "30d"
    d90 = "90d"
    d180 = "180d"

class BenchmarkTierEnum(str, Enum):
    leader = "leader"
    strong = "strong"
    emerging = "emerging"
    weakly_evidenced = "weakly_evidenced"

class CompetitorCapabilityBenchmark(Base):
    __tablename__ = "competitor_capability_benchmarks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    capability_key = Column(String(100), nullable=False)
    period_type = Column(String(10), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    capability_depth_score = Column(SmallInteger, nullable=False, default=0)
    execution_momentum_score = Column(SmallInteger, nullable=False, default=0)
    market_proof_score = Column(SmallInteger, nullable=False, default=0)
    strategic_focus_score = Column(SmallInteger, nullable=False, default=0)
    evidence_coverage_score = Column(SmallInteger, nullable=False, default=0)
    
    relative_strength_score = Column(Integer, nullable=False, default=0)
    prev_period_strength_score = Column(Integer, nullable=True)
    strength_delta = Column(Integer, nullable=True)
    peer_rank = Column(Integer, nullable=True)
    peer_percentile = Column(Float, nullable=True)
    tier = Column(String(20), nullable=False, default="weakly_evidenced")
    confidence = Column(Float, nullable=False, default=0.0)
    
    source_signal_count = Column(Integer, nullable=False, default=0)
    summary_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    company = relationship("Company", backref="capability_benchmarks")
    
    __table_args__ = (
        UniqueConstraint("company_id", "capability_key", "period_type", name="uq_benchmark_company_cap_period"),
        Index("ix_benchmark_company", "company_id"),
        Index("ix_benchmark_cap_period", "capability_key", "period_type"),
        Index("ix_benchmark_period_tier", "period_type", "tier"),
    )
```

### Schemas (Pydantic v2)

```python
class BenchmarkSubScores(BaseModel):
    capability_depth: int = Field(0, ge=0, le=5)
    execution_momentum: int = Field(0, ge=0, le=5)
    market_proof: int = Field(0, ge=0, le=5)
    strategic_focus: int = Field(0, ge=0, le=5)
    evidence_coverage: int = Field(0, ge=0, le=5)

class BenchmarkRead(BaseModel):
    id: str
    company_id: str
    capability_key: str
    period_type: str
    capability_depth_score: int
    execution_momentum_score: int
    market_proof_score: int
    strategic_focus_score: int
    evidence_coverage_score: int
    relative_strength_score: int
    prev_period_strength_score: int | None
    strength_delta: int | None
    peer_rank: int | None
    peer_percentile: float | None
    tier: str
    confidence: float
    source_signal_count: int
    summary_reason: str | None

class BenchmarkMatrixCell(BaseModel):
    score: int
    tier: str
    confidence: float
    rank: int | None
    momentum_score: int  # execution_momentum_score for quick overview

class BenchmarkOverviewResponse(BaseModel):
    period_type: str
    period_start: date
    period_end: date
    capabilities: list[str]
    competitors: list[CompetitorBrief]
    matrix: dict[str, dict[str, BenchmarkMatrixCell]]  # capability_key → company_id → cell

class CompetitorBenchmarkDetail(BaseModel):
    capability_key: str
    label: str
    relative_strength_score: int
    prev_period_strength_score: int | None
    strength_delta: int | None
    tier: str
    peer_rank: int | None
    peer_percentile: float | None
    confidence: float
    sub_scores: BenchmarkSubScores
    source_signal_count: int
    summary_reason: str | None

class CompetitorBenchmarkResponse(BaseModel):
    competitor: CompetitorBrief
    period_type: str
    capabilities: list[CompetitorBenchmarkDetail]
    strongest_capabilities: list[str]
    weakest_evidenced_capabilities: list[str]

class LeaderboardEntry(BaseModel):
    company_id: str
    company_name: str
    slug: str
    score: int
    tier: str
    confidence: float
    rank: int
    momentum_score: int
    strength_delta: int | None
    summary_reason: str | None

class CapabilityLeaderboardResponse(BaseModel):
    capability_key: str
    label: str
    period_type: str
    leaderboard: list[LeaderboardEntry]
    strongest_competitor: LeaderboardEntry | None
    fastest_riser: LeaderboardEntry | None
```

### Service: BenchmarkAggregationService

```python
class BenchmarkAggregationService:
    def __init__(self, db: Session):
        self.db = db
    
    def recompute_all(self, period_type: str = "30d") -> list[CompetitorCapabilityBenchmark]:
        """Recompute benchmarks for all competitors."""
        competitors = self.db.query(Company).filter(Company.type == "competitor").all()
        results = []
        for c in competitors:
            results.extend(self.recompute_company(c.id, period_type))
        # After all individual scores computed, compute peer rankings
        self._compute_peer_rankings(period_type)
        return results
    
    def recompute_company(self, company_id: str, period_type: str = "30d") -> list[CompetitorCapabilityBenchmark]:
        """Recompute benchmarks for a single company across all capabilities."""
        period_start, period_end = self._get_period_bounds(period_type)
        assessments = self._get_assessments(company_id, period_start, period_end)
        
        benchmarks = []
        for cap_key in CAPABILITY_KEYS:
            cap_assessments = [a for a in assessments if a.capability_primary == cap_key]
            scores = compute_sub_scores(cap_assessments, assessments, period_start, period_end, cap_key)
            confidence = compute_confidence(cap_assessments, scores.evidence_coverage)
            
            # Preserve previous score before overwriting
            prev_score = self._get_previous_score(company_id, cap_key, period_type)
            
            # Lookup strategic_weight from CAPABILITIES
            strategic_weight = CAPABILITIES.get(cap_key, {}).get("strategic_weight", 5)
            
            strength_score = compute_relative_strength(scores)
            tier = determine_tier(strength_score, confidence, scores.evidence_coverage)
            
            benchmark = upsert_benchmark(
                db=self.db,
                company_id=company_id,
                capability_key=cap_key,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                sub_scores=scores,
                relative_strength_score=strength_score,
                prev_period_strength_score=prev_score,
                strength_delta=(strength_score - prev_score) if prev_score is not None else None,
                tier=tier,
                confidence=confidence,
                source_signal_count=len(cap_assessments),
            )
            benchmarks.append(benchmark)
        
        self.db.commit()
        return benchmarks
    
    def _compute_peer_rankings(self, period_type: str):
        """Compute peer_rank and peer_percentile for all benchmarks of a period_type."""
        for cap_key in CAPABILITY_KEYS:
            benchmarks = self.db.query(CompetitorCapabilityBenchmark).filter(
                CompetitorCapabilityBenchmark.capability_key == cap_key,
                CompetitorCapabilityBenchmark.period_type == period_type,
            ).order_by(CompetitorCapabilityBenchmark.relative_strength_score.desc()).all()
            
            total = len(benchmarks)
            for i, b in enumerate(benchmarks):
                b.peer_rank = i + 1
                b.peer_percentile = round((1 - i / total) * 100, 1) if total > 0 else 0
            self.db.commit()
```

### Service: Scoring Functions (`benchmark/scoring.py`)

Reine Funktionen, die aus einer Liste von `SignalAssessment`-Objekten die Sub-Scores berechnen. Keine DB-Abhängigkeiten, testbar in Isolation.

```python
class SubScores:
    capability_depth: int      # 0-5
    execution_momentum: int     # 0-5
    market_proof: int           # 0-5
    strategic_focus: int        # 0-5
    evidence_coverage: int      # 0-5

def compute_sub_scores(
    cap_assessments: list,    # filtered to capability_primary == cap_key
    all_assessments: list,    # all assessments for the company in period
    period_start: date,
    period_end: date,
    cap_key: str,
) -> SubScores:
    ...

def compute_relative_strength(scores: SubScores) -> int:
    """Weighted sum, normalized to 0-100."""
    raw = (
        scores.capability_depth * 0.35 +
        scores.execution_momentum * 0.25 +
        scores.market_proof * 0.20 +
        scores.strategic_focus * 0.10 +
        scores.evidence_coverage * 0.10
    )
    return round(raw * (100 / 5))

def determine_tier(score: int, confidence: float, evidence_coverage: int) -> str:
    """Determine tier with confidence correction."""
    if evidence_coverage < 2:
        return "weakly_evidenced"
    if score >= 75:
        tier = "leader"
    elif score >= 55:
        tier = "strong"
    elif score >= 30:
        tier = "emerging"
    else:
        tier = "weakly_evidenced"
    # Confidence downgrade
    if confidence < 0.4 and tier in ("leader", "strong"):
        tier = "strong" if tier == "leader" else "emerging"
    elif confidence < 0.4 and tier == "emerging":
        tier = "weakly_evidenced"
    return tier

def compute_confidence(cap_assessments: list, evidence_coverage: int) -> float:
    """0-1, capped low when few signals."""
    count = len(cap_assessments)
    if count == 0:
        return 0.0
    avg_confidence = sum(a.confidence for a in cap_assessments if a.confidence) / max(1, count)
    raw = (count / 8) * 0.5 + (evidence_coverage / 5) * 0.3 + avg_confidence * 0.2
    confidence = min(1.0, raw)
    if count < 3:
        confidence = min(confidence, 0.3)
    return round(confidence, 2)
```

### Service: BenchmarkQueryService

```python
class BenchmarkQueryService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_overview(self, period_type: str = "30d") -> BenchmarkOverviewResponse:
        """Matrix overview: all competitors × all capabilities."""
        ...
    
    def get_competitor_strengths(self, slug: str, period_type: str = "30d") -> CompetitorBenchmarkResponse:
        """All capability benchmarks for a single competitor."""
        ...
    
    def get_capability_leaderboard(self, cap_key: str, period_type: str = "30d") -> CapabilityLeaderboardResponse:
        """Leaderboard for a specific capability."""
        ...
```

### Service: BenchmarkSummaryLLMService (Optional)

```python
class BenchmarkSummaryLLMService:
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_summary(self, benchmark: CompetitorCapabilityBenchmark, assessments: list) -> str:
        """Generate a 1-2 sentence summary_reason for a benchmark entry."""
        # Uses Claude to generate qualitative summary
        # Input: sub-scores, top 3 assessment summaries, company name, capability label
        # Output: 1-2 sentences in German
        ...
```

### Router: `/api/benchmark/`

```python
router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

@router.get("/overview")
def get_overview(period_type: str = "30d", db: Session = Depends(get_db), user=Depends(auth)):
    ...

@router.get("/competitors/{slug}")
def get_competitor_strengths(slug: str, period_type: str = "30d", db: Session = Depends(get_db), user=Depends(auth)):
    ...

@router.get("/capabilities/{key}")
def get_capability_leaderboard(key: str, period_type: str = "30d", db: Session = Depends(get_db), user=Depends(auth)):
    ...

@router.post("/recompute")
def recompute_all(period_type: str = "30d", db: Session = Depends(get_db), user=Depends(auth)):
    ...

@router.post("/recompute/{company_id}")
def recompute_company(company_id: str, period_type: str = "30d", db: Session = Depends(get_db), user=Depends(auth)):
    ...
```

### Integration in Crawl-Pipeline

In `backend/app/crawler/pipeline.py` oder `backend/app/assessor/pipeline.py`:
Nach erfolgreichem Assessment einer Company wird `BenchmarkAggregationService(db).recompute_company(company_id, "30d")` aufgerufen.

---

## Frontend

### Integration auf `/competitors` Page

Die bestehende `/competitors`-Seite bekommt oben einen neuen Abschnitt:

**Benchmark Matrix Section** (oben)
- Period-Tabs: 30d | 90d | 180d
- Recompute-Button (löst `POST /api/benchmark/recompute` aus)
- **Capability Strength Matrix**: Horizontale Scroll-Tabelle
  - Spalten: 16 Capability-Keys (mit Labels)
  - Zeilen: Alle Competitors
  - Zellen: `relative_strength_score` als Zahl, Hintergrundfarbe nach Tier, Confidence als Opacity
  - Hover: Tooltip mit Tier, Confidence, Rank, Summary-Reason
  - Klick auf Spalten-Header → öffnet CapabilityLeaderboardDrawer
  - Klick auf Competitor-Zelle → navigiert zu `/competitors/{slug}`
- **Top-in-Category Panel**: Kompakte Liste, pro Capability der Leader mit Score und Trend-Pfeil

**Bestehende Card-Liste** (unten, unverändert)

### Neue Komponente auf `/competitors/:slug` Page

**Relative Capability Strength Panel** (unter dem bestehenden CapabilityRadar)

- Klarer visueller Abschnitt mit Überschrift "Relative Capability Strength"
- Pro Capability: Score-Balken, Tier-Badge, Rank, Confidence-Indikator, Delta (↑+7 / ↓-3)
- Visuell getrennt von Activity (CapabilityRadar) und Moves (RecentMovesTimeline)

### Capability Leaderboard Drawer

Slide-in von rechts bei Klick auf eine Capability-Spalte in der Matrix:
- Titel: Capability-Label
- Sortierte Liste aller Competitors nach Score
- Pro Zeile: Rank, Name, Score, Tier-Badge, Confidence, Momentum, Detail-Summary
- Vergleich zum Vorzeitraum (Delta-Anzeige)

### Neue Frontend-Dateien

```
frontend/src/
├── api/benchmark.ts                         # API-Client
├── hooks/useBenchmark.ts                    # React Query Hooks
├── types/benchmark.ts                       # TypeScript-Typen
├── components/benchmark/
│   ├── CapabilityStrengthMatrix.tsx         # Heatmap-Matrix
│   ├── TopInCategoryPanel.tsx              # Leader pro Capability
│   ├── OverallPeerSnapshot.tsx             # Gesamtrangliste
│   ├── CapabilityLeaderboardDrawer.tsx      # Slide-in Drawer
│   ├── TierBadge.tsx                        # Tier-Badge-Komponente
│   ├── ConfidenceIndicator.tsx             # Confidence-Anzeige
│   └── StrengthDeltaIndicator.tsx          # Delta ↑↓→ Indikator
├── components/workspace/
│   └── RelativeCapabilityStrength.tsx       # Neues Panel für Detail-Seite
└── pages/
    └── CompetitorList.tsx                    # Erweitert um Benchmark Section oben
```

### Farbskala & Badges

| Tier | Hintergrund | Text | Badge |
|------|-------------|------|-------|
| leader | emerald-600 (#059669) | weiß | "Leader" grün |
| strong | blue-600 (#2563eb) | weiß | "Strong" blau |
| emerging | amber-500 (#f59e0b) | slate-900 | "Emerging" amber |
| weakly_evidenced | slate-200 (#e2e8f0) | slate-500 | "Weakly Evidenced" grau |

**Confidence-Overlay**: Niedrige Confidence (unter 0.5) macht die Zelle heller/transparenter. Confidence wird nicht als eigener Score dargestellt, sondern als Deckkraft-Modifikator.

### UX-Anforderungen

- Die Matrix muss mit 5-8 Wettbewerbern und 16 Capabilities gut lesbar bleiben
- Horizontal scrollbar wenn nötig
- Hover zeigt Explainability (Confidence, Reason, Sub-Scores)
- Schwache Evidenz (weakly_evidenced) darf nicht wie eine schwache Marktposition aussehen → klar "kaum Belege" statt "schwach"
- Klarheit über Dekoration

---

## Migration

Neue Alembic-Migration für `competitor_capability_benchmarks`-Tabelle.

Rollout:
1. Neue Tabelle erstellen
2. Models und Schemas hinzufügen
3. Services implementieren
4. Router hinzufügen
5. Integration in Crawl-Pipeline
6. Frontend-Komponenten implementieren
7. Initiales `POST /api/benchmark/recompute` für alle bestehenden Daten

---

## Out of Scope (MVP)

- Benchmark-History-Tabelle (kann später ergänzt werden)
- Dashboard-Integration (nur Competitor-Seiten)
- Benchmark-Vergleich über Zeiträume (nur Delta zum Vor-Compute)
- Export/Download der Matrix
- LLM-generierte Competitor-Vergleichs-Narrative