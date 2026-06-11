import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { useCompetitorBenchmark } from '../../hooks/useBenchmark';
import type { BenchmarkPeriodType, CompetitorBenchmarkDetail } from '../../types/benchmark';
import { CAPABILITIES } from '../../constants/capabilities';

const TIER_COLORS: Record<string, string> = {
  leader: '#059669',
  strong: '#2563eb',
  emerging: '#f59e0b',
  weakly_evidenced: '#d1d5db',
};

const TIER_LABELS: Record<string, string> = {
  leader: 'Leader',
  strong: 'Strong',
  emerging: 'Emerging',
  weakly_evidenced: 'Weakly Evidenced',
};

const PERIOD_OPTIONS: { value: BenchmarkPeriodType; label: string }[] = [
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
  { value: '180d', label: '180d' },
];

const PLOT_W = 620;
const PLOT_H = 360;
const PAD_T = 28;
const PAD_R = 24;
const PAD_B = 24;
const PAD_L = 24;
const ARROW_SCALE = 32;
const MAX_ARROW = 38;

interface Props {
  slug: string;
  onCapabilityClick: (detail: CompetitorBenchmarkDetail) => void;
}

function dotRadius(score: number) {
  return 8 + (score / 100) * 13;
}

function toX(momentum: number) {
  return PAD_L + (momentum / 5) * PLOT_W;
}

function toY(strength: number) {
  return PAD_T + PLOT_H - (strength / 100) * PLOT_H;
}

function arrowVec(mDelta: number | null, sDelta: number | null) {
  if (mDelta == null && sDelta == null) return null;
  const mNorm = (mDelta ?? 0) / 5;
  const sNorm = (sDelta ?? 0) / 100;
  const rawDx = mNorm * ARROW_SCALE;
  const rawDy = -sNorm * ARROW_SCALE; // SVG Y is inverted
  const rawLen = Math.sqrt(rawDx ** 2 + rawDy ** 2);
  if (rawLen < 1) return null;
  const cap = rawLen > MAX_ARROW ? MAX_ARROW / rawLen : 1;
  return { dx: rawDx * cap, dy: rawDy * cap, len: Math.min(rawLen, MAX_ARROW) };
}

