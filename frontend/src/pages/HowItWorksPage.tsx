import { useEffect, useRef, useState } from 'react';
import { PipelineFlow, PipelineStep } from '../components/docs/PipelineFlow';

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

        {/* Sections will be added in subsequent tasks */}
        <div className="text-slate-500 text-sm py-10">Sektionen folgen…</div>
      </div>
    </div>
  );
}
