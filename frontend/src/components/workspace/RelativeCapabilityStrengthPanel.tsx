import { useState } from 'react';
import { useCompetitorBenchmark } from '../../hooks/useBenchmark';
import type { BenchmarkPeriodType, CompetitorBenchmarkDetail } from '../../types/benchmark';
import { TierBadge } from '../benchmark/TierBadge';
import { ConfidenceIndicator } from '../benchmark/ConfidenceIndicator';
import { StrengthDeltaIndicator } from '../benchmark/StrengthDeltaIndicator';

interface RelativeCapabilityStrengthPanelProps {
  slug: string;
}

const PERIOD_OPTIONS: { value: BenchmarkPeriodType; label: string }[] = [
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
  { value: '180d', label: '180d' },
];

function StrengthBar({ score }: { score: number }) {
  return (
    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
      <div
        className="h-full bg-blue-500 rounded-full transition-all"
        style={{ width: `${score}%` }}
      />
    </div>
  );
}

function CapabilityRow({ detail }: { detail: CompetitorBenchmarkDetail }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
      <div className="w-32 shrink-0">
        <span className="text-xs text-slate-700 font-medium truncate block">{detail.label}</span>
      </div>
      <StrengthBar score={detail.relative_strength_score} />
      <span className="w-8 text-right text-xs font-mono text-slate-600 shrink-0">{detail.relative_strength_score}</span>
      <TierBadge tier={detail.tier} size="sm" />
      {detail.peer_rank && (
        <span className="text-xs text-slate-400 shrink-0">#{detail.peer_rank}</span>
      )}
      <StrengthDeltaIndicator delta={detail.strength_delta} />
      <ConfidenceIndicator confidence={detail.confidence} />
    </div>
  );
}

export function RelativeCapabilityStrengthPanel({ slug }: RelativeCapabilityStrengthPanelProps) {
  const [period, setPeriod] = useState<BenchmarkPeriodType>('30d');
  const { data, isLoading } = useCompetitorBenchmark(slug, period);

  const evidenced = data?.capabilities.filter(c => c.tier !== 'weakly_evidenced') ?? [];
  const weakly = data?.capabilities.filter(c => c.tier === 'weakly_evidenced') ?? [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-900">Relative Capability Strength</h3>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                period === opt.value
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-sm text-slate-400">Loading benchmark data…</p>}

      {data && (
        <>
          {evidenced.length > 0 && (
            <div className="mb-4">
              {evidenced
                .sort((a, b) => b.relative_strength_score - a.relative_strength_score)
                .map(d => <CapabilityRow key={d.capability_key} detail={d} />)}
            </div>
          )}
          {weakly.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-slate-400 cursor-pointer select-none">
                {weakly.length} capability{weakly.length > 1 ? 'ies' : 'y'} with insufficient evidence
              </summary>
              <div className="mt-2 opacity-60">
                {weakly.map(d => <CapabilityRow key={d.capability_key} detail={d} />)}
              </div>
            </details>
          )}
          {evidenced.length === 0 && weakly.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-6">No benchmark data yet. Run a recompute to generate scores.</p>
          )}
        </>
      )}
    </div>
  );
}