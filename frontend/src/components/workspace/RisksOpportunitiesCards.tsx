import type { CompetitorSummary } from '../../types/intelligence';

interface Props {
  summary: CompetitorSummary | null;
}

export default function RisksOpportunitiesCards({ summary }: Props) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-3 gap-4 mt-4">
      <div className="bg-red-50 border border-red-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-red-700 mb-2">Top Risks</h4>
        {summary.top_risks.length === 0 ? (
          <p className="text-slate-500 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.top_risks.slice(0, 4).map((r, i) => (
              <li key={i} className="text-[12px] text-slate-700 flex gap-2">
                <span className="text-red-500 flex-shrink-0 mt-0.5">▸</span>
                {r}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-green-50 border border-green-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-green-700 mb-2">Opportunities</h4>
        {summary.top_opportunities.length === 0 ? (
          <p className="text-slate-500 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.top_opportunities.slice(0, 4).map((o, i) => (
              <li key={i} className="text-[12px] text-slate-700 flex gap-2">
                <span className="text-green-500 flex-shrink-0 mt-0.5">▸</span>
                {o}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-amber-700 mb-2">Watchpoints</h4>
        {summary.watchpoints.length === 0 ? (
          <p className="text-slate-500 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.watchpoints.slice(0, 4).map((w, i) => (
              <li key={i} className="text-[12px] text-slate-700 flex gap-2">
                <span className="text-amber-500 flex-shrink-0 mt-0.5">▸</span>
                {w}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