export function CapabilityStrengthVsMovement({ slug, onCapabilityClick }: Props) {
  const [period, setPeriod] = useState<BenchmarkPeriodType>('30d');
  const [hovered, setHovered] = useState<string | null>(null);
  const [showInfo, setShowInfo] = useState(false);
  const { data, isLoading } = useCompetitorBenchmark(slug, period);

  const svgW = PLOT_W + PAD_L + PAD_R;
  const svgH = PLOT_H + PAD_T + PAD_B;

  if (isLoading || !data) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 h-[460px] flex items-center justify-center">
        <span className="text-slate-400 text-sm">{isLoading ? 'Loading…' : 'No data'}</span>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-900">Capability Strength vs. Movement</h3>
          <button
            onClick={() => setShowInfo(v => !v)}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <HelpCircle size={15} />
          </button>
        </div>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors border ${
                period === opt.value
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'text-slate-500 hover:text-slate-700 border-transparent'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {showInfo && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-100 rounded text-xs text-blue-800 leading-relaxed">
          <strong>X-axis:</strong> Current execution momentum (0–5). &nbsp;
          <strong>Y-axis:</strong> Relative capability strength (0–100). &nbsp;
          Arrows show trajectory — direction encodes (Δ momentum, Δ strength); length scales with magnitude. Dot size reflects current strength.
        </div>
      )}

      <div className="flex gap-2">
        {/* Y-axis labels */}
        <div className="flex flex-col justify-between text-[10px] text-slate-400 w-9 text-right select-none" style={{ paddingTop: PAD_T, paddingBottom: PAD_B }}>
          <span>High</span>
          <span>Med</span>
          <span>Low</span>
        </div>

        {/* Chart */}
        <div className="flex-1 overflow-x-auto">
          <svg width={svgW} height={svgH} className="block" style={{ minWidth: svgW }}>
            {/* Plot background */}
            <rect x={PAD_L} y={PAD_T} width={PLOT_W} height={PLOT_H} fill="#f8fafc" rx="6" />

            {/* Quadrant dividers */}
            <line x1={toX(2.5)} y1={PAD_T} x2={toX(2.5)} y2={PAD_T + PLOT_H} stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4 3" />
            <line x1={PAD_L} y1={toY(50)} x2={PAD_L + PLOT_W} y2={toY(50)} stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4 3" />

            {/* Quadrant labels */}
            <text x={PAD_L + 10} y={PAD_T + 16} fontSize="9.5" fontWeight="600" fill="#94a3b8" letterSpacing="0.3">Established but Quiet</text>
            <text x={toX(2.5) + 10} y={PAD_T + 16} fontSize="9.5" fontWeight="600" fill="#94a3b8" letterSpacing="0.3">Accelerating Strongholds</text>
            <text x={PAD_L + 10} y={PAD_T + PLOT_H - 8} fontSize="9.5" fontWeight="600" fill="#94a3b8" letterSpacing="0.3">Low Relevance</text>
            <text x={toX(2.5) + 10} y={PAD_T + PLOT_H - 8} fontSize="9.5" fontWeight="600" fill="#94a3b8" letterSpacing="0.3">Emerging Bets</text>

            {/* Data points */}
            {data.capabilities.map(cap => {
              const momentum = cap.sub_scores.execution_momentum;
              const cx = toX(momentum);
              const cy = toY(cap.relative_strength_score);
              const r = dotRadius(cap.relative_strength_score);
              const color = TIER_COLORS[cap.tier] ?? '#94a3b8';
              const isHovered = hovered === cap.capability_key;
              const vec = arrowVec(cap.momentum_delta, cap.strength_delta);
              const shortLabel = CAPABILITIES[cap.capability_key]?.label?.split(' ')[0] ?? cap.capability_key;

              // Arrow geometry
              let arrowEl = null;
              if (vec) {
                const ndx = vec.dx / vec.len;
                const ndy = vec.dy / vec.len;
                const startX = cx + ndx * (r + 2);
                const startY = cy + ndy * (r + 2);
                const tipX = startX + vec.dx;
                const tipY = startY + vec.dy;
                const angle = Math.atan2(vec.dy, vec.dx);
                const headLen = 5.5;
                const headAngle = Math.PI / 6;
                const p1x = tipX - headLen * Math.cos(angle - headAngle);
                const p1y = tipY - headLen * Math.sin(angle - headAngle);
                const p2x = tipX - headLen * Math.cos(angle + headAngle);
                const p2y = tipY - headLen * Math.sin(angle + headAngle);
                const strokeW = 1.2 + (vec.len / MAX_ARROW) * 1.1;
                arrowEl = (
                  <g opacity={isHovered ? 1 : 0.72} pointerEvents="none">
                    <line x1={startX} y1={startY} x2={tipX} y2={tipY} stroke={color} strokeWidth={strokeW} strokeLinecap="round" />
                    <polygon points={`${tipX},${tipY} ${p1x},${p1y} ${p2x},${p2y}`} fill={color} />
                  </g>
                );
              }

              // Tooltip position (clamp inside SVG)
              const ttW = 168;
              const ttH = 82;
              const ttX = Math.max(2, Math.min(cx - ttW / 2, svgW - ttW - 2));
              const ttY = Math.max(2, cy - r - ttH - 10);

              return (
                <g
                  key={cap.capability_key}
                  onMouseEnter={() => setHovered(cap.capability_key)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onCapabilityClick(cap)}
                  className="cursor-pointer"
                >
                  {arrowEl}

                  <circle
                    cx={cx} cy={cy} r={r}
                    fill={color}
                    opacity={isHovered ? 1 : 0.85}
                    stroke={isHovered ? 'white' : 'none'}
                    strokeWidth={2}
                    className="transition-opacity"
                  />

                  {/* Label beside dot */}
                  <text
                    x={cx + r + 5}
                    y={cy + 4}
                    fontSize="10"
                    fontWeight="500"
                    fill={isHovered ? '#0f172a' : color}
                    pointerEvents="none"
                    style={{ userSelect: 'none' }}
                  >
                    {shortLabel}
                  </text>

                  {/* Tooltip */}
                  {isHovered && (
                    <g pointerEvents="none">
                      <rect x={ttX} y={ttY} width={ttW} height={ttH} rx="5" fill="white" stroke="#e2e8f0" strokeWidth="1" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.10))" />
                      <text x={ttX + ttW / 2} y={ttY + 15} textAnchor="middle" fontSize="11" fontWeight="600" fill="#0f172a">
                        {CAPABILITIES[cap.capability_key]?.label ?? cap.capability_key}
                      </text>
                      <text x={ttX + ttW / 2} y={ttY + 30} textAnchor="middle" fontSize="10" fill="#475569">
                        {`Strength: ${cap.relative_strength_score} · ${TIER_LABELS[cap.tier] ?? cap.tier}`}
                      </text>
                      <text x={ttX + ttW / 2} y={ttY + 44} textAnchor="middle" fontSize="10" fill="#475569">
                        {`Δ Strength: ${cap.strength_delta != null ? (cap.strength_delta >= 0 ? '+' : '') + cap.strength_delta : '—'}`}
                      </text>
                      <text x={ttX + ttW / 2} y={ttY + 58} textAnchor="middle" fontSize="10" fill="#475569">
                        {`Momentum: ${momentum}/5  ·  Δ: ${cap.momentum_delta != null ? (cap.momentum_delta >= 0 ? '+' : '') + cap.momentum_delta : '—'}`}
                      </text>
                      <text x={ttX + ttW / 2} y={ttY + 72} textAnchor="middle" fontSize="10" fill="#94a3b8">
                        {`Conf: ${Math.round(cap.confidence * 100)}%  ·  ${cap.source_signal_count} signals`}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>

          {/* X-axis labels */}
          <div
            className="flex justify-between text-[10px] text-slate-400 mt-1"
            style={{ paddingLeft: PAD_L, paddingRight: PAD_R }}
          >
            <span>Low Movement</span>
            <span>High Movement</span>
          </div>
        </div>
      </div>

      {/* X-axis title + legend */}
      <div className="mt-3 ml-11 flex items-center justify-between">
        <span className="text-[10px] text-slate-400 font-medium tracking-wide">← Execution Momentum →</span>
        <div className="flex flex-wrap gap-3">
          {Object.entries(TIER_COLORS).map(([tier, color]) => (
            <div key={tier} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
              <span className="text-[10px] text-slate-500">{TIER_LABELS[tier]}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
