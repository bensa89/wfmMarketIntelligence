import type { ScorecardDimension } from '../../types/scorecard';
import { DimensionScoreCard } from './DimensionScoreCard';

const DIMENSIONS = ['capability_strength', 'market_impact', 'activity', 'customer_proof', 'momentum'];

interface Props {
  dimensionScores: Record<string, ScorecardDimension> | null | undefined;
  loading?: boolean;
}

export function DimensionScoreGrid({ dimensionScores, loading }: Props) {
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
    </div>
  );
}
