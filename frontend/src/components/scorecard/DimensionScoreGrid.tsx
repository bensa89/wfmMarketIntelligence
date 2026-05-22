import type { ReactNode } from 'react';
import type { ScorecardDimension } from '../../types/scorecard';
import { DimensionScoreCard } from './DimensionScoreCard';

const DIMENSIONS = ['capability_strength', 'market_impact', 'activity', 'customer_proof', 'momentum'];

interface Props {
  dimensionScores: Record<string, ScorecardDimension> | null | undefined;
  loading?: boolean;
  slot?: ReactNode;
  slotFirst?: boolean;
}

export function DimensionScoreGrid({ dimensionScores, loading, slot, slotFirst }: Props) {
  const slotCard = slot ? (
    <div className="rounded-lg border border-gray-200 p-4 bg-white flex flex-col gap-2 h-full">
      {slot}
    </div>
  ) : null;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 [grid-template-rows:repeat(2,minmax(0,1fr))] min-h-[11rem]">
      {slotFirst && slotCard}
      {DIMENSIONS.map((dim) => (
        <DimensionScoreCard
          key={dim}
          dimensionKey={dim}
          dimension={dimensionScores?.[dim]}
          loading={loading}
        />
      ))}
      {!slotFirst && slotCard}
    </div>
  );
}
