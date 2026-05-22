import { X } from 'lucide-react';
import type { CompetitorBenchmarkDetail, BenchmarkPeriodType } from '../../types/benchmark';
import { TierBadge } from '../benchmark/TierBadge';
import { InfoTooltip } from './InfoTooltip';
import { useCapabilityAssessments } from '../../hooks/useBenchmark';

// ─── Momentum helpers ────────────────────────────────────────────────────────

function getMomentumColor(score: number): string {
  if (score >= 80) return '#f97316';
  if (score >= 60) return '#8b5cf6';
  if (score >= 30) return '#3b82f6';
  return '#64748b';
}

function getMomentumLabel(score: number): string {
  if (score >= 80) return 'Sehr hoch (≥80)';
  if (score >= 60) return 'Hoch (≥60)';
  if (score >= 30) return 'Mittel (≥30)';
  return 'Gering (<30)';
}

// ─── Sub-score metadata ───────────────────────────────────────────────────────

const SUB_SCORE_META = [
  {
    key: 'capability_depth' as const,
    label: 'Capability Depth',
    weight: '35%',
    tooltip:
      'Qualität und Substanz der Signale: Wie stark deuten Produkt-Moves, Positionierung und Evidenzstärke auf echte Capability-Tiefe hin?',
  },
  {
    key: 'execution_momentum' as const,
    label: 'Execution Momentum',
    weight: '25%',
    tooltip:
      'Signal-Dichte + durchschnittlicher Bewegungsscore + Anteil starker Moves. Wie aktiv und kraftvoll agiert der Wettbewerber?',
  },
  {
    key: 'market_proof' as const,
    label: 'Market Proof',
    weight: '20%',
    tooltip:
      'Externe Belege: Ecosystem-Moves, Kunden-Referenzen, hoher Visibility-Impact. Wie sichtbar ist die Capability am Markt?',
  },
  {
    key: 'strategic_focus' as const,
    label: 'Strategic Focus',
    weight: '10%',
    tooltip:
      'Anteil aller Assessments, der auf diese Capability entfällt + Positionierungs-Moves. Wie stark priorisiert der Wettbewerber diese Fähigkeit?',
  },
  {
    key: 'evidence_coverage' as const,
    label: 'Evidence Coverage',
    weight: '10%',
    tooltip:
      'Kombination aus Quellen-Diversität, Confidence der Assessments und Aktualität (Freshness). Wie verlässlich ist die Datenbasis?',
  },
];

// ─── Sub-score bar ────────────────────────────────────────────────────────────

