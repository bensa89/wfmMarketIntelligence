import { Link } from 'react-router-dom';
import type { SignalFeedItem } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  signals: SignalFeedItem[];
}

export default function MarketShapingFeed({ signals }: Props) {
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="flex items-center gap-2 mb-4">
        <span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />
        <h3 className="text-[13px] font-semibold text-slate-200">Market Shaping Signals</h3>
      </div>

      {signals.length === 0 ? (
        <p className="text-slate-600 text-[12px]">No market-shaping signals in the last 30 days</p>
      ) : (
        <ul className="space-y-3">
          {signals.slice(0, 6).map((item) => (
            <li key={item.id} className="flex gap-3">
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-medium text-slate-200 leading-snug line-clamp-2">
                  {item.title}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {item.company_slug && (
                    <Link
                      to={`/competitors/${item.company_slug}`}
                      className="text-[11px] text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      {item.company_name}
                    </Link>
                  )}
                  {item.assessment?.capability_primary && (
                    <span className="text-[11px] text-slate-500">
                      · {getCapabilityLabel(item.assessment.capability_primary)}
                    </span>
                  )}
                  <span className="text-[11px] text-slate-600">
                    · {formatDistanceToNow(item.published_at || item.created_at)}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
