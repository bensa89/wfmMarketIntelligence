import { X } from 'lucide-react';

interface CapabilityActivityInfoDrawerProps {
  open: boolean;
  onClose: () => void;
}

const COLOR_TIERS = [
  { label: 'Sehr hoch', range: '≥80', swatch: 'rgba(249,115,22,0.55)', desc: 'Starke, intensive Aktivität in dieser Capability in den letzten 30 Tagen.' },
  { label: 'Hoch', range: '≥60', swatch: 'rgba(139,92,246,0.45)', desc: 'Deutliche Aktivität mit überdurchschnittlichem Movement Score.' },
  { label: 'Mittel', range: '≥30', swatch: 'rgba(59,130,246,0.35)', desc: 'Moderate Aktivität, einzelne relevante Signale.' },
  { label: 'Gering', range: '<30', swatch: 'rgba(59,130,246,0.12)', desc: 'Schwache Aktivität, kaum nennenswerte Signale.' },
  { label: 'Keine Daten', range: '0', swatch: 'rgba(203,213,225,0.4)', desc: 'Keine Signale für diese Capability in den letzten 30 Tagen.' },
];

export function CapabilityActivityInfoDrawer({ open, onClose }: CapabilityActivityInfoDrawerProps) {
  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-800">Capability Activity (30d) — Erklärung</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-7 text-sm">

          <div>
            <h3 className="font-semibold text-slate-800 mb-1.5">Was zeigt das Panel?</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Jede Zeile ist ein Wettbewerber, jede Spalte eine der wichtigsten Capabilities. Die Zellenfarbe zeigt, wie aktiv ein Wettbewerber im gewählten Zeitfenster (7d / 30d) in dieser Capability war — gemessen am <strong>durchschnittlichen Movement Score</strong> der zugehörigen Assessments. Gezeigt werden die 8 Capabilities mit dem höchsten strategischen Gewicht.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-slate-800 mb-2">Zellenfarbe = Aktivitätsniveau</h3>
            <div className="space-y-2">
              {COLOR_TIERS.map(({ label, range, swatch, desc }) => (
                <div key={label} className="flex items-start gap-3">
                  <div
                    className="shrink-0 w-7 h-5 rounded mt-0.5"
                    style={{ background: swatch }}
                  />
                  <div className="text-xs text-slate-600">
                    <span className="font-medium text-slate-800">{label} ({range}) — </span>{desc}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-slate-800 mb-1.5">Tooltip bei Hover</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Beim Überfahren einer Zelle erscheint die Capability-Beschreibung, der Firmenname und der genaue Avg. Movement Score. Steht dort "Keine Signale in den letzten 30 Tagen", gab es für diese Kombination keine Assessments im Zeitfenster.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-slate-800 mb-1.5">7d / 30d — Zeitfenster</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Der Umschalter wählt den Betrachtungszeitraum: Es fließen nur Assessments von Signalen ein, die in den letzten 7 bzw. 30 Tagen erfasst wurden (kein gleitender Decay wie in der Capability Strength Matrix). Das Panel zeigt also reine, aktuelle Aktivität statt eines historisch gewichteten Scores — ein kürzeres Fenster macht einzelne neue Signale stärker sichtbar.
            </p>
          </div>

        </div>
      </div>
    </>
  );
}
