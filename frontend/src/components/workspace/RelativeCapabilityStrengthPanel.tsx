import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { useCompetitorBenchmark } from '../../hooks/useBenchmark';
import type { BenchmarkPeriodType, CompetitorBenchmarkDetail } from '../../types/benchmark';
import type { CapabilityCount } from '../../types/intelligence';
import { TierBadge } from '../benchmark/TierBadge';
import { ConfidenceIndicator } from '../benchmark/ConfidenceIndicator';
import { StrengthDeltaIndicator } from '../benchmark/StrengthDeltaIndicator';
import { InfoTooltip } from './InfoTooltip';

interface RelativeCapabilityStrengthPanelProps {
  slug: string;
  capabilityDistribution?: CapabilityCount[];
  onCapabilityClick?: (detail: CompetitorBenchmarkDetail) => void;
  onInfoClick?: () => void;
}

const PERIOD_OPTIONS: { value: BenchmarkPeriodType; label: string }[] = [
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
  { value: '180d', label: '180d' },
];

const COLUMN_TOOLTIPS = {
  score: 'Score 0–100. Gewichteter Durchschnitt aus 5 Sub-Scores: Capability Depth (35%), Execution Momentum (25%), Market Proof (20%), Strategic Focus (10%), Evidence Coverage (10%).',
  tier: 'Leader (≥75), Strong (≥55), Emerging (≥30), Weakly Evidenced (<30 oder zu wenig Belege). Wird bei niedriger Confidence um eine Stufe reduziert.',
  rank: 'Position im Vergleich zu allen Wettbewerbern für diese Capability im gewählten Zeitraum.',
  delta: 'Veränderung des Scores zur Vorperiode (positiv = gestärkt, negativ = geschwächt).',
  conf: 'Confidence-Score 0–1: basiert auf Anzahl der Assessments, Evidence Coverage und durchschnittlichem Konfidenzwert.',
  signals: 'Anzahl der Assessments, die in diesem Zeitraum dieser Capability zugeordnet wurden.',
};

const MOMENTUM_BAR_TOOLTIP =
  'Balkenfarbe = durchschnittlicher Movement Score aller Assessments:\n🟠 ≥80 sehr hoch · 🟣 ≥60 hoch · 🔵 ≥30 mittel · ⚫ <30 gering';

function getMomentumColor(score?: number): string {
  if (score === undefined) return '#3b82f6';
  if (score >= 80) return '#f97316';
  if (score >= 60) return '#8b5cf6';
  if (score >= 30) return '#3b82f6';
  return '#64748b';
}

function StrengthBar({ score, momentumColor }: { score: number; momentumColor: string }) {
  return (
    <div className="relative flex-1 group/bar">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, backgroundColor: momentumColor }}
        />
      </div>
      {/* Momentum bar tooltip */}
      <span className="absolute z-50 bottom-full mb-1.5 left-1/2 -translate-x-1/2 w-64 bg-slate-900 text-white text-[10px] rounded-lg px-2.5 py-1.5 shadow-xl pointer-events-none leading-snug whitespace-pre-line hidden group-hover/bar:block">
        {MOMENTUM_BAR_TOOLTIP}
      </span>
    </div>
  );
}

function ColumnHeaders() {
  return (
    <div className="flex items-center gap-3 pb-1.5 border-b border-slate-100 mb-1">
      <div className="w-32 shrink-0" />
      <div className="flex-1 flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Score <InfoTooltip text={COLUMN_TOOLTIPS.score} />
      </div>
      <div className="w-8 shrink-0" />
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Tier <InfoTooltip text={COLUMN_TOOLTIPS.tier} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        # <InfoTooltip text={COLUMN_TOOLTIPS.rank} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Δ <InfoTooltip text={COLUMN_TOOLTIPS.delta} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Conf <InfoTooltip text={COLUMN_TOOLTIPS.conf} />
      </div>
      <div className="flex items-center gap-1 text-[10px] text-slate-400 font-medium">
        Signals <InfoTooltip text={COLUMN_TOOLTIPS.signals} />
      </div>
    </div>
  );
}

function CapabilityRow({
  detail,
  momentumColor,
  onClick,
}: {
  detail: CompetitorBenchmarkDetail;
  momentumColor: string;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0 cursor-pointer hover:bg-slate-50 rounded -mx-1 px-1 transition-colors"
    >
      <div className="w-32 shrink-0">
        <span className="text-xs text-slate-700 font-medium truncate block">{detail.label}</span>
      </div>
      <StrengthBar score={detail.relative_strength_score} momentumColor={momentumColor} />
      <span className="w-8 text-right text-xs font-mono text-slate-600 shrink-0">
        {detail.relative_strength_score}
      </span>
      <TierBadge tier={detail.tier} size="sm" />
      {detail.peer_rank ? (
        <span className="text-xs text-slate-400 shrink-0 w-5 text-right">#{detail.peer_rank}</span>
      ) : (
        <span className="w-5" />
      )}
      <StrengthDeltaIndicator delta={detail.strength_delta} />
      <ConfidenceIndicator confidence={detail.confidence} />
      <span className="text-[11px] text-slate-400 shrink-0 w-12 text-right">
        {detail.source_signal_count > 0 ? `${detail.source_signal_count}` : '—'}
      </span>
    </div>
  );
}

export function RelativeCapabilityStrengthPanel({
  slug,
  capabilityDistribution,
  onCapabilityClick,
  onInfoClick,
}: RelativeCapabilityStrengthPanelProps) {
  const [period, setPeriod] = useState<BenchmarkPeriodType>('30d');
  const { data, isLoading } = useCompetitorBenchmark(slug, period);

  const distLookup = new Map(
    (capabilityDistribution ?? []).map((d) => [d.capability_key, d.avg_movement_score])
  );

  const evidenced = data?.capabilities.filter(c => c.tier !== 'weakly_evidenced') ?? [];
  const weakly = data?.capabilities.filter(c => c.tier === 'weakly_evidenced') ?? [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-1.5">
          <h3 className="text-sm font-semibold text-slate-900">Relative Capability Strength</h3>
          <button
            onClick={onInfoClick}
            className="p-0.5 rounded hover:bg-slate-100 transition-colors"
            title="Was bedeutet das?"
          >
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
          </button>
        </div>
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
          <ColumnHeaders />
          {evidenced.length > 0 && (
            <div className="mb-4">
              {evidenced
                .sort((a, b) => b.relative_strength_score - a.relative_strength_score)
                .map(d => (
                  <CapabilityRow
                    key={d.capability_key}
                    detail={d}
                    momentumColor={getMomentumColor(distLookup.get(d.capability_key))}
                    onClick={() => onCapabilityClick?.(d)}
                  />
                ))}
            </div>
          )}
          {weakly.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-slate-400 cursor-pointer select-none">
                {weakly.length} capability{weakly.length > 1 ? 'ies' : 'y'} with insufficient evidence
              </summary>
              <div className="mt-2 opacity-60">
                {weakly.map(d => (
                  <CapabilityRow
                    key={d.capability_key}
                    detail={d}
                    momentumColor={getMomentumColor(distLookup.get(d.capability_key))}
                    onClick={() => onCapabilityClick?.(d)}
                  />
                ))}
              </div>
            </details>
          )}
          {evidenced.length === 0 && weakly.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-6">
              No benchmark data yet. Run a recompute to generate scores.
            </p>
          )}
        </>
      )}
    </div>
  );
}
