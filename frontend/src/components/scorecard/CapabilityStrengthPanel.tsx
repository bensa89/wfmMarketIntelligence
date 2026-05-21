import type { CompetitorScorecard } from '../../types/scorecard';

interface Props {
  scorecard: CompetitorScorecard | null | undefined;
  loading?: boolean;
}

export function CapabilityStrengthPanel({ scorecard, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-32 bg-gray-200 rounded mb-3 animate-pulse" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 bg-gray-100 rounded mb-2 animate-pulse" />
        ))}
      </div>
    );
  }

  const caps = scorecard?.top_capabilities ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Capabilities</h3>
      {caps.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No capability data in this period.</p>
      ) : (
        <ul className="space-y-2">
          {caps.map((cap) => (
            <li key={cap.capability_key} className="flex items-center justify-between">
              <span className="text-sm text-gray-700 capitalize">
                {cap.capability_key.replace(/_/g, ' ')}
              </span>
              <span className="text-sm font-medium text-indigo-700">
                {cap.score != null ? Math.round(cap.score) : '—'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
