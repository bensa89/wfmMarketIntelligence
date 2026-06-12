import { X } from 'lucide-react';

interface MatrixInfoDrawerProps {
  open: boolean;
  onClose: () => void;
}

const TIERS = [
  { label: 'Leader', range: '≥75', bg: 'bg-emerald-600', text: 'text-white', desc: 'Starke, gut belegte Capability mit hoher Aktivität und Marktpräsenz.' },
  { label: 'Strong', range: '≥55', bg: 'bg-blue-600', text: 'text-white', desc: 'Solide Capability mit guter Evidenzlage.' },
  { label: 'Emerging', range: '≥30', bg: 'bg-amber-400', text: 'text-slate-900', desc: 'Erste Signale vorhanden, aber noch keine dominante Position.' },
  { label: 'Weakly Evidenced', range: '<30', bg: 'bg-slate-100', text: 'text-slate-400', desc: 'Kaum Belege — keine verlässliche Aussage möglich.' },
];

const SUB_SCORES = [
  { label: 'Capability Depth', weight: '35%', desc: 'Qualität der Signale: Produkt-Moves, Evidenzstärke, Movement Strength.' },
  { label: 'Execution Momentum', weight: '25%', desc: 'Anzahl und Intensität der Aktivitäten: Signal-Dichte, Movement Score, starke Moves.' },
  { label: 'Market Proof', weight: '20%', desc: 'Externe Belege: Ecosystem-Moves, hoher Visibility-Impact, Kunden-Referenzen.' },
  { label: 'Strategic Focus', weight: '10%', desc: 'Anteil aller Assessments auf diese Capability + Positionierungs-Moves.' },
  { label: 'Evidence Coverage', weight: '10%', desc: 'Quellen-Diversität, Confidence und Aktualität der Assessments.' },
];

export function MatrixInfoDrawer({ open, onClose }: MatrixInfoDrawerProps) {
  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-800">Capability Strength Matrix — Legende</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-7 text-sm">

          {/* What is it */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-1.5">Was zeigt die Matrix?</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Jede Zelle zeigt den <strong>Relative Capability Score (0–100)</strong> eines Wettbewerbers für eine spezifische Fähigkeit. Der Score kombiniert Qualität, Aktivität und Marktbelege aller historischen Assessments — gewichtet nach Alter (neuere Signale zählen mehr).
            </p>
          </div>

          {/* Tier colors */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-2">Zellenfarbe = Tier</h3>
            <div className="space-y-2">
              {TIERS.map(({ label, range, bg, text, desc }) => (
                <div key={label} className="flex items-start gap-3">
                  <div className={`shrink-0 w-24 rounded px-2 py-1 text-xs font-semibold text-center ${bg} ${text}`}>
                    {label}
                  </div>
                  <div className="text-xs text-slate-600 pt-0.5">
                    <span className="font-medium text-slate-800">{range} — </span>{desc}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-2">Niedrige Confidence (opacity reduziert) senkt das Tier automatisch um eine Stufe.</p>
          </div>

          {/* Delta indicators */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-2">Δ seit letztem Recompute (▲ / ▼)</h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-2">
              Das kleine Symbol oben rechts zeigt die Differenz zwischen dem <strong>aktuellen Score</strong> und dem <strong>Score des vorherigen Recompute-Laufs</strong> — kein fixer Zeitvergleich, sondern der Unterschied zwischen zwei aufeinanderfolgenden Berechnungen.
            </p>
            <div className="space-y-1.5 text-xs mb-2">
              <div className="flex items-center gap-2">
                <span className="text-emerald-400 font-bold text-base">▲</span>
                <span className="text-slate-600">Score gestiegen seit letztem Recompute</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-red-400 font-bold text-base">▼</span>
                <span className="text-slate-600">Score gefallen seit letztem Recompute</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-300 font-bold text-base">—</span>
                <span className="text-slate-600">Kein Delta (erster Recompute oder keine Änderung)</span>
              </div>
            </div>
            <p className="text-[11px] text-slate-400">Hover über die Zelle zeigt den genauen Delta-Wert. Ein Delta von 0 trotz neuer Signale entsteht, wenn Decay und neue Daten sich gegenseitig ausgleichen.</p>
          </div>

          {/* Score formula */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-2">Score-Formel</h3>
            <p className="text-xs text-slate-600 mb-2">Gewichteter Durchschnitt aus 5 Sub-Scores (je 0–5), skaliert auf 0–100:</p>
            <div className="space-y-1.5">
              {SUB_SCORES.map(({ label, weight, desc }) => (
                <div key={label} className="flex items-start gap-2 text-xs">
                  <span className="shrink-0 font-medium text-slate-800 w-40">{label}</span>
                  <span className="text-slate-400 shrink-0">{weight}</span>
                  <span className="text-slate-500">{desc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Decay / period selector */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-2">Period-Selector (Recency Focus)</h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-2">
              Anstatt eines harten Zeitfilters nutzt die Matrix <strong>exponentiellen Decay</strong>: Alle Assessments fließen ein, ältere erhalten aber ein kleineres Gewicht (<code className="bg-slate-100 px-1 rounded">e<sup>−λ·Alter</sup></code>).
            </p>
            <div className="space-y-1.5 text-xs">
              {[
                { label: '30d', desc: 'Starker Recency-Fokus — Halbwertszeit 30 Tage. Signale älter als ~3 Monate haben kaum Einfluss.' },
                { label: '90d', desc: 'Mittlerer Fokus — Halbwertszeit 90 Tage.' },
                { label: 'All', desc: 'Historical View — Halbwertszeit 180 Tage. Alle Assessments zählen, ältere mit leicht reduziertem Gewicht.' },
              ].map(({ label, desc }) => (
                <div key={label} className="flex items-start gap-2">
                  <span className="shrink-0 px-2 py-0.5 bg-slate-900 text-white rounded text-[10px] font-medium">{label}</span>
                  <span className="text-slate-600 pt-0.5">{desc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Confidence */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-1.5">Opacity = Confidence</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Zellen mit Confidence &lt; 0.5 werden transparent dargestellt. Niedrige Confidence entsteht bei wenigen Assessments, geringer Quellen-Diversität oder niedriger Durchschnitts-Confidence der zugrunde liegenden Signale.
            </p>
          </div>

        </div>
      </div>
    </>
  );
}
