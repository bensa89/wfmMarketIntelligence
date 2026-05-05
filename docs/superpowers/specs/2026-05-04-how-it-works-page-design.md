# Design Spec: "How It Works" Documentation Page

**Date:** 2026-05-04  
**Status:** Approved for implementation  
**Route:** `/how-it-works`  
**Nav placement:** Admin section in sidebar

---

## Goal

A static, non-technical documentation page that explains to stakeholders (management, product owners, new team members) what the WFM Market Intelligence Hub does, how it works end-to-end, and why they can trust the outputs. No code references, no Python — just clear process explanation with optional depth on demand.

---

## Didactic Approach

**Running example:** Throughout the entire page, a single concrete case is followed from start to finish:

> *"Workday publishes a blog post: 'Introducing AI Scheduling Copilot for Enterprise Teams'"*

Every section shows what the system does with this exact article at that step. By the end of the page, the reader has seen how a blog post becomes a strategic recommendation — without ever reading code.

**Two content layers:**
- **Plain language** always visible — explains what happens and why it matters
- **Expandable panels** on demand — for readers who want depth:
  - "Datenstruktur anzeigen" — the data model fields introduced at that step
  - "Prompt anzeigen" — LLM prompt paraphrase + verbatim (KI steps only)

**Deterministic vs. KI badge:**  
Every pipeline step is labeled with a small badge:
- 🔢 **Regel** — deterministic, always produces the same output for the same input
- 🤖 **KI** — evaluated by LLM, context-sensitive and interpretive

This distinction helps stakeholders understand what is reliable/consistent vs. what involves judgment.

---

## Page Structure

### 1. Hero

