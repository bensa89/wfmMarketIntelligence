import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from '../signals/MovementBadge';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  assessments: SignalFeedItem[];
  onSelectSignal: (item: SignalFeedItem) => void;
}

export default function RecentMovesTimeline({ assessments, onSelectSignal }: Props) {
  if (assessments.length === 0) {
    return (
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <p className="text-slate-600 text-[12px]">No recent moves</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <h3 className="text-[13px] font-semibold text-slate-200 mb-3">Recent Moves</h3>
      <ul className="space-y-3">
        {assessments.slice(0, 15).map((item) => (
          <li
            key={item.id}
            className="cursor-pointer hover:bg-white/5 -mx-2 px-2 py-1.5 rounded-lg transition-colors"
            onClick={() => onSelectSignal(item)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-[12px] text-slate-200 font-medium leading-snug line-clamp-2">
                  {item.title}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {item.assessment?.capability_primary && (
                    <span className="text-[11px] text-slate-500">
                      {getCapabilityLabel(item.assessment.capability_primary)}
                    </span>
                  )}
                  <span className="text-[11px] text-slate-600">
                    {formatDistanceToNow(item.published_at || item.created_at)}
                  </span>
                </div>
              </div>
              <MovementBadge strength={item.assessment?.movement_strength} size="sm" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
