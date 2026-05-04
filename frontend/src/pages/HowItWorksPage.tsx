import { useEffect, useRef, useState } from 'react';
import { PipelineFlow } from '../components/docs/PipelineFlow';
import type { PipelineStep } from '../components/docs/PipelineFlow';
import { PipelineSection } from '../components/docs/PipelineSection';
import { ExpandablePanel } from '../components/docs/ExpandablePanel';

const STEPS: PipelineStep[] = [
  { id: 'quellen', label: 'Quellen', type: 'rule', description: 'Quellen & Crawling' },
  { id: 'analyse', label: 'Signal-Analyse', type: 'ai', description: 'KI extrahiert Signal' },
  { id: 'assessment', label: 'Tiefenbewertung', type: 'ai', description: 'KI bewertet tiefer' },
  { id: 'capabilities', label: 'Capability-Mapping', type: 'rule', description: 'Movement Score' },
  { id: 'benchmark', label: 'Benchmark', type: 'rule', description: 'Stärke-Matrix' },
  { id: 'summary', label: 'Competitor Summary', type: 'ai', description: 'KI synthetisiert' },
  { id: 'briefing', label: 'Briefings', type: 'ai', description: 'KI-Zusammenfassung' },
];

export default function HowItWorksPage() {
  const [activeStep, setActiveStep] = useState<string | null>('quellen');
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveStep(entry.target.id);
          }
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    );

    STEPS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observerRef.current?.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, []);

  return (
    <div className="min-h-screen" style={{ background: '#0f172a' }}>
      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Hero */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-100 mb-3">Wie funktioniert das Tool?</h1>
          <p className="text-[15px] text-slate-400 leading-relaxed max-w-2xl">
            Das WFM Market Intelligence Hub überwacht automatisch Websites von Wettbewerbern und
            Marktquellen, extrahiert relevante Signale und bewertet sie gegen unsere eigene
            Strategie. Was früher Stunden manueller Recherche gekostet hat, läuft jetzt
            kontinuierlich im Hintergrund — und liefert täglich priorisierte, handlungsorientierte
            Einblicke für Produkt, Strategie und GTM.
          </p>
        </div>

        {/* Running example intro */}
        <div className="rounded-lg border border-amber-700/40 bg-amber-950/20 px-5 py-4 mb-8">
          <p className="text-[11px] font-semibold text-amber-500 uppercase tracking-wider mb-2">
            Roter Faden — unser Beispiel
          </p>
          <p className="text-[14px] text-amber-200/80 leading-relaxed">
            Um zu zeigen wie das Tool funktioniert, begleiten wir einen konkreten Fall von Anfang
            bis Ende:{' '}
            <strong className="text-amber-300">
              Workday veröffentlicht auf ihrem Blog den Artikel „Introducing AI Scheduling Copilot
              for Enterprise Teams"
            </strong>
            . Wir sehen auf jeder Stufe was das System damit macht — und am Ende ist aus diesem
            Blogpost eine konkrete Handlungsempfehlung für unser Produkt geworden.
          </p>
        </div>

        <PipelineFlow
          steps={STEPS}
          activeStep={activeStep}
          onStepClick={setActiveStep}
        />

        {/* ── SEKTION 1: Quellen & Crawling ── */}
<PipelineSection
  id="quellen"
  title="Quellen & Crawling"
  type="rule"
  explanation={
    <>
      <p>
        Quellen — Blogs, Newsseiten, Produktseiten, Karriereseiten — werden einmalig in
        der Admin-Oberfläche gepflegt und jeweils einem Unternehmen (Wettbewerber oder
        Marktbeobachtungsquelle) zugeordnet. Das System besucht regelmäßig jede aktive
        Quelle, lädt den Inhalt herunter und wandelt ihn automatisch in lesbaren Text um.
      </p>
      <p>
        Jedes Dokument erhält einen digitalen Fingerabdruck (SHA-256 Hash). Existiert
        dieser Fingerabdruck bereits in der Datenbank, wird der Inhalt übersprungen —
        so werden Duplikate zuverlässig vermieden, ohne den Inhalt erneut zu analysieren.
      </p>
    </>
  }
  example={
    <p>
      Das System findet den Workday-Blogpost unter blog.workday.com/…, wandelt ihn von
      HTML in lesbaren Text um und berechnet seinen Fingerabdruck. Da dieser Hash noch
      nicht bekannt ist, wird ein neues Dokument gespeichert und zur Analyse
      weitergegeben.
    </p>
  }
>
  <ExpandablePanel title="Datenstruktur — Company">
    <table className="w-full text-xs mt-2 border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Feld</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Beschreibung</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['name', 'Name des Unternehmens'],
          ['slug', 'URL-freundlicher Bezeichner (z.B. workday)'],
          ['type', 'competitor oder market_source'],
          ['description', 'Kurzbeschreibung'],
        ].map(([field, desc]) => (
          <tr key={field} className="border-b border-white/5">
            <td className="py-1.5 pr-4 font-mono text-blue-300">{field}</td>
            <td className="py-1.5">{desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>

  <ExpandablePanel title="Datenstruktur — Source">
    <table className="w-full text-xs mt-2 border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Feld</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Beschreibung</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['url', 'URL der zu crawlenden Seite'],
          ['type', 'news | blog | product | press | jobs'],
          ['company', 'Zugehöriges Unternehmen'],
          ['is_active', 'Ob die Quelle aktiv gecrawlt wird'],
        ].map(([field, desc]) => (
          <tr key={field} className="border-b border-white/5">
            <td className="py-1.5 pr-4 font-mono text-blue-300">{field}</td>
            <td className="py-1.5">{desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>

  <ExpandablePanel title="Datenstruktur — Document">
    <table className="w-full text-xs mt-2 border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Feld</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Beschreibung</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['url', 'Ursprungs-URL'],
          ['content_markdown', 'Extrahierter Textinhalt'],
          ['content_hash', 'SHA-256 Fingerabdruck (für Dedup)'],
          ['published_at', 'Veröffentlichungsdatum aus HTML Meta-Tags'],
          ['crawled_at', 'Zeitpunkt des Crawls'],
          ['is_analysed', 'Ob das Dokument bereits analysiert wurde'],
        ].map(([field, desc]) => (
          <tr key={field} className="border-b border-white/5">
            <td className="py-1.5 pr-4 font-mono text-blue-300">{field}</td>
            <td className="py-1.5">{desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>
</PipelineSection>

{/* ── SEKTION 2: Signal-Analyse ── */}
<PipelineSection
  id="analyse"
  title="Signal-Analyse"
  type="ai"
  explanation={
    <>
      <p>
        Jedes neue Dokument wird einem KI-Analysten übergeben. Dieser kennt unser
        eigenes Unternehmensprofil — unsere Zielmärkte, Kernkompetenzen und strategischen
        Prioritäten — und liest den Inhalt vor diesem Hintergrund. Er bewertet: Was ist
        die Kernaussage? Welchen Signaltyp hat diese Information? Und wie relevant ist das
        für uns (Relevanz-Score 0–1) und wie sicher ist er sich (Confidence-Score 0–1)?
      </p>
      <p>
        Vor der KI-Analyse prüft das System zwei{' '}
        <span className="text-blue-400 font-medium">🔢 regelbasierte Filter</span>:
        Dokumente mit weniger als 50 Wörtern werden übersprungen; Dokumente älter als 365
        Tage ebenfalls.
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {[
          ['product_update', 'Neue Produktfeatures oder -versionen'],
          ['ai_announcement', 'KI-bezogene Produktankündigungen'],
          ['partnership', 'Partnerschaften und Integrationen'],
          ['positioning_change', 'Veränderung in Messaging oder Positionierung'],
          ['target_market_change', 'Neue Zielmärkte oder Segmente'],
          ['event_or_thought_leadership', 'Events, Whitepapers, Keynotes'],
          ['hiring_signal', 'Stellenausschreibungen als strategisches Signal'],
          ['other', 'Sonstiges'],
        ].map(([type, desc]) => (
          <div key={type} className="flex gap-2">
            <code className="text-blue-300 text-[11px] flex-shrink-0">{type}</code>
            <span className="text-slate-500 text-[11px]">{desc}</span>
          </div>
        ))}
      </div>
    </>
  }
  example={
    <p>
      Der KI-Analyst liest den Workday-Artikel und erstellt ein Signal: Typ{' '}
      <code className="text-purple-300 bg-purple-900/30 px-1 rounded">ai_announcement</code>,
      Titel „Workday launches AI Scheduling Copilot", Relevanz-Score{' '}
      <strong className="text-amber-300">0.88</strong> (sehr relevant — direkter Angriff
      auf unsere KI-Roadmap), Confidence{' '}
      <strong className="text-amber-300">0.92</strong>. Das Veröffentlichungsdatum wird
      aus dem Artikel extrahiert: 2026-04-18.
    </p>
  }
>
  <ExpandablePanel title="Prompt anzeigen" variant="prompt">
    <p className="mb-3 text-slate-300">
      Der Analyst erhält das Unternehmensprofil (Märkte, Capabilities, Prioritäten) und
      den Artikeltext. Er soll genau ein Signal extrahieren: Was passiert hier, welchen
      Typ hat es, warum ist es für uns relevant, wie sicher ist er sich? Er antwortet
      ausschließlich mit einem JSON-Objekt — kein Fließtext, keine Erklärung.
    </p>
    <pre className="bg-slate-900/60 rounded p-3 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">{`Du bist ein Market Intelligence Analyst für folgendes Unternehmen:

Company: [aus dem Kontext-Profil]
Target Industries: [Liste aus dem Kontext-Profil]
Core Capabilities: [Liste aus dem Kontext-Profil]
Strategic Priorities: [Liste aus dem Kontext-Profil]
Differentiators: [Liste aus dem Kontext-Profil]
Non-Focus Areas: [Liste aus dem Kontext-Profil]

Analysiere folgenden Wettbewerber-/Marktinhalt und extrahiere ein strukturiertes Signal.

INHALT:
[Artikeltext, max. 4.000 Zeichen]

Berücksichtige auch Aktualität: Neuere Entwicklungen sollen einen höheren
relevance_score erhalten als ältere, veraltete Informationen.

Antworte NUR mit einem validen JSON-Objekt nach diesem Schema:
{
  "title": "kurzer beschreibender Titel (max. 100 Zeichen)",
  "signal_type": "product_update | ai_announcement | partnership | ...",
  "topic": "Hauptthema (max. 60 Zeichen)",
  "summary": "2-3 Sätze faktische Zusammenfassung",
  "why_it_matters": "1-2 Sätze strategische Relevanz für uns",
  "relevance_score": 0.0 bis 1.0,
  "confidence_score": 0.0 bis 1.0,
  "published_at": "ISO-8601 Datum oder null"
}`}</pre>
  </ExpandablePanel>

  <ExpandablePanel title="Datenstruktur — Signal">
    <table className="w-full text-xs mt-2 border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Feld</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Beschreibung</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['title', 'Kurzer beschreibender Titel (max. 100 Zeichen)'],
          ['signal_type', 'Einer der 8 Signal-Typen'],
          ['topic', 'Hauptthema (max. 60 Zeichen)'],
          ['summary', '2–3 Sätze faktische Zusammenfassung'],
          ['why_it_matters', '1–2 Sätze strategische Relevanz für uns'],
          ['relevance_score', '0.0 (irrelevant) – 1.0 (hochrelevant)'],
          ['confidence_score', '0.0 (unsicher) – 1.0 (sehr sicher)'],
          ['published_at', 'Veröffentlichungsdatum des Originalinhalts'],
          ['company', 'Zugehöriger Wettbewerber'],
          ['document', 'Quell-Dokument'],
        ].map(([field, desc]) => (
          <tr key={field} className="border-b border-white/5">
            <td className="py-1.5 pr-4 font-mono text-blue-300">{field}</td>
            <td className="py-1.5">{desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>

  <ExpandablePanel title="Datenstruktur — InternalCompanyContext (unser Profil)">
    <p className="text-[12px] text-slate-400 mt-1 mb-2">
      Dieses Profil wird bei jeder KI-Analyse mitgegeben, damit die KI einschätzen kann
      wie relevant ein Signal für uns spezifisch ist.
    </p>
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Feld</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Beschreibung</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['company_name', 'Unser Unternehmensname'],
          ['short_description', 'Kurzbeschreibung unseres Produkts'],
          ['target_industries', 'Zielbranchen (Liste)'],
          ['target_segments', 'Zielsegmente (Liste)'],
          ['core_capabilities', 'Kernkompetenzen (Liste)'],
          ['strategic_priorities', 'Strategische Prioritäten (Liste)'],
          ['differentiators', 'Differenzierungsmerkmale (Liste)'],
          ['relevant_competitive_areas', 'Relevante Wettbewerbsbereiche (Liste)'],
          ['non_focus_areas', 'Explizit nicht relevante Bereiche (Liste)'],
        ].map(([field, desc]) => (
          <tr key={field} className="border-b border-white/5">
            <td className="py-1.5 pr-4 font-mono text-blue-300">{field}</td>
            <td className="py-1.5">{desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>
</PipelineSection>

{/* ── SEKTION 3: Tiefenbewertung ── */}
<PipelineSection
  id="assessment"
  title="Tiefenbewertung (Assessment)"
  type="ai"
  explanation={
    <>
      <p>
        Signale, deren Relevanz-Score einen konfigurierbaren Schwellenwert überschreitet,
        werden einem zweiten, spezialisierten KI-Analysten übergeben. Dieser geht tiefer:
        Er ordnet das Signal einer konkreten WFM-Capability zu (z.B. „AI Copilot" oder
        „Shift Scheduling"), klassifiziert die Art des strategischen Moves, schätzt wie
        belastbar der Beweis ist (Evidence Strength 1–5) und leitet ab, was die
        strategische Absicht des Wettbewerbers ist — und was das für uns konkret bedeutet.
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {[
          ['product_capability_move', 'Produktentwicklung in einer Capability'],
          ['positioning_move', 'Veränderung in Marktpositionierung'],
          ['ecosystem_move', 'Partnerschaften, Integrationen'],
          ['thought_leadership_signal', 'Events, Content, Whitepapers'],
          ['hiring_signal', 'Personalstrategie als Indikator'],
          ['market_expansion_move', 'Expansion in neue Märkte / Segmente'],
          ['weak_signal', 'Schwaches oder unklares Signal'],
        ].map(([cls, desc]) => (
          <div key={cls} className="flex gap-2">
            <code className="text-purple-300 text-[11px] flex-shrink-0">{cls}</code>
            <span className="text-slate-500 text-[11px]">{desc}</span>
          </div>
        ))}
      </div>
    </>
  }
  example={
    <p>
      Das Signal überschreitet den Schwellenwert (0.88 ≥ 0.7). Der Assessment-Analyst
      bewertet: Capability{' '}
      <code className="text-purple-300 bg-purple-900/30 px-1 rounded">ai_copilot</code>{' '}
      (primär), Signal Class{' '}
      <code className="text-purple-300 bg-purple-900/30 px-1 rounded">
        product_capability_move
      </code>
      , Evidence Strength <strong className="text-amber-300">4/5</strong>, Visibility
      Impact: <strong className="text-amber-300">high</strong>. Strategic Intent:
      „Differenzierung über KI im Kernprodukt Scheduling". Implication for us: „Direkter
      Angriff auf unsere KI-Roadmap — Priorisierung des AI Copilot Moduls überdenken."
    </p>
  }
>
  <ExpandablePanel title="Prompt anzeigen" variant="prompt">
    <p className="mb-3 text-slate-300">
      Der Assessment-Analyst erhält das vollständige Signal sowie unser Kontext-Profil
      und die Liste der 16 WFM-Capabilities. Er soll die betroffene Capability benennen,
      die strategische Absicht des Wettbewerbers einschätzen und konkrete Watchpoints
      ableiten.
    </p>
    <pre className="bg-slate-900/60 rounded p-3 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">{`Bewerte dieses Wettbewerber-Signal für einen WFM-Software-Anbieter.

Signal:
- Unternehmen: [Wettbewerber-Name]
- Typ: [signal_type]
- Titel: [title]
- Zusammenfassung: [summary]
- Warum es wichtig ist: [why_it_matters]
- Relevanz-Score: [relevance_score]
- Confidence-Score: [confidence_score]

Unser interner Kontext:
- Kernkompetenzen: [core_capabilities]
- Strategische Prioritäten: [strategic_priorities]

Verfügbare Capability-Keys: [Liste der 16 Capabilities]

Antworte mit genau diesem JSON-Objekt:
{
  "capability_primary": "<ein Capability-Key oder null>",
  "capability_secondary": ["<key>"],
  "signal_class": "<product_capability_move | positioning_move | ...>",
  "evidence_strength": 1-5,
  "visibility_impact": "<low | medium | high>",
  "strategic_intent_guess": "<ein Satz>",
  "gameplay_tags": ["<tag>"],
  "assessment_summary": "<2-3 Sätze>",
  "implication_for_us": "<1-2 Sätze>",
  "watch_items": ["<konkretes Beobachtungsziel>"],
  "confidence": 0.0-1.0
}`}</pre>
  </ExpandablePanel>

  <ExpandablePanel title="Datenstruktur — SignalAssessment">
    <table className="w-full text-xs mt-2 border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Feld</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Beschreibung</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['capability_primary', 'Primär betroffene WFM-Capability'],
          ['capability_secondary', 'Weitere betroffene Capabilities (Liste)'],
          ['signal_class', 'Art des strategischen Moves'],
          ['evidence_strength', 'Beweisstärke 1 (schwach) – 5 (sehr stark)'],
          ['visibility_impact', 'Marktsichtbarkeit: low / medium / high'],
          ['strategic_intent_guess', 'Vermutete strategische Absicht (1 Satz)'],
          ['gameplay_tags', 'Kategorisierungs-Tags (Liste)'],
          ['assessment_summary', '2–3 Sätze was dieses Signal bedeutet'],
          ['implication_for_us', '1–2 Sätze was das für unser Produkt bedeutet'],
          ['watch_items', 'Konkrete Beobachtungspunkte (Liste)'],
          ['movement_score', 'Deterministisch berechneter Score 0–100'],
          ['movement_strength', 'weak / relevant / strong / market_shaping'],
        ].map(([field, desc]) => (
          <tr key={field} className="border-b border-white/5">
            <td className="py-1.5 pr-4 font-mono text-blue-300">{field}</td>
            <td className="py-1.5">{desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>
</PipelineSection>

{/* ── SEKTION 4: Capability-Mapping & Movement Score ── */}
<PipelineSection
  id="capabilities"
  title="Capability-Mapping & Movement Score"
  type="rule"
  explanation={
    <>
      <p>
        Aus den Assessment-Daten berechnet das System deterministisch einen{' '}
        <strong className="text-slate-200">Movement Score (0–100)</strong> pro Signal. Die
        Formel gewichtet vier Faktoren: Relevanz des Signals, Confidence des Analysten,
        Beweisstärke und Marktsichtbarkeit.
      </p>
      <div className="mt-3 bg-slate-800/40 rounded-lg p-3 font-mono text-[12px] text-slate-300">
        Score = (Relevanz × 35) + (Confidence × 20) + (Evidence × 6) + Visibility-Bonus
        <br />
        <span className="text-slate-500">
          Visibility-Bonus: low=0, medium=8, high=15 | Thought-Leadership-Abzug: −10
        </span>
      </div>
      <div className="mt-3 flex gap-3">
        {[
          { range: '0–29', label: 'weak', color: 'text-slate-400' },
          { range: '30–59', label: 'relevant', color: 'text-blue-400' },
          { range: '60–79', label: 'strong', color: 'text-emerald-400' },
          { range: '80–100', label: 'market_shaping', color: 'text-orange-400' },
        ].map(({ range, label, color }) => (
          <div key={label} className="flex flex-col items-center px-3 py-2 rounded-lg bg-slate-800/40 text-center">
            <span className="text-[10px] text-slate-500">{range}</span>
            <span className={`text-[12px] font-semibold ${color}`}>{label}</span>
          </div>
        ))}
      </div>
      <p className="mt-3">
        Das{' '}
        <strong className="text-slate-200">Wardley Evolution-Band</strong> einer Capability
        zeigt wo sie im Evolutionszyklus steht: <code className="text-blue-300">genesis</code>{' '}
        (neu, experimentell) → <code className="text-blue-300">product</code> → commodity.
        Mehrere starke Signale zu einer Capability können anzeigen, dass ein Wettbewerber
        diese aktiv Richtung nächster Evolutionsstufe treibt.
      </p>
    </>
  }
  example={
    <p>
      Movement Score: (0.88×35) + (0.92×20) + (4×6) + 15 ={' '}
      <strong className="text-amber-300">88</strong> →{' '}
      <strong className="text-orange-400">market_shaping</strong>. Das Signal bewegt die
      Nadel bei{' '}
      <code className="text-purple-300 bg-purple-900/30 px-1 rounded">ai_copilot</code>{' '}
      (strategisches Gewicht 9/10, Wardley-Band:{' '}
      <code className="text-blue-300">genesis</code> — Workday schiebt diese Capability
      aktiv Richtung <code className="text-blue-300">product</code>).
    </p>
  }
>
  <ExpandablePanel title="Die 16 WFM-Capabilities anzeigen">
    <table className="w-full text-xs mt-2 border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Capability</th>
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Gewicht</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Wardley-Band</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['Shift Scheduling', '10/10', 'product'],
          ['Demand Forecasting', '9/10', 'product'],
          ['AI Copilot', '9/10', 'genesis'],
          ['Optimization Engine', '9/10', 'product'],
          ['Compliance & Labor Rules', '8/10', 'product'],
          ['Intraday Management', '8/10', 'product'],
          ['Analytics & Insights', '8/10', 'product'],
          ['Platform & Ecosystem', '8/10', 'product'],
          ['Time & Attendance', '7/10', 'product'],
          ['Manager Experience', '7/10', 'product'],
          ['Workflow Automation', '7/10', 'product'],
          ['Integration Hub', '7/10', 'product'],
          ['Vertical Solutions', '7/10', 'product'],
          ['Employee Self-Service', '6/10', 'product'],
          ['Mobile Experience', '6/10', 'product'],
          ['Data Foundation', '6/10', 'product'],
        ].map(([cap, weight, band]) => (
          <tr key={cap} className="border-b border-white/5">
            <td className="py-1.5 pr-4 text-slate-300">{cap}</td>
            <td className="py-1.5 pr-4">{weight}</td>
            <td className="py-1.5">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${band === 'genesis' ? 'bg-orange-900/40 text-orange-300' : 'bg-slate-700/40 text-slate-400'}`}>
                {band}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>
</PipelineSection>

{/* ── SEKTION 5: Benchmark ── */}
<PipelineSection
  id="benchmark"
  title="Benchmark-Berechnung"
  type="rule"
  explanation={
    <p>
      Über einen gewählten Zeitraum (30 / 90 / 180 Tage) aggregiert das System alle
      Assessments aller Wettbewerber pro Capability. Das Ergebnis ist die{' '}
      <strong className="text-slate-200">Capability Strength Matrix</strong>: eine
      Übersicht, wer in welchem Bereich wie aktiv ist und welche Bewegungsstärke er dabei
      zeigt. Diese Matrix ist der schnellste Weg um zu verstehen, wo der Markt sich gerade
      bewegt — und wo wir besonders aufmerksam sein sollten.
    </p>
  }
  example={
    <p>
      Nach 30 Tagen hat Workday 5 Signals zu{' '}
      <code className="text-purple-300 bg-purple-900/30 px-1 rounded">ai_copilot</code>{' '}
      produziert, davon 3 mit{' '}
      <strong className="text-orange-400">market_shaping</strong>. In der Capability
      Strength Matrix erscheint Workday als stärkster Akteur in dieser Capability im
      aktuellen Zeitraum.
    </p>
  }
/>

{/* ── SEKTION 6: Competitor Summary ── */}
<PipelineSection
  id="summary"
  title="Competitor Summary"
  type="ai"
  explanation={
    <p>
      Auf Knopfdruck (oder automatisch) fasst ein KI-Analyst alle Assessments eines
      Wettbewerbers für einen Zeitraum zusammen. Das Ergebnis ist ein vollständiges
      strategisches Profil: Wie ist die Gesamtausrichtung gerade? In welchen Capabilities
      ist der Wettbewerber am aktivsten? Was sind die konkreten Risiken und Chancen für
      uns — und was sollten wir in den nächsten Wochen besonders beobachten?
    </p>
  }
  example={
    <p>
      Nach 30 Tagen mit mehreren Workday-Signalen generiert das System eine Competitor
      Summary: Strategic Posture:{' '}
      <code className="text-purple-300 bg-purple-900/30 px-1 rounded">
        aggressive_ai_expansion
      </code>
      . Top Risk: „Workday positioniert KI als Standard-Feature — Gefahr der
      Commoditisierung unseres AI-Differenzierers." Watchpoint: „Nächste Workday Rising
      Keynote auf weitere AI-Announcements überwachen."
    </p>
  }
>
  <ExpandablePanel title="Prompt anzeigen" variant="prompt">
    <p className="mb-3 text-slate-300">
      Der Analyst bekommt alle Assessments des Wettbewerbers im Zeitraum als strukturierte
      Liste sowie unser Kontext-Profil. Er soll ein zusammenfassendes strategisches Bild
      zeichnen: Gesamtausrichtung, stärkste Capabilities, Risiken und Chancen für uns.
    </p>
    <pre className="bg-slate-900/60 rounded p-3 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">{`Synthetisiere diese Signal-Assessments für Wettbewerber "[Name]" über [Zeitraum].

Assessments ([N] Signale):
[Strukturierte Liste aller Assessments mit capability_primary, signal_class,
evidence_strength, assessment_summary, implication_for_us]

Unser interner Kontext:
- Kernkompetenzen: [core_capabilities]
- Strategische Prioritäten: [strategic_priorities]

Antworte mit genau diesem JSON-Objekt:
{
  "strategic_posture": "<2-4 Wort Label, z.B. aggressive_expansion>",
  "positioning_summary": "<2-3 Sätze zur strategischen Ausrichtung>",
  "top_capabilities": ["<capability_key>"],
  "capability_assessment": [
    {"key": "...", "label": "...", "activity_level": "low|medium|high", "notes": "..."}
  ],
  "top_risks": ["<Risiko für uns, je ein Satz>"],
  "top_opportunities": ["<Chance für uns, je ein Satz>"],
  "watchpoints": ["<konkretes Beobachtungsziel>"]
}`}</pre>
  </ExpandablePanel>

  <ExpandablePanel title="Datenstruktur — CompetitorSummary">
    <table className="w-full text-xs mt-2 border-collapse">
      <thead>
        <tr className="border-b border-white/10">
          <th className="text-left py-1.5 pr-4 text-slate-300 font-semibold">Feld</th>
          <th className="text-left py-1.5 text-slate-300 font-semibold">Beschreibung</th>
        </tr>
      </thead>
      <tbody className="text-slate-400">
        {[
          ['company', 'Bewerteter Wettbewerber'],
          ['period_type', 'Zeitraum: 7d / 30d / 90d'],
          ['strategic_posture', 'KI-generiertes Label (z.B. aggressive_expansion)'],
          ['positioning_summary', '2–3 Sätze zur strategischen Ausrichtung'],
          ['top_capabilities', 'Aktivste Capabilities im Zeitraum'],
          ['capability_assessment', 'Aktivitätslevel pro Capability'],
          ['top_risks', 'Risiken für uns (Liste)'],
          ['top_opportunities', 'Chancen für uns (Liste)'],
          ['watchpoints', 'Konkrete Beobachtungspunkte (Liste)'],
          ['avg_movement_score', 'Durchschnittlicher Movement Score im Zeitraum'],
          ['signal_count', 'Anzahl Signals im Zeitraum'],
        ].map(([field, desc]) => (
          <tr key={field} className="border-b border-white/5">
            <td className="py-1.5 pr-4 font-mono text-blue-300">{field}</td>
            <td className="py-1.5">{desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </ExpandablePanel>
</PipelineSection>

{/* ── SEKTION 7: Briefings ── */}
<PipelineSection
  id="briefing"
  title="Briefings"
  type="ai"
  explanation={
    <>
      <p>
        Das System generiert zwei verschiedene KI-Briefings — für unterschiedliche
        Zielgruppen und Datenbasis:
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3">
        <div className="rounded-lg border border-slate-700/40 bg-slate-800/30 p-3">
          <p className="text-[12px] font-semibold text-slate-200 mb-1">
            Weekly Digest (Dashboard)
          </p>
          <p className="text-[12px] text-slate-400">
            Aus allen neuen Signals der letzten 7 Tage — unabhängig vom Movement Score.
            Kompakter Überblick welche Unternehmen aktiv waren, plus drei priorisierte
            Handlungsempfehlungen als Tabelle mit direkten Links zu den Originalquellen.
          </p>
        </div>
        <div className="rounded-lg border border-slate-700/40 bg-slate-800/30 p-3">
          <p className="text-[12px] font-semibold text-slate-200 mb-1">
            Intelligence Briefing (Overview)
          </p>
          <p className="text-[12px] text-slate-400">
            Nur aus Signals mit Movement Strength{' '}
            <code className="text-emerald-300">strong</code> oder{' '}
            <code className="text-orange-300">market_shaping</code>. Selektiver und
            strategischer — ein Executive Summary der wichtigsten Marktbewegungen plus
            priorisierte Handlungsempfehlungen für Produkt und GTM.
          </p>
        </div>
      </div>
    </>
  }
  example={
    <p>
      Das Workday-Signal mit Movement Score 88 (
      <strong className="text-orange-400">market_shaping</strong>) erscheint im
      Intelligence Briefing: „Workday beschleunigt AI-Investitionen im
      Scheduling-Kernprodukt — direkter Wettbewerbsdruck auf unsere AI-Roadmap."
      Empfehlung #1: „AI Copilot Modul priorisieren — Workday schiebt diesen Bereich
      aktiv Richtung Marktstandard."
    </p>
  }
>
  <ExpandablePanel title="Prompt anzeigen — Weekly Digest" variant="prompt">
    <p className="mb-3 text-slate-300">
      Der Analyst erhält eine Zusammenfassung der Signalaktivität der letzten 7 Tage:
      aktivste Unternehmen, Top-Signals nach Relevanz, Signaltyp-Verteilung. Er soll eine
      kurze Zusammenfassung, eine Empfehlungstabelle mit Quell-Links und einen Ausblick
      erstellen.
    </p>
    <pre className="bg-slate-900/60 rounded p-3 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">{`Du bist ein Market Intelligence Analyst.
Erstelle eine prägnante, handlungsorientierte Zusammenfassung der wichtigsten
Marktentwicklungen.

Analysezeitraum: letzte 7 Tage
Neue Signale gesamt: [N]
Davon hohe Relevanz (≥0.7): [N]

Aktivste Unternehmen:
- [Unternehmen]: [N] Signale
...

Top-Signale nach Relevanz:
- [[Unternehmen]] [Titel] (Relevanz: X.XX, Typ: ...)
  Quelle: [URL]
  → [why_it_matters]

Erstelle auf Deutsch:
1. Kurze Zusammenfassung (2-3 Sätze) der wichtigsten Entwicklungen
2. Top 3 Handlungsempfehlungen als Markdown-Tabelle:
   | Priorität | Signal | Grund |
3. Ausblick: Was könnte sich als nächstes entwickeln?`}</pre>
  </ExpandablePanel>

  <ExpandablePanel title="Prompt anzeigen — Intelligence Briefing" variant="prompt">
    <p className="mb-3 text-slate-300">
      Der Analyst erhält ausschließlich Signals mit hohem Movement Score. Er erstellt ein
      strategisches Executive-Summary und bis zu 3 priorisierte Handlungsempfehlungen für
      Produkt und GTM-Teams.
    </p>
    <pre className="bg-slate-900/60 rounded p-3 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">{`Du bist ein strategischer Market Intelligence Analyst für ein WFM-Unternehmen.
Erstelle ein Executive Intelligence Briefing aus den wichtigsten Marktbewegungen.

Zeitraum: letzte 7 Tage
Analysierte Signale: [N] Assessments
Starke / market-shaping Signale: [N]

Top Moves (nach Movement Score):
- [Unternehmen] | [Titel] | Score: [X] | [market_shaping/strong]
  Capability: [capability_primary]
  [assessment_summary]
  Für uns: [implication_for_us]
...

Aktivste Capability-Bereiche: [Top 5]

Unser Kontext:
- Kernkompetenzen: [core_capabilities]
- Strategische Prioritäten: [strategic_priorities]

Erstelle:
1. Strategischer Überblick (2-3 Sätze): Was bewegt sich gerade im Markt?
2. Top 3 Handlungsempfehlungen für Produkt / GTM (je 1-2 Sätze, konkret)`}</pre>
  </ExpandablePanel>
</PipelineSection>

{/* ── SEKTION 8: Bewertungskriterien ── */}
<section className="scroll-mt-24 py-10 border-t border-white/5">
  <h2 className="text-lg font-semibold text-slate-100 mb-6">Bewertungskriterien</h2>
  <div className="grid grid-cols-1 gap-4">
    {[
      {
        name: 'Relevanz-Score',
        scale: '0.0 – 1.0',
        who: '🤖 KI',
        whoColor: 'bg-purple-900/40 text-purple-300',
        desc: 'Wie relevant ist dieses Signal für unsere Strategie und Märkte?',
        bands: [
          { range: '0.0 – 0.3', label: 'Kaum relevant', color: 'text-slate-500' },
          { range: '0.4 – 0.6', label: 'Peripher (beobachten)', color: 'text-blue-400' },
          { range: '0.7 – 0.85', label: 'Relevant (aktiv verfolgen)', color: 'text-emerald-400' },
          { range: '0.86 – 1.0', label: 'Hochrelevant (sofort handeln)', color: 'text-orange-400' },
        ],
      },
      {
        name: 'Confidence-Score',
        scale: '0.0 – 1.0',
        who: '🤖 KI',
        whoColor: 'bg-purple-900/40 text-purple-300',
        desc: 'Wie sicher ist der Analyst sich bei seiner Einschätzung?',
        bands: [
          { range: '0.0 – 0.5', label: 'Unsicher — kritisch prüfen', color: 'text-slate-500' },
          { range: '0.5 – 0.75', label: 'Mittel', color: 'text-blue-400' },
          { range: '0.75 – 1.0', label: 'Sicher', color: 'text-emerald-400' },
        ],
      },
      {
        name: 'Evidence Strength',
        scale: '1 – 5',
        who: '🤖 KI',
        whoColor: 'bg-purple-900/40 text-purple-300',
        desc: 'Wie belastbar ist der Beweis im Assessment?',
        bands: [
          { range: '1', label: 'Sehr schwach / spekulativ', color: 'text-slate-500' },
          { range: '2–3', label: 'Mittel', color: 'text-blue-400' },
          { range: '4–5', label: 'Stark / sehr belastbar', color: 'text-emerald-400' },
        ],
      },
      {
        name: 'Movement Score',
        scale: '0 – 100',
        who: '🔢 Formel',
        whoColor: 'bg-blue-900/40 text-blue-300',
        desc: 'Wie stark bewegt sich ein Wettbewerber in einer Capability?',
        bands: [
          { range: '0–29', label: 'weak', color: 'text-slate-500' },
          { range: '30–59', label: 'relevant', color: 'text-blue-400' },
          { range: '60–79', label: 'strong', color: 'text-emerald-400' },
          { range: '80–100', label: 'market_shaping', color: 'text-orange-400' },
        ],
      },
    ].map((score) => (
      <div key={score.name} className="rounded-lg border border-white/5 bg-slate-800/20 p-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[14px] font-semibold text-slate-200">{score.name}</span>
          <span className="text-[10px] text-slate-500">{score.scale}</span>
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${score.whoColor}`}>
            {score.who}
          </span>
        </div>
        <p className="text-[13px] text-slate-400 mb-3">{score.desc}</p>
        <div className="flex gap-2 flex-wrap">
          {score.bands.map((b) => (
            <div key={b.range} className="text-[11px]">
              <span className="text-slate-600">{b.range}: </span>
              <span className={b.color}>{b.label}</span>
            </div>
          ))}
        </div>
      </div>
    ))}
  </div>
</section>
      </div>
    </div>
  );
}
