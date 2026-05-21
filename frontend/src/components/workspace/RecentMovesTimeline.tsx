import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from '../signals/MovementBadge';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

function ScoreBadge({ score }: { score: number }) {
  const { bg, text, dot } = score >= 70
    ? { bg: 'rgba(139,92,246,0.15)', text: '#a78bfa', dot: '#8b5cf6' }
    : score >= 40
    ? { bg: 'rgba(59,130,246,0.15)', text: '#60a5fa', dot: '#3b82f6' }
    : { bg: 'rgba(100,116,139,0.15)', text: '#94a3b8', dot: '#64748b' };
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full font-medium px-2 py-0.5 text-[11px] flex-shrink-0"
      style={{ background: bg, color: text }}
    >
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: dot }} />
      {score}
    </span>
  );
}

interface Props {
  assessments: SignalFeedItem[];
  onSelectSignal: (item: SignalFeedItem) => void;
}

export default function RecentMovesTimeline({ assessments, onSelectSignal }: Props) {
  if (assessments.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4">
        <p className="text-slate-400 text-[12px]">No recent moves</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <h3 className="text-[13px] font-semibold text-slate-700 mb-3">Recent Moves</h3>
      <ul className="space-y-3">
        {assessments.slice(0, 15).map((item) => (
          <li
            key={item.id}
            className="cursor-pointer hover:bg-slate-50 -mx-2 px-2 py-1.5 rounded-lg transition-colors"
            onClick={() => onSelectSignal(item)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-[12px] text-slate-800 font-medium leading-snug line-clamp-2">
                  {item.title}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {item.assessment?.capability_primary && (
                    <span className="text-[11px] text-slate-500">
                      {getCapabilityLabel(item.assessment.capability_primary)}
                    </span>
                  )}
                  <span className="text-[11px] text-slate-500">
                    {formatDistanceToNow(item.published_at || item.created_at)}
                  </span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <MovementBadge strength={item.assessment?.movement_strength} size="sm" />
                {item.assessment?.movement_score != null && (
                  <ScoreBadge score={item.assessment.movement_score} />
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