Short intro (3 sentences):
- What the tool does (monitors competitor and market websites, extracts intelligence signals)
- Why it exists (manual monitoring doesn't scale; the tool automates what would take hours per day)
- For whom (product, strategy, and GTM teams)

Immediately followed by the **running example introduction box** (amber/yellow highlight):

> *"Um zu zeigen wie das Tool funktioniert, begleiten wir einen konkreten Fall von Anfang bis Ende: Workday veröffentlicht auf ihrem Blog den Artikel 'Introducing AI Scheduling Copilot for Enterprise Teams'. Wir sehen auf jeder Stufe was das System damit macht — und am Ende ist aus diesem Blogpost eine konkrete Handlungsempfehlung für unser Produkt geworden."*

---

### 2. Visual Pipeline Flow (sticky/scrollable)

A horizontal row of 7 clickable boxes with arrows between them. On click, scrolls to the corresponding section. The active section highlights the corresponding box (achieved via IntersectionObserver).

```
[Quellen] → [Crawlen 🔢] → [Signal-Analyse 🤖] → [Tiefenbewertung 🤖] → [Capability-Mapping 🔢] → [Benchmark 🔢] → [Briefings 🤖]
```

Each box shows:
- Step name
- 🔢 or 🤖 badge
- One-sentence description

Mobile: horizontally scrollable.

---

### 3. Section: Quellen & Crawling 🔢

**Explanation (plain language):**  
Quellen — Blogs, Newsseiten, Produktseiten, Karriereseiten — werden einmalig in der Admin-Oberfläche gepflegt und jeweils einem Unternehmen (Wettbewerber oder Markbeobachtungsquelle) zugeordnet. Das System besucht regelmäßig jede aktive Quelle, lädt den Inhalt herunter und wandelt ihn automatisch in lesbaren Text um. Jedes Dokument erhält einen digitalen Fingerabdruck (SHA-256 Hash) — existiert dieser Fingerabdruck bereits in der Datenbank, wird der Inhalt übersprungen. So werden Duplikate zuverlässig vermieden, ohne den Inhalt erneut zu analysieren.

**Running example box:**  
*"Das System findet den Workday-Blogpost unter blog.workday.com/..., wandelt ihn von HTML in lesbaren Text um und berechnet seinen Fingerabdruck. Da dieser Hash noch nicht bekannt ist, wird ein neues Dokument gespeichert und zur Analyse weitergegeben."*

**Expandable: Datenstruktur — Company**
| Feld | Beschreibung |
|---|---|
| name | Name des Unternehmens |
| slug | URL-freundlicher Bezeichner (z.B. `workday`) |
| type | `competitor` oder `market_source` |
| description | Kurzbeschreibung |

**Expandable: Datenstruktur — Source**
| Feld | Beschreibung |
|---|---|
| url | URL der Quelle |
| type | Art der Quelle: `news`, `blog`, `product`, `press`, `jobs` |
| company | Zugehöriges Unternehmen |
| is_active | Ob die Quelle aktiv gecrawlt wird |

**Expandable: Datenstruktur — Document**
| Feld | Beschreibung |
|---|---|
| url | Ursprungs-URL des Dokuments |
| content_markdown | Extrahierter Textinhalt |
| content_hash | SHA-256 Fingerabdruck (für Dedup) |
| published_at | Veröffentlichungsdatum (aus HTML Meta-Tags) |
| crawled_at | Zeitpunkt des Crawls |
| is_analysed | Ob das Dokument bereits analysiert wurde |

---

### 4. Section: Signal-Analyse 🤖

**Explanation (plain language):**  
Jedes neue Dokument wird einem KI-Analysten übergeben. Dieser kennt unser eigenes Unternehmensprofil — unsere Zielmärkte, Kernkompetenzen und strategischen Prioritäten — und liest den Inhalt vor diesem Hintergrund. Er bewertet: Was ist die Kernaussage? Welchen Signaltyp hat diese Information? Und — entscheidend — wie relevant ist das konkret für uns (Relevanz-Score 0–1) und wie sicher ist er sich (Confidence-Score 0–1)?

Vor der KI-Analyse prüft das System zwei **regelbasierte Filter** (🔢):
- Dokumente mit weniger als 50 Wörtern werden übersprungen (kein verwertbarer Inhalt)
- Dokumente älter als 365 Tage werden übersprungen (veraltete Information)

**Die 8 Signal-Typen:**
| Typ | Bedeutung |
|---|---|
| `product_update` | Neue Produktfeatures oder -versionen |
| `ai_announcement` | KI-bezogene Produktankündigungen |
| `partnership` | Partnerschaften und Integrationen |
| `positioning_change` | Veränderung in Messaging oder Positionierung |
| `target_market_change` | Neue Zielmärkte oder Segmente |
| `event_or_thought_leadership` | Events, Whitepapers, Keynotes |
| `hiring_signal` | Stellenausschreibungen als strategisches Signal |
| `other` | Sonstiges |

**Running example box:**  
*"Der KI-Analyst liest den Workday-Artikel und erstellt ein Signal: Typ `ai_announcement`, Titel 'Workday launches AI Scheduling Copilot', Relevanz-Score 0.88 (sehr relevant — direkter Angriff auf unsere KI-Roadmap), Confidence 0.92 (hohe Sicherheit). Das Veröffentlichungsdatum wird aus dem Artikel extrahiert: 2026-04-18."*

**Expandable: Prompt anzeigen**  
*Paraphrase:* Der Analyst erhält das Unternehmensprofil (Märkte, Capabilities, Prioritäten) und den Artikeltext. Er soll genau ein Signal extrahieren: Was passiert hier, welchen Typ hat es, warum ist es für uns relevant, und wie sicher ist er sich? Er antwortet ausschließlich mit einem strukturierten JSON-Objekt.  
*Verbatim prompt:* → `backend/app/analyser/prompts.py :: build_analysis_prompt()`

**Expandable: Datenstruktur — Signal**
| Feld | Beschreibung |
|---|---|
| title | Kurzer beschreibender Titel (max. 100 Zeichen) |
| signal_type | Einer der 8 Typen (s.o.) |
| topic | Hauptthema (max. 60 Zeichen) |
| summary | 2–3 Sätze faktische Zusammenfassung |
| why_it_matters | 1–2 Sätze strategische Relevanz für uns |
| relevance_score | 0.0 (irrelevant) – 1.0 (hochrelevant) |
| confidence_score | 0.0 (unsicher) – 1.0 (sehr sicher) |
| published_at | Veröffentlichungsdatum des Originalinhalts |
| company | Zugehöriger Wettbewerber |
| document | Quell-Dokument |

**Expandable: Datenstruktur — InternalCompanyContext**
| Feld | Beschreibung |
|---|---|
| company_name | Unser Unternehmensname |
| short_description | Kurzbeschreibung unseres Produkts |
| target_industries | Zielbranchen (Liste) |
| target_segments | Zielsegmente (Liste) |
| core_capabilities | Kernkompetenzen (Liste) |
| strategic_priorities | Strategische Prioritäten (Liste) |
| differentiators | Differenzierungsmerkmale (Liste) |
| relevant_competitive_areas | Relevante Wettbewerbsbereiche (Liste) |
| non_focus_areas | Explizit nicht relevante Bereiche (Liste) |

---

### 5. Section: Tiefenbewertung (Assessment) 🤖

**Explanation (plain language):**  
Signale, deren Relevanz-Score einen konfigurierbaren Schwellenwert überschreitet, werden einem zweiten, spezialisierten KI-Analysten übergeben. Dieser geht tiefer: Er ordnet das Signal einer konkreten WFM-Capability zu (z.B. "AI Copilot" oder "Shift Scheduling"), klassifiziert die Art des strategischen Moves, schätzt wie belastbar der Beweis ist (Evidence Strength 1–5) und leitet ab, was die strategische Absicht des Wettbewerbers ist — und was das konkret für uns bedeutet.

**Signal Classes:**
| Klasse | Bedeutung |
|---|---|
| `product_capability_move` | Produktentwicklung in einer Capability |
| `positioning_move` | Veränderung in Marktpositionierung |
| `ecosystem_move` | Partnerschaften, Integrationen |
| `thought_leadership_signal` | Events, Content, Whitepapers |
| `hiring_signal` | Personalstrategie als Indikator |
| `market_expansion_move` | Expansion in neue Märkte/Segmente |
| `weak_signal` | Schwaches oder unklares Signal |

**Running example box:**  
*"Das Signal überschreitet den Schwellenwert (0.88 ≥ 0.7). Der Assessment-Analyst bewertet: Capability `ai_copilot` (primär), Signal Class `product_capability_move`, Evidence Strength 4/5, Visibility Impact: high. Strategic Intent: 'Differenzierung über KI im Kernprodukt Scheduling'. Implication for us: 'Direkter Angriff auf unsere KI-Roadmap — Priorisierung des AI Copilot Moduls überdenken.'"*

**Expandable: Prompt anzeigen**  
*Paraphrase:* Der Assessment-Analyst erhält das vollständige Signal (Titel, Typ, Zusammenfassung, Scores) sowie unser Kontext-Profil und die Liste der 16 WFM-Capabilities. Er soll die Capability benennen, die am stärksten betroffen ist, die strategische Absicht des Wettbewerbers einschätzen und konkrete Watchpoints für uns ableiten.  
*Verbatim prompt:* → `backend/app/assessor/prompts.py :: build_assessment_prompt()`

**Expandable: Datenstruktur — SignalAssessment**
| Feld | Beschreibung |
|---|---|
| capability_primary | Primär betroffene WFM-Capability |
| capability_secondary | Weitere betroffene Capabilities (Liste) |
| signal_class | Art des strategischen Moves (s.o.) |
| evidence_strength | Beweisstärke 1 (schwach) – 5 (sehr stark) |
| visibility_impact | Marktsichtbarkeit: `low`, `medium`, `high` |
| strategic_intent_guess | Vermutete strategische Absicht (1 Satz) |
| gameplay_tags | Kategorisierungs-Tags (Liste) |
| assessment_summary | 2–3 Sätze was dieses Signal bedeutet |
| implication_for_us | 1–2 Sätze was das für unser Produkt bedeutet |
| watch_items | Konkrete Dinge die zu beobachten sind (Liste) |
| movement_score | Deterministisch berechneter Score 0–100 (s. Sektion 6) |
| movement_strength | Abgeleitete Stärke: `weak`, `relevant`, `strong`, `market_shaping` |

---

### 6. Section: Capability-Mapping & Movement Score 🔢

**Explanation (plain language):**  
Aus den Assessment-Daten berechnet das System deterministisch einen **Movement Score** (0–100) pro Signal. Die Formel gewichtet vier Faktoren: Relevanz des Signals für uns, Confidence des Analysten, Beweisstärke und Marktsichtbarkeit. Ein Abzug erfolgt für reine Thought-Leadership-Signale (weniger operativ relevant). Daraus wird eine **Movement Strength** abgeleitet: `weak → relevant → strong → market_shaping`.

**Movement Score Formel (🔢):**
```
Score = (Relevanz × 35) + (Confidence × 20) + (Evidence Strength × 6) + Visibility-Bonus − Thought-Leadership-Abzug
Visibility-Bonus: low=0, medium=8, high=15
Thought-Leadership-Abzug: −10
```

**Movement Strength Schwellenwerte:**
| Score | Strength |
|---|---|
| 0–29 | `weak` |
| 30–59 | `relevant` |
| 60–79 | `strong` |
| 80–100 | `market_shaping` |

**Die 16 WFM-Capabilities** (aufklappbare Tabelle):
| Capability | Strategisches Gewicht | Wardley-Band |
|---|---|---|
| Shift Scheduling | 10/10 | product |
| Demand Forecasting | 9/10 | product |
| AI Copilot | 9/10 | genesis |
| Optimization Engine | 9/10 | product |
| Compliance & Labor Rules | 8/10 | product |
| Intraday Management | 8/10 | product |
| Analytics & Insights | 8/10 | product |
| Platform & Ecosystem | 8/10 | product |
| Time & Attendance | 7/10 | product |
| Manager Experience | 7/10 | product |
| Workflow Automation | 7/10 | product |
| Integration Hub | 7/10 | product |
| Vertical Solutions | 7/10 | product |
| Employee Self-Service | 6/10 | product |
| Mobile Experience | 6/10 | product |
| Data Foundation | 6/10 | product |

Das Wardley-Band zeigt wo sich eine Capability im Evolutionszyklus befindet: `genesis` (neu, experimentell) → `custom` → `product` → `commodity`. Signale von Wettbewerbern können anzeigen, dass eine Capability von `genesis` Richtung `product` wandert — ein strategisch wichtiges Frühwarnsignal.

**Running example box:**  
*"Movement Score für das Workday-Signal: (0.88×35) + (0.92×20) + (4×6) + 15 = 30.8 + 18.4 + 24 + 15 = 88.2 → gerundet: 88 → Movement Strength: `market_shaping`. Das Signal bewegt die Nadel bei `ai_copilot` (strategisches Gewicht 9/10, aktuell im Wardley-Band `genesis` — Workday schiebt diese Capability aktiv Richtung `product`)."*

---

### 7. Section: Benchmark-Berechnung 🔢

**Explanation (plain language):**  
Über einen gewählten Zeitraum (30/90/180 Tage) aggregiert das System alle Assessments aller Wettbewerber pro Capability. Das Ergebnis ist die **Capability Strength Matrix**: Eine Übersicht welcher Wettbewerber in welchem Bereich wie aktiv ist und welche Bewegungsstärke er dabei zeigt. Diese Matrix ist der schnellste Weg um zu verstehen wo der Markt sich gerade bewegt — und wo wir besonders aufmerksam sein sollten.

**Running example box:**  
*"Nach 30 Tagen hat Workday 5 Signals zu `ai_copilot` produziert, davon 3 mit `strong` oder `market_shaping`. In der Capability Strength Matrix erscheint Workday als stärkster Akteur in `ai_copilot` des aktuellen Zeitraums."*

**Expandable: Datenstruktur — CompetitorSummary**
| Feld | Beschreibung |
|---|---|
| company | Bewerteter Wettbewerber |
| period_type | Zeitraum: `7d`, `30d`, `90d` |
| strategic_posture | KI-generiertes Label (z.B. `aggressive_expansion`) |
| positioning_summary | 2–3 Sätze zur strategischen Ausrichtung |
| top_capabilities | Aktivste Capabilities im Zeitraum |
| capability_assessment | Aktivitätslevel pro Capability |
| top_risks | Risiken für uns (Liste) |
| top_opportunities | Chancen für uns (Liste) |
| watchpoints | Konkrete Beobachtungspunkte (Liste) |
| avg_movement_score | Durchschnittlicher Movement Score |
| signal_count | Anzahl Signals im Zeitraum |

---

### 8. Section: Competitor Summary 🤖

**Explanation (plain language):**  
Auf Knopfdruck (oder automatisch) fasst ein KI-Analyst alle Assessments eines Wettbewerbers für einen gewählten Zeitraum zusammen. Das Ergebnis ist ein vollständiges strategisches Profil: Wie ist die Gesamtausrichtung des Wettbewerbers gerade? In welchen Capabilities ist er am aktivsten? Was sind die konkreten Risiken und Chancen für uns — und was sollten wir in den nächsten Wochen besonders beobachten?

**Running example box:**  
*"Nach 30 Tagen mit mehreren Workday-Signalen generiert das System eine Competitor Summary: Strategic Posture: `aggressive_ai_expansion`. Top Capabilities: `ai_copilot`, `shift_scheduling`. Top Risk for us: 'Workday positioniert KI als Standard-Feature — Gefahr der Commoditisierung unseres AI-Differenzierers.' Watchpoint: 'Nächste Workday Rising Keynote auf weitere AI-Announcements überwachen.'"*

**Expandable: Prompt anzeigen**  
*Paraphrase:* Der Analyst bekommt alle Assessments des Wettbewerbers im Zeitraum als strukturierte Liste sowie unser Kontext-Profil. Er soll ein zusammenfassendes strategisches Bild zeichnen: Gesamtausrichtung, stärkste Capabilities, was das für uns bedeutet.  
*Verbatim prompt:* → `backend/app/assessor/prompts.py :: build_summary_prompt()`

---

### 9. Section: Briefings 🤖

Zwei klar getrennte Briefing-Typen, jeweils mit eigenem Erklärungsblock:

**Weekly Digest (Dashboard)**  
Einmal pro Woche (oder auf Anfrage) aggregiert das System alle neuen Signals der letzten 7 Tage. Ein KI-Analyst fasst zusammen: Welche Unternehmen waren besonders aktiv? Was waren die wichtigsten Signale? Und er leitet drei priorisierte Handlungsempfehlungen ab — als Markdown-Tabelle mit direkten Links zu den Originalquellen. Dieser Digest erscheint auf dem Dashboard.

*Expandable: Prompt anzeigen* → `backend/app/analyser/briefing.py :: _build_briefing_prompt()`

**Intelligence Briefing (Overview)**  
Das Intelligence Briefing ist selektiver: Es berücksichtigt nur Signals mit Movement Strength `strong` oder `market_shaping`. Ein KI-Analyst erstellt daraus ein strategisches Executive Summary (2–3 Sätze Marktüberblick) plus bis zu 3 priorisierte Handlungsempfehlungen für Produkt und GTM. Dieser Briefing erscheint auf der Overview-Seite.

*Expandable: Prompt anzeigen* → `backend/app/assessor/intel_briefing.py :: generate_intelligence_briefing()`

**Running example box:**  
*"Das Workday-Signal mit Movement Score 88 (`market_shaping`) erscheint im Intelligence Briefing: 'Workday beschleunigt AI-Investitionen im Scheduling-Kernprodukt — direkter Wettbewerbsdruck auf unsere AI-Roadmap.' Empfehlung #1: 'AI Copilot Modul priorisieren — Workday schiebt diesen Bereich aktiv Richtung Marktstandard.'"*

---

### 10. Section: Bewertungskriterien

Visuelle Übersicht der 4 Scores mit Skala, Bedeutung und Beispielwerten:

| Score | Skala | Wer berechnet | Bedeutung |
|---|---|---|---|
| **Relevanz-Score** | 0.0 – 1.0 | 🤖 KI | Wie relevant ist dieses Signal für unsere Strategie und Märkte? |
| **Confidence-Score** | 0.0 – 1.0 | 🤖 KI | Wie sicher ist der Analyst sich bei seiner Einschätzung? |
| **Evidence Strength** | 1 – 5 | 🤖 KI | Wie belastbar ist der Beweis im Assessment? |
| **Movement Score** | 0 – 100 | 🔢 Formel | Wie stark bewegt sich ein Wettbewerber in einer Capability? |

Beispiel-Legende:
- Relevanz 0.0–0.3: Kaum relevant (anderer Markt, andere Zielgruppe)
- Relevanz 0.4–0.6: Peripher relevant (beobachten)
- Relevanz 0.7–0.85: Relevant (aktiv verfolgen)
- Relevanz 0.86–1.0: Hochrelevant (sofort handeln)

---

## Implementation Notes

**Technology:** Static React page, no API calls. All content hardcoded in the component.

**New files:**
- `frontend/src/pages/HowItWorksPage.tsx` — main page
- `frontend/src/components/docs/PipelineFlow.tsx` — sticky pipeline flow component
- `frontend/src/components/docs/PipelineSection.tsx` — reusable section with expandable panels
- `frontend/src/components/docs/ExpandablePanel.tsx` — generic expand/collapse panel

**Routing:** Add `<Route path="how-it-works" element={<HowItWorksPage />} />` in `App.tsx`

**Nav:** Add entry to `Admin` section in `Layout.tsx`:
```
{ to: '/how-it-works', label: 'Wie funktioniert\'s?', icon: BookOpen }
```

**Expandable panels:** Use a simple `useState` toggle per panel. No library needed.

**Pipeline highlight on scroll:** `IntersectionObserver` on each section, updates active step in pipeline flow.

**Styling:** Follow existing Tailwind + dark sidebar conventions. Running example boxes use `bg-amber-950/30 border border-amber-700/40`. KI badge: `bg-purple-900/40 text-purple-300`. Regel badge: `bg-blue-900/40 text-blue-300`.

---

## Out of Scope

- Live data from the API (signal counts, recent activity) — static only
- Editable prompts from the UI
- Internationalization (page is in German)
