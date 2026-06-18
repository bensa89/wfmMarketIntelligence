import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { SignalFeedItem } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';
import CompanyLogo from '../CompanyLogo';
import MovementBadge from '../signals/MovementBadge';

interface Props {
  signals7d: SignalFeedItem[];
  signals30d: SignalFeedItem[];
  signals90d: SignalFeedItem[];
  onSelect?: (item: SignalFeedItem) => void;
}

const VISIBLE_LIMIT = 7;

export default function MarketShapingFeed({ signals7d, signals30d, signals90d, onSelect }: Props) {
  const [period, setPeriod] = useState<'7d' | '30d' | '90d'>('30d');
  const [expanded, setExpanded] = useState(false);
  const signals = period === '7d' ? signals7d : period === '30d' ? signals30d : signals90d;
  const visibleSignals = expanded ? signals : signals.slice(0, VISIBLE_LIMIT);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />
          <h3 className="text-[13px] font-semibold text-slate-700">Wichtige neue Signale</h3>
        </div>
        <div className="flex gap-1">
          {(['7d', '30d', '90d'] as const).map((p) => (
            <button
              key={p}
              onClick={() => { setPeriod(p); setExpanded(false); }}
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

      {signals.length === 0 ? (
        <p className="text-slate-400 text-[12px]">No strong or market-shaping signals in this period</p>
      ) : (
        <ul className="space-y-3">
          {visibleSignals.map((item) => (
            <li key={item.id} className="flex gap-3">
              {item.company_name && (
                <CompanyLogo
                  name={item.company_name}
                  slug={item.company_slug ?? item.company_id}
                  logo_path={item.company_logo_path}
                  companyId={item.company_id}
                  size="sm"
                />
              )}
              <div className="flex-1 min-w-0">
                <button
                  onClick={() => onSelect?.(item)}
                  className="text-[12px] font-medium text-slate-800 leading-snug line-clamp-2 text-left hover:text-blue-700 transition-colors cursor-pointer"
                >
                  {item.title}
                </button>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <MovementBadge
                    strength={item.assessment?.movement_strength}
                    score={item.assessment?.movement_score}
                  />
                  {item.company_slug && (
                    <Link
                      to={`/competitors/${item.company_slug}`}
                      className="text-[11px] text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      {item.company_name}
                    </Link>
                  )}
                  {item.assessment?.capability_primary && (
                    <span className="text-[11px] text-slate-500">
                      · {getCapabilityLabel(item.assessment.capability_primary)}
                    </span>
                  )}
                  <span className="text-[11px] text-slate-500">
                    · {formatDistanceToNow(item.published_at || item.created_at)}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {signals.length > VISIBLE_LIMIT && (
        <button
          onClick={() => setExpanded((e) => !e)}
          className="mt-3 text-[11px] font-medium text-blue-600 hover:text-blue-700 transition-colors"
        >
          {expanded ? 'Weniger anzeigen' : `Alle ${signals.length} anzeigen`}
        </button>
      )}
    </div>
  );
}
