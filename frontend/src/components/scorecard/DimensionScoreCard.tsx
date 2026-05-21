import type { ScorecardDimension } from '../../types/scorecard';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const DIM_LABELS: Record<string, string> = {
  capability_strength: 'Capability Strength',
  market_impact: 'Market Impact',
  activity: 'Activity',
  customer_proof: 'Customer Proof',
  momentum: 'Momentum',
};

const DIM_PRIMARY_KPI: Record<string, string> = {
  capability_strength: 'cap_weighted_score',
  activity: 'act_weighted_strength',
  market_impact: 'mkt_weighted_visibility',
  customer_proof: 'cp_validation_score',
  momentum: 'mom_period_delta',
};

interface Props {
  dimensionKey: string;
  dimension: ScorecardDimension | null | undefined;
  loading?: boolean;
}

export function DimensionScoreCard({ dimensionKey, dimension, loading }: Props) {
  const label = DIM_LABELS[dimensionKey] ?? dimensionKey;

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4 animate-pulse">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3" />
        <div className="h-8 w-12 bg-gray-200 rounded mb-2" />
        <div className="h-3 w-32 bg-gray-100 rounded" />
      </div>
    );
  }

  const score = dimension?.score ?? null;
  const trend = dimension?.trend ?? null;
  const primaryKpi = DIM_PRIMARY_KPI[dimensionKey];
  const kpiValue = primaryKpi ? dimension?.kpis?.[primaryKpi]?.value : null;

  const trendIcon = trend === 'rising'
    ? <TrendingUp className="w-4 h-4 text-green-500" />
    : trend === 'declining'
    ? <TrendingDown className="w-4 h-4 text-red-500" />
    : trend === 'stable'
    ? <Minus className="w-4 h-4 text-gray-400" />
    : null;

  const scoreColor = score == null
    ? 'text-gray-400'
    : score >= 70 ? 'text-green-700'
    : score >= 40 ? 'text-yellow-700'
    : 'text-red-600';

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white hover:border-indigo-200 transition-colors">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
        {trendIcon}
      </div>
      <p className={`text-2xl font-bold ${scoreColor}`}>
        {score != null ? Math.round(score) : '—'}
      </p>
      {kpiValue != null && (
        <p className="mt-1 text-xs text-gray-400">
          {primaryKpi?.replace(/_/g, ' ')}: {typeof kpiValue === 'number' ? Math.round(kpiValue * 10) / 10 : kpiValue}
        </p>
      )}
      {score == null && (
        <p className="mt-1 text-xs text-gray-400 italic">No data this period</p>
      )}
    </div>
  );
}
