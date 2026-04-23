import type { OverviewResponse } from '../../types/intelligence';

interface Props {
  data: OverviewResponse;
}

export default function OverviewKPIBar({ data }: Props) {
  const totalSignals = data.top_movers_30d.reduce((sum, m) => sum + m.signal_count, 0);
  const avgScore = data.top_movers_30d.length > 0
    ? Math.round(data.top_movers_30d.reduce((sum, m) => sum + m.avg_movement_score, 0) / data.top_movers_30d.length)
    : 0;
  const activeCompetitors = data.top_movers_30d.length;
  const marketShapingCount = data.recent_market_shaping.length;

  const kpis = [
    { label: 'Signals (30d)', value: totalSignals, accent: 'bg-blue-500' },
    { label: 'Active Competitors', value: activeCompetitors, accent: 'bg-green-500' },
    { label: 'Avg Movement Score', value: avgScore, accent: 'bg-purple-500' },
    { label: 'Market Shaping', value: marketShapingCount, accent: 'bg-orange-500' },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {kpis.map((k) => (
        <div
          key={k.label}
          className="bg-white border border-slate-200 rounded-xl overflow-hidden"
        >
          <div className={`h-[3px] ${k.accent}`} />
          <div className="px-4 py-3">
            <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1">{k.label}</div>
            <div className="text-[28px] font-extrabold text-slate-900 leading-none tabular-nums">{k.value}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
