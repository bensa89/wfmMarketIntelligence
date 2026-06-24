import { useState } from 'react';
import { Link } from 'react-router-dom';
import { HelpCircle } from 'lucide-react';
import type { CompetitorMover } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';
import CompanyLogo from '../CompanyLogo';
import { TopMoversInfoDrawer } from './TopMoversInfoDrawer';

interface Props {
  movers7d: CompetitorMover[];
  movers30d: CompetitorMover[];
}

export default function TopMoversList({ movers7d, movers30d }: Props) {
  const [period, setPeriod] = useState<'7d' | '30d'>('7d');
  const [infoOpen, setInfoOpen] = useState(false);
  const movers = period === '7d' ? movers7d : movers30d;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <TopMoversInfoDrawer open={infoOpen} onClose={() => setInfoOpen(false)} />
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-1.5">
          <h3 className="text-[13px] font-semibold text-slate-700">Top Movers</h3>
          <button
            onClick={() => setInfoOpen(true)}
            className="p-0.5 rounded hover:bg-slate-100 transition-colors"
            title="Erklärung"
          >
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
          </button>
        </div>
        <div className="flex gap-1">
          {(['7d', '30d'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors border ${
                period === p
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'text-slate-500 hover:text-slate-700 border-transparent'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {movers.length === 0 ? (
        <p className="text-slate-400 text-[12px]">No data yet</p>
      ) : (
        <ul className="space-y-2">
          {movers.map((mover, i) => (
            <li key={mover.company_id} className="flex items-center gap-3">
              <span className="text-[11px] text-slate-400 w-4 tabular-nums">{i + 1}</span>
              <CompanyLogo
                name={mover.company_name}
                slug={mover.company_slug}
                logo_path={mover.logo_path}
                size="sm"
                companyId={mover.company_id}
              />
              <div className="flex-1 min-w-0 leading-tight">
                <Link
                  to={`/competitors/${mover.company_slug}`}
                  className="text-[13px] text-slate-900 hover:text-blue-600 font-medium truncate block transition-colors"
                >
                  {mover.company_name}
                </Link>
                {mover.top_capability && (
                  <span className="text-[11px] text-slate-500 block truncate">{getCapabilityLabel(mover.top_capability)}</span>
                )}
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-[13px] font-semibold text-slate-900 tabular-nums">
                  {mover.avg_movement_score}
                </div>
                <div className="text-[10px] text-slate-500">{mover.signal_count} signals</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
