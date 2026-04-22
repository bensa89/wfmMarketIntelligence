import type { CompetitorSummary } from '../../types/intelligence';

interface Props {
  summary: CompetitorSummary | null;
}

export default function RisksOpportunitiesCards({ summary }: Props) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-3 gap-4 mt-4">
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-red-400 mb-2">Top Risks</h4>
        {summary.top_risks.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.top_risks.slice(0, 4).map((r, i) => (
              <li key={i} className="text-[12px] text-slate-300 flex gap-2">
                <span className="text-red-500 flex-shrink-0 mt-0.5">▸</span>
                {r}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-green-400 mb-2">Opportunities</h4>
        {summary.top_opportunities.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.top_opportunities.slice(0, 4).map((o, i) => (
              <li key={i} className="text-[12px] text-slate-300 flex gap-2">
                <span className="text-green-500 flex-shrink-0 mt-0.5">▸</span>
                {o}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <h4 className="text-[12px] font-semibold text-amber-400 mb-2">Watchpoints</h4>
        {summary.watchpoints.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {summary.watchpoints.slice(0, 4).map((w, i) => (
              <li key={i} className="text-[12px] text-slate-300 flex gap-2">
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
