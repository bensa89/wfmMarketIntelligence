import type { ScorecardRiskFlag } from '../../types/scorecard';
import { AlertTriangle } from 'lucide-react';

interface Props {
  flags: ScorecardRiskFlag[] | null | undefined;
  loading?: boolean;
}

export function RiskFlagsPanel({ flags, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3 animate-pulse" />
        <div className="h-10 bg-gray-100 rounded animate-pulse" />
      </div>
    );
  }

  const list = flags ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        Risk Flags
      </h3>
      {list.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No high-risk signals in this period.</p>
      ) : (
        <ul className="space-y-2">
          {list.map((flag) => (
            <li key={flag.assessment_id} className="p-2 bg-amber-50 border border-amber-200 rounded text-sm">
              <p className="font-medium text-amber-900 truncate">{flag.title}</p>
              <p className="text-xs text-amber-700 mt-0.5 capitalize">
                {flag.capability_key.replace(/_/g, ' ')} · {flag.movement_strength.replace(/_/g, ' ')}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
