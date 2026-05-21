import type { ReactNode } from 'react';
import type { ScorecardDimension } from '../../types/scorecard';
import { DimensionScoreCard } from './DimensionScoreCard';

const DIMENSIONS = ['capability_strength', 'market_impact', 'activity', 'customer_proof', 'momentum'];

interface Props {
  dimensionScores: Record<string, ScorecardDimension> | null | undefined;
  loading?: boolean;
  slot?: ReactNode;
}

export function DimensionScoreGrid({ dimensionScores, loading, slot }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {DIMENSIONS.map((dim) => (
        <DimensionScoreCard
          key={dim}
          dimensionKey={dim}
          dimension={dimensionScores?.[dim]}
          loading={loading}
        />
      ))}
      {slot && (
        <div className="rounded-lg border border-gray-200 p-4 bg-white flex flex-col justify-center gap-2">
          {slot}
        </div>
      )}
    </div>
  );
}
