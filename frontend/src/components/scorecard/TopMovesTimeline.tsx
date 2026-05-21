import type { ScorecardTopMove } from '../../types/scorecard';
import { formatDistanceToNow } from '../../utils/dates';

const CLASS_LABELS: Record<string, string> = {
  product_capability_move: 'Product',
  positioning_move: 'Positioning',
  ecosystem_move: 'Ecosystem',
  thought_leadership_signal: 'Thought Leadership',
  hiring_signal: 'Hiring',
  market_expansion_move: 'Expansion',
  weak_signal: 'Weak Signal',
};

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
  moves: ScorecardTopMove[] | null | undefined;
  loading?: boolean;
  onSelect?: (signalId: string) => void;
}

export function TopMovesTimeline({ moves, loading, onSelect }: Props) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4 animate-pulse">
        <div className="h-4 w-24 bg-slate-200 rounded mb-3" />
        {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-slate-100 rounded mb-2" />)}
      </div>
    );
  }

  const list = moves ?? [];

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <h3 className="text-[13px] font-semibold text-slate-700 mb-3">Top Moves</h3>
      {list.length === 0 ? (
        <p className="text-slate-400 text-[12px]">No moves recorded in this period.</p>
      ) : (
        <ul className="space-y-3">
          {list.map((move) => (
            <li
              key={move.assessment_id}
              onClick={() => onSelect?.(move.signal_id)}
              className={`-mx-2 px-2 py-1.5 rounded-lg transition-colors ${onSelect ? 'cursor-pointer hover:bg-slate-50' : ''}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] text-slate-800 font-medium leading-snug line-clamp-2">{move.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[11px] text-slate-500">
                      {CLASS_LABELS[move.signal_class] ?? move.signal_class}
                    </span>
                    {move.published_at && (
                      <span className="text-[11px] text-slate-500">
                        {formatDistanceToNow(move.published_at)}
                      </span>
                    )}
                  </div>
                </div>
                <ScoreBadge score={move.movement_score} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