function SubScoreBar({ label, value, weight, tooltip }: { label: string; value: number; weight: string; tooltip: string }) {
  const color = value >= 4 ? 'bg-emerald-500' : value >= 2 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-3">
      <div className="w-40 shrink-0 flex items-center gap-1.5">
        <span className="text-xs text-slate-700 truncate">{label}</span>
        <InfoTooltip text={tooltip} placement="bottom" />
        <span className="text-[10px] text-slate-400 ml-auto">{weight}</span>
      </div>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${(value / 5) * 100}%` }}
        />
      </div>
      <span className="w-8 text-right text-xs font-mono text-slate-600 shrink-0">{value}/5</span>
    </div>
  );
}

// ─── Momentum legend ──────────────────────────────────────────────────────────

function MomentumLegend() {
  const levels = [
    { score: 80, label: '≥80 — Sehr hohe Aktivitätsintensität', color: '#f97316' },
    { score: 60, label: '≥60 — Hohe Intensität', color: '#8b5cf6' },
    { score: 30, label: '≥30 — Mittlere Intensität', color: '#3b82f6' },
    { score: 0,  label: '<30 — Geringe Intensität', color: '#64748b' },
  ];
  return (
    <div className="space-y-1.5">
      {levels.map(({ label, color }) => (
        <div key={label} className="flex items-center gap-2 text-xs text-slate-600">
          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
          {label}
        </div>
      ))}
    </div>
  );
}

// ─── Panel mode content ───────────────────────────────────────────────────────

function PanelModeContent() {
  return (
    <div className="space-y-6 text-sm">
      <div>
        <h3 className="font-semibold text-slate-800 mb-1">Was ist der Relative Capability Score?</h3>
        <p className="text-slate-600 text-xs leading-relaxed">
          Der Score (0–100) misst, wie stark ein Wettbewerber in einer bestimmten Capability aktiv und belegt ist — relativ zu seinen eigenen Signalen im gewählten Zeitraum. Er ist kein absoluter Marktvergleich, sondern ein gewichtetes Qualitäts- und Aktivitätsmaß.
        </p>
      </div>

      <div>
        <h3 className="font-semibold text-slate-800 mb-2">Score-Formel</h3>
        <div className="space-y-1.5">
          {SUB_SCORE_META.map(({ label, weight, tooltip }) => (
            <div key={label} className="flex items-center gap-2 text-xs text-slate-600">
              <InfoTooltip text={tooltip} placement="bottom" />
              <span className="flex-1">{label}</span>
              <span className="font-medium text-slate-800">{weight}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="font-semibold text-slate-800 mb-2">Tier-Definitionen</h3>
        <div className="space-y-1.5 text-xs">
          {[
            { label: 'Leader', range: '≥75', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
            { label: 'Strong', range: '≥55', color: 'text-blue-700 bg-blue-50 border-blue-200' },
            { label: 'Emerging', range: '≥30', color: 'text-amber-700 bg-amber-50 border-amber-200' },
            { label: 'Weakly Evidenced', range: '<30 oder zu wenig Belege', color: 'text-slate-500 bg-slate-50 border-slate-200' },
          ].map(({ label, range, color }) => (
            <div key={label} className={`flex items-center justify-between px-3 py-1.5 rounded border ${color}`}>
              <span className="font-medium">{label}</span>
              <span>{range}</span>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-slate-400 mt-1.5">Bei niedriger Confidence wird das Tier um eine Stufe reduziert.</p>
      </div>

      <div>
        <h3 className="font-semibold text-slate-800 mb-2">Momentum-Farblegende</h3>
        <p className="text-xs text-slate-500 mb-2">Farbe des Stärkebalkens = durchschnittlicher Movement Score aller Assessments dieser Capability.</p>
        <MomentumLegend />
      </div>
    </div>
  );
}

// ─── Capability mode content ──────────────────────────────────────────────────

interface CapabilityModeContentProps {
  detail: CompetitorBenchmarkDetail;
  slug: string;
  periodType: BenchmarkPeriodType;
  avgMovementScore?: number;
  periodLabel: string;
  onSelectSignal: (signalId: string) => void;
}

function CapabilityModeContent({
  detail,
  slug,
  periodType,
  avgMovementScore,
  periodLabel,
  onSelectSignal,
}: CapabilityModeContentProps) {
  const { data, isLoading } = useCapabilityAssessments(slug, detail.capability_key, periodType, true);

  return (
    <div className="space-y-6">
      {/* Sub-score breakdown */}
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Sub-Score Breakdown</h3>
        <div className="space-y-3">
          {SUB_SCORE_META.map(({ key, label, weight, tooltip }) => (
            <SubScoreBar
              key={key}
              label={label}
              value={detail.sub_scores[key]}
              weight={weight}
              tooltip={tooltip}
            />
          ))}
        </div>
        <p className="text-[11px] text-slate-400 mt-3">
          Gesamtscore: <strong className="text-slate-700">{detail.relative_strength_score}/100</strong>
          {' '}(Σ gewichteter Sub-Scores × 20)
        </p>
      </div>

      {/* Activity */}
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Activity</h3>
        <div className="flex gap-4 text-xs text-slate-600">
          <div>
            <span className="text-slate-400">Assessments</span>
            <p className="font-semibold text-slate-800 text-base">{detail.source_signal_count}</p>
            <p className="text-slate-400">{periodLabel}</p>
          </div>
          {avgMovementScore !== undefined && (
            <div>
              <span className="text-slate-400">Avg. Movement Score</span>
              <p className="font-semibold text-base" style={{ color: getMomentumColor(avgMovementScore) }}>
                {avgMovementScore}
              </p>
              <p className="text-slate-400">{getMomentumLabel(avgMovementScore)}</p>
            </div>
          )}
        </div>
        {avgMovementScore !== undefined && (
          <div className="mt-3">
            <MomentumLegend />
          </div>
        )}
      </div>

      {/* Contributing assessments */}
      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Contributing Assessments</h3>
        {isLoading && (
          <div className="space-y-2 animate-pulse">
            {[1, 2, 3].map((i) => <div key={i} className="h-8 bg-slate-100 rounded" />)}
          </div>
        )}
        {!isLoading && data && data.assessments.length === 0 && (
          <p className="text-xs text-slate-400 italic">Keine Assessments für diesen Zeitraum.</p>
        )}
        {!isLoading && data && data.assessments.length > 0 && (
          <>
            <ul className="space-y-1.5">
              {data.assessments.map((a) => (
                <li
                  key={a.assessment_id}
                  onClick={() => onSelectSignal(a.signal_id)}
                  className="flex items-center justify-between gap-3 text-xs p-2 rounded-lg hover:bg-slate-50 cursor-pointer group"
                >
                  <span className="text-slate-700 truncate group-hover:text-slate-900">{a.title}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-slate-400">{a.signal_class.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-indigo-600">{a.movement_score}</span>
                  </div>
                </li>
              ))}
            </ul>
            {data.total_count > 20 && (
              <p className="text-[11px] text-slate-400 italic mt-2">
                … und {data.total_count - 20} weitere Assessments
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main drawer ──────────────────────────────────────────────────────────────

interface CapabilityExplainDrawerProps {
  open: boolean;
  onClose: () => void;
  mode: 'panel' | 'capability';
  slug?: string;
  detail?: CompetitorBenchmarkDetail;
  periodType?: BenchmarkPeriodType;
  avgMovementScore?: number;
  onSelectSignal?: (signalId: string) => void;
}

const PERIOD_LABELS: Record<string, string> = {
  '30d': 'Letzten 30 Tage',
  '90d': 'Letzten 90 Tage',
  '180d': 'Letzten 180 Tage',
};

export function CapabilityExplainDrawer({
  open,
  onClose,
  mode,
  slug,
  detail,
  periodType = '30d',
  avgMovementScore,
  onSelectSignal,
}: CapabilityExplainDrawerProps) {
  if (!open) return null;

  const title = mode === 'panel'
    ? 'Was bedeutet das?'
    : detail?.label ?? 'Capability';

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-gray-800">{title}</h2>
            {mode === 'capability' && detail && (
              <TierBadge tier={detail.tier} size="sm" />
            )}
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {mode === 'panel' && <PanelModeContent />}
          {mode === 'capability' && detail && slug && (
            <CapabilityModeContent
              detail={detail}
              slug={slug}
              periodType={periodType}
              avgMovementScore={avgMovementScore}
              periodLabel={PERIOD_LABELS[periodType] ?? periodType}
              onSelectSignal={onSelectSignal ?? (() => {})}
            />
          )}
        </div>
      </div>
    </>
  );
}
