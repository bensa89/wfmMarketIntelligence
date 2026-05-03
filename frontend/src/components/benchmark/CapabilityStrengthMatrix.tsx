import { useState } from 'react';
import type { BenchmarkOverviewResponse, BenchmarkMatrixCell, BenchmarkTier } from '../../types/benchmark';
import { CAPABILITIES } from '../../constants/capabilities';
import { TierBadge } from './TierBadge';
import { ConfidenceIndicator } from './ConfidenceIndicator';

const TIER_BG: Record<BenchmarkTier, string> = {
  leader: 'bg-emerald-600',
  strong: 'bg-blue-600',
  emerging: 'bg-amber-400',
  weakly_evidenced: 'bg-slate-100',
};

const TIER_TEXT: Record<BenchmarkTier, string> = {
  leader: 'text-white',
  strong: 'text-white',
  emerging: 'text-slate-900',
  weakly_evidenced: 'text-slate-400',
};

interface MatrixCellProps {
  cell: BenchmarkMatrixCell;
  onClick?: () => void;
}

function MatrixCell({ cell, onClick }: MatrixCellProps) {
  const [hovered, setHovered] = useState(false);
  const tier = cell.tier as BenchmarkTier;
  const opacity = cell.confidence < 0.5 ? 'opacity-60' : 'opacity-100';

  return (
    <div className="relative">
      <button
        onClick={onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={`w-full h-12 rounded flex items-center justify-center font-semibold text-sm transition-all
          ${TIER_BG[tier]} ${TIER_TEXT[tier]} ${opacity} hover:ring-2 hover:ring-slate-400`}
      >
        {cell.score}
      </button>
      {hovered && (
        <div className="absolute z-50 bottom-full mb-2 left-1/2 -translate-x-1/2 w-52 bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-left pointer-events-none">
          <div className="flex items-center justify-between mb-2">
            <TierBadge tier={tier} size="sm" />
            {cell.rank && <span className="text-xs text-slate-500">#{cell.rank}</span>}
          </div>
          <div className="text-xs text-slate-600 mb-1">Score: <span className="font-medium text-slate-900">{cell.score}</span></div>
          <div className="text-xs text-slate-600 mb-1">Momentum: <span className="font-medium text-slate-900">{cell.momentum_score}/5</span></div>
          <div className="flex items-center gap-1 text-xs text-slate-600">
            Confidence: <ConfidenceIndicator confidence={cell.confidence} showLabel />
          </div>
          {tier === 'weakly_evidenced' && (
            <p className="mt-2 text-xs text-slate-400 italic">Kaum Belege — keine Schwache-Aussage</p>
          )}
        </div>
      )}
    </div>
  );
}

interface CapabilityStrengthMatrixProps {
  data: BenchmarkOverviewResponse;
  onCapabilityClick?: (capKey: string) => void;
  onCompetitorClick?: (slug: string) => void;
}

export function CapabilityStrengthMatrix({ data, onCapabilityClick, onCompetitorClick }: CapabilityStrengthMatrixProps) {
  const visibleCaps = data.capabilities.filter(k => CAPABILITIES[k]?.visibilityToUser !== false);

  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-1 min-w-max">
        <thead>
          <tr>
            <th className="w-36 text-left text-xs text-slate-500 font-medium pb-2 pr-3">Competitor</th>
            {visibleCaps.map(capKey => (
              <th key={capKey} className="w-12">
                <button
                  onClick={() => onCapabilityClick?.(capKey)}
                  className="text-xs text-slate-600 font-medium hover:text-slate-900 truncate block max-w-[48px] leading-tight text-center"
                  title={CAPABILITIES[capKey]?.label ?? capKey}
                >
                  {(CAPABILITIES[capKey]?.label ?? capKey).split(' ')[0]}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.competitors.map(comp => (
            <tr key={comp.id}>
              <td className="text-xs text-slate-700 font-medium pr-3 whitespace-nowrap">
                <button
                  onClick={() => onCompetitorClick?.(comp.slug)}
                  className="hover:underline text-left"
                >
                  {comp.name}
                </button>
              </td>
              {visibleCaps.map(capKey => {
                const cell = data.matrix[capKey]?.[comp.id] ?? {
                  score: 0, tier: 'weakly_evidenced' as BenchmarkTier, confidence: 0, rank: null, momentum_score: 0,
                };
                return (
                  <td key={capKey}>
                    <MatrixCell
                      cell={cell}
                      onClick={() => onCapabilityClick?.(capKey)}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}