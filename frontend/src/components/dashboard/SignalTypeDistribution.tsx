import type { SignalTypeCount } from '../../types';
import { labelMap } from '../SignalTypeIcon';

const TYPE_COLORS: Record<string, string> = {
  ai_announcement: '#7c3aed',
  product_update: '#10b981',
  partnership: '#c2410c',
  positioning_change: '#86198f',
  target_market_change: '#be123c',
  event_or_thought_leadership: '#0f766e',
  hiring_signal: '#1d4ed8',
  other: '#52525b',
};

interface SignalTypeDistributionProps {
  byType: SignalTypeCount[];
}

export default function SignalTypeDistribution({ byType }: SignalTypeDistributionProps) {
  const maxCount = Math.max(...byType.map((t) => t.count), 1);

  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Nach Typ</p>
      <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-2">
        {byType.map((item) => {
          const color = TYPE_COLORS[item.signal_type] ?? '#52525b';
          const label = labelMap[item.signal_type as keyof typeof labelMap] ?? item.signal_type;
          const pct = (item.count / maxCount) * 100;
          return (
            <div key={item.signal_type}>
              <span className="text-[10px] font-medium" style={{ color }}>{label} {Math.round((item.count / (byType.reduce((s, t) => s + t.count, 0) || 1)) * 100)}%</span>
              <div className="bg-slate-100 rounded h-[5px] mt-0.5">
                <div className="rounded h-[5px]" style={{ width: `${pct}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}