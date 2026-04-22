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
    { label: 'Signals (30d)', value: totalSignals },
    { label: 'Active Competitors', value: activeCompetitors },
    { label: 'Avg Movement Score', value: avgScore },
    { label: 'Market Shaping', value: marketShapingCount },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {kpis.map((k) => (
        <div
          key={k.label}
          className="rounded-xl px-4 py-3"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
        >
          <div className="text-[11px] text-slate-500 uppercase tracking-wider mb-1">{k.label}</div>
          <div className="text-2xl font-semibold text-slate-100 tabular-nums">{k.value}</div>
        </div>
      ))}
    </div>
  );
}
