import type { CompetitorSummary, RiskItem } from '../../types/intelligence';

interface Props {
  summary: CompetitorSummary | null;
  scorecardWatchpoints?: string[];
  onSelectSignal?: (signalId: string) => void;
}

function normalize(r: RiskItem | string): RiskItem {
  return typeof r === 'string' ? { text: r, signal_ids: [] } : r;
}

interface CitedListProps {
  items: (RiskItem | string)[];
  bullet: string;
  hoverClass: string;
  newBadgeClass: string;
  max?: number;
  onSelectSignal?: (signalId: string) => void;
}

function CitedItemList({ items, bullet, hoverClass, newBadgeClass, max = 4, onSelectSignal }: CitedListProps) {
  const normalized = items.slice(0, max).map(normalize);
  if (normalized.length === 0) return <p className="text-slate-500 text-[11px]">None identified</p>;
  return (
    <ul className="space-y-2">
      {normalized.map((item, i) => {
        const firstSignalId = item.signal_ids?.[0];
        const clickable = !!firstSignalId && !!onSelectSignal;
        return (
          <li
            key={i}
            onClick={clickable ? () => onSelectSignal!(firstSignalId) : undefined}
            className={`flex gap-2 p-1 -mx-1 rounded ${clickable ? `cursor-pointer ${hoverClass} group` : ''}`}
          >
            <span className={`${bullet} flex-shrink-0 mt-0.5`}>▸</span>
            <span className="text-[12px] text-slate-700 leading-snug">
              {item.text}
              {item.signal_ids && item.signal_ids.length > 1 && (
                <span className="ml-1 text-[10px] text-slate-400">+{item.signal_ids.length - 1}</span>
              )}
              {item.is_new === true && (
                <span className={`ml-1.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wide ${newBadgeClass}`}>
                  NEW
                </span>
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default function RisksOpportunitiesCards({ summary, scorecardWatchpoints, onSelectSignal }: Props) {
  const risks = summary?.top_risks ?? [];
  const opportunities = summary?.top_opportunities ?? [];

  // Merge scorecard watchpoints (plain strings) with summary watchpoints (may be cited),
  // deduplicating by text.
  const summaryWatchpoints = summary?.watchpoints ?? [];
  const scorecardTexts = new Set(
    (scorecardWatchpoints ?? []).map((w) => w.toLowerCase())
  );
  const extraScorecard: RiskItem[] = (scorecardWatchpoints ?? [])
    .filter((w) => !summaryWatchpoints.some((s) => normalize(s).text.toLowerCase() === w.toLowerCase()))
    .map((w) => ({ text: w, signal_ids: [] }));
  const allWatchpoints: (RiskItem | string)[] = [...summaryWatchpoints, ...extraScorecard];
  void scorecardTexts; // used only for dedup above

  return (
    <div className="grid grid-cols-3 gap-4 mt-4">
      <div className="bg-red-50 border border-red-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-red-700 mb-2">Top Risks</h4>
        <CitedItemList items={risks} bullet="text-red-500" hoverClass="hover:bg-red-100" newBadgeClass="bg-red-100 text-red-700" onSelectSignal={onSelectSignal} />
      </div>

      <div className="bg-green-50 border border-green-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-green-700 mb-2">Opportunities</h4>
        <CitedItemList items={opportunities} bullet="text-green-500" hoverClass="hover:bg-green-100" newBadgeClass="bg-green-100 text-green-700" onSelectSignal={onSelectSignal} />
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-amber-700 mb-2">Watchpoints</h4>
        <CitedItemList items={allWatchpoints} bullet="text-amber-500" hoverClass="hover:bg-amber-100" newBadgeClass="bg-amber-100 text-amber-700" max={5} onSelectSignal={onSelectSignal} />
      </div>
    </div>
  );
}
