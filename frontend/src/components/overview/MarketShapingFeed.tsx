import { Link } from 'react-router-dom';
import type { SignalFeedItem } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  signals: SignalFeedItem[];
  onSelect?: (item: SignalFeedItem) => void;
}

export default function MarketShapingFeed({ signals, onSelect }: Props) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />
        <h3 className="text-[13px] font-semibold text-slate-700">Market Shaping Signals</h3>
      </div>

      {signals.length === 0 ? (
        <p className="text-slate-400 text-[12px]">No market-shaping signals in the last 30 days</p>
      ) : (
        <ul className="space-y-3">
          {signals.slice(0, 6).map((item) => (
            <li key={item.id} className="flex gap-3">
              <div className="flex-1 min-w-0">
                <button
                  onClick={() => onSelect?.(item)}
                  className="text-[12px] font-medium text-slate-800 leading-snug line-clamp-2 text-left hover:text-blue-700 transition-colors cursor-pointer"
                >
                  {item.title}
                </button>
                <div className="flex items-center gap-2 mt-1">
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
    </div>
  );
}
