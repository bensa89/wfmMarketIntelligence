import { X } from 'lucide-react';

interface TopMoversInfoDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function TopMoversInfoDrawer({ open, onClose }: TopMoversInfoDrawerProps) {
  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-800">Top Movers — Erklärung</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-7 text-sm">

          <div>
            <h3 className="font-semibold text-slate-800 mb-1.5">Was zeigt die Liste?</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Die <strong>10 Wettbewerber mit dem höchsten durchschnittlichen Movement Score</strong> aus allen Signal-Assessments, deren zugrunde liegendes Signal im gewählten Zeitfenster erfasst wurde. Es ist ein Ranking nach Bewegungsintensität, nicht nach reiner Signal-Anzahl.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-slate-800 mb-2">7d / 30d — Zeitfenster</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Der Umschalter wählt den Betrachtungszeitraum: Es fließen nur Assessments von Signalen ein, die in den letzten 7 bzw. 30 Tagen erfasst wurden. Der Score selbst ist innerhalb dieses Fensters ungewichtet — ein Signal von gestern zählt genauso wie eines vom Fenster-Anfang.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-slate-800 mb-2">Angezeigte Werte</h3>
            <div className="space-y-2 text-xs">
              <div className="flex items-start gap-2">
                <span className="shrink-0 font-medium text-slate-800 w-32">Score (groß, rechts)</span>
                <span className="text-slate-500">Durchschnittlicher Movement Score (0–100) aller Assessments des Wettbewerbers im Zeitfenster.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="shrink-0 font-medium text-slate-800 w-32">"N signals"</span>
                <span className="text-slate-500">Anzahl der Assessments, aus denen der Score gemittelt wurde — höher heißt belastbarer.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="shrink-0 font-medium text-slate-800 w-32">Capability-Label</span>
                <span className="text-slate-500">Die Capability, die im Zeitfenster am häufigsten als primäre Capability dieses Wettbewerbers erkannt wurde — nicht zwingend die mit dem höchsten Score.</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-slate-800 mb-1.5">Wann fehlt ein Wettbewerber?</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Ein Wettbewerber erscheint nur, wenn im Zeitfenster mindestens ein Signal mit Assessment vorliegt. Bei wenig Aktivität kann die Liste daher kürzer als 10 Einträge sein.
            </p>
          </div>

        </div>
      </div>
    </>
  );
}
