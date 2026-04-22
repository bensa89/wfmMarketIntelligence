import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { CompetitorMover } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';

interface Props {
  movers7d: CompetitorMover[];
  movers30d: CompetitorMover[];
}

export default function TopMoversList({ movers7d, movers30d }: Props) {
  const [period, setPeriod] = useState<'7d' | '30d'>('7d');
  const movers = period === '7d' ? movers7d : movers30d;

  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[13px] font-semibold text-slate-200">Top Movers</h3>
        <div className="flex gap-1">
          {(['7d', '30d'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                period === p
                  ? 'text-blue-400'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
              style={period === p ? { background: 'rgba(59,130,246,0.15)' } : undefined}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {movers.length === 0 ? (
        <p className="text-slate-600 text-[12px]">No data yet</p>
      ) : (
        <ul className="space-y-2">
          {movers.map((mover, i) => (
            <li key={mover.company_id} className="flex items-center gap-3">
              <span className="text-[11px] text-slate-600 w-4 tabular-nums">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <Link
                  to={`/competitors/${mover.company_slug}`}
                  className="text-[13px] text-slate-200 hover:text-blue-400 font-medium truncate block transition-colors"
                >
                  {mover.company_name}
                </Link>
                {mover.top_capability && (
                  <span className="text-[11px] text-slate-500">{getCapabilityLabel(mover.top_capability)}</span>
                )}
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-[13px] font-semibold text-slate-200 tabular-nums">
                  {mover.avg_movement_score}
                </div>
                <div className="text-[10px] text-slate-600">{mover.signal_count} signals</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
