import type { OverviewResponse } from '../../types/intelligence';
import KPICard from './KPICard';

interface Props {
  data: OverviewResponse;
}

export default function OverviewKPIBar({ data }: Props) {
  const totalSignals = data.top_movers_30d.reduce((sum, m) => sum + m.signal_count, 0);
  const avgScore = data.top_movers_30d.length > 0
    ? Math.round(data.top_movers_30d.reduce((sum, m) => sum + m.avg_movement_score, 0) / data.top_movers_30d.length)
    : 0;
  const importantSignalCount = data.recent_market_shaping_30d.length;

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <KPICard label="Signals (30d)" value={totalSignals} accent="bg-blue-500" />
      <KPICard label="Avg Movement Score" value={avgScore} accent="bg-purple-500" />
      <KPICard label="Wichtige neue Signale" value={importantSignalCount} accent="bg-orange-500" />
    </div>
  );
}
