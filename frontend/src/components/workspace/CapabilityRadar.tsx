import type { CapabilityCount } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';

interface Props {
  distribution: CapabilityCount[];
}

export default function CapabilityRadar({ distribution }: Props) {
  if (distribution.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4">
        <p className="text-slate-400 text-[12px]">No capability data yet</p>
      </div>
    );
  }

  const maxCount = Math.max(...distribution.map((d) => d.count));

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <h3 className="text-[13px] font-semibold text-slate-700 mb-3">Capability Activity</h3>
      <div className="space-y-2">
        {distribution.slice(0, 8).map((d) => {
          const barPct = maxCount > 0 ? (d.count / maxCount) * 100 : 0;
          const scoreColor = d.avg_movement_score >= 80 ? '#f97316'
            : d.avg_movement_score >= 60 ? '#8b5cf6'
            : d.avg_movement_score >= 30 ? '#3b82f6'
            : '#64748b';
          return (
            <div key={d.capability_key} className="flex items-center gap-3">
              <div className="w-28 flex-shrink-0">
                <span className="text-[11px] text-slate-600 truncate block" title={getCapabilityLabel(d.capability_key)}>
                  {getCapabilityLabel(d.capability_key)}
                </span>
              </div>
              <div className="flex-1 h-2 rounded-full bg-slate-200 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${barPct}%`, background: scoreColor }}
                />
              </div>
              <span className="text-[11px] text-slate-500 w-8 text-right tabular-nums">{d.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
