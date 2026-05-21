import type { ScorecardTopMove } from '../../types/scorecard';

const CLASS_LABELS: Record<string, string> = {
  product_capability_move: 'Product',
  positioning_move: 'Positioning',
  ecosystem_move: 'Ecosystem',
  thought_leadership_signal: 'Thought Leadership',
  hiring_signal: 'Hiring',
  market_expansion_move: 'Expansion',
  weak_signal: 'Weak',
};

interface Props {
  moves: ScorecardTopMove[] | null | undefined;
  loading?: boolean;
}

export function TopMovesTimeline({ moves, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3 animate-pulse" />
        {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded mb-2 animate-pulse" />)}
      </div>
    );
  }

  const list = moves ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Moves</h3>
      {list.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No moves recorded in this period.</p>
      ) : (
        <ul className="space-y-2">
          {list.map((move) => (
            <li key={move.assessment_id} className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm text-gray-800 truncate">{move.title}</p>
                <span className="inline-block text-xs text-gray-500 bg-gray-100 rounded px-1.5 py-0.5 mt-0.5">
                  {CLASS_LABELS[move.signal_class] ?? move.signal_class}
                </span>
              </div>
              <span className="flex-shrink-0 text-xs font-semibold text-indigo-700 bg-indigo-50 rounded px-1.5 py-0.5">
                {move.movement_score}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
