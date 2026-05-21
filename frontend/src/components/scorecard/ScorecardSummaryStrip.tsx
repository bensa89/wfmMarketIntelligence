import type { BenchmarkScorecardItem } from '../../types/scorecard';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const TREND_ICONS = {
  rising: <TrendingUp className="w-4 h-4 text-green-500" />,
  declining: <TrendingDown className="w-4 h-4 text-red-500" />,
  stable: <Minus className="w-4 h-4 text-gray-400" />,
};

const TOP_DIMENSIONS = ['capability_strength', 'market_impact'];
const DIM_LABELS: Record<string, string> = {
  capability_strength: 'Cap',
  market_impact: 'Impact',
  activity: 'Activity',
  customer_proof: 'Proof',
  momentum: 'Momentum',
};

interface Props {
  scorecard: BenchmarkScorecardItem | null | undefined;
  loading?: boolean;
}

export function ScorecardSummaryStrip({ scorecard, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 mt-2 animate-pulse">
        <div className="h-7 w-12 rounded-full bg-gray-200" />
        <div className="h-5 w-4 rounded bg-gray-200" />
        <div className="h-5 w-16 rounded-full bg-gray-200" />
        <div className="h-5 w-16 rounded-full bg-gray-200" />
        <div className="h-5 w-14 rounded bg-gray-200" />
      </div>
    );
  }

  if (!scorecard || scorecard.overall_score == null) {
    return (
      <p className="mt-2 text-xs text-gray-400 italic">No scorecard data for this period</p>
    );
  }

  const trend = scorecard.overall_trend as keyof typeof TREND_ICONS | null;

  return (
    <div className="flex items-center gap-3 mt-2 flex-wrap">
      {/* Overall score badge */}
      <span className="inline-flex items-center justify-center w-10 h-7 rounded-full bg-indigo-100 text-indigo-800 text-xs font-bold">
        {Math.round(scorecard.overall_score)}
      </span>

      {/* Trend */}
      {trend && TREND_ICONS[trend]}

      {/* Top 2 dimension pills */}
      {TOP_DIMENSIONS.map((dim) => {
        const score = scorecard.dimension_scores?.[dim]?.score;
        if (score == null) return null;
        return (
          <span key={dim} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs">
            <span className="font-medium">{DIM_LABELS[dim]}</span>
            <span>{Math.round(score)}</span>
          </span>
        );
      })}

      {/* Rank badge */}
      {scorecard.rank && (
        <span className="text-xs text-gray-500">
          #{scorecard.rank} of {/* total available from parent */}
        </span>
      )}
    </div>
  );
}
