import { useNavigate } from 'react-router-dom';
import { useCapabilityLeaderboard } from '../../hooks/useBenchmark';
import type { BenchmarkPeriodType } from '../../types/benchmark';
import { TierBadge } from './TierBadge';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { StrengthDeltaIndicator } from './StrengthDeltaIndicator';
import { CAPABILITIES } from '../../constants/capabilities';

interface CapabilityLeaderboardDrawerProps {
  capKey: string | null;
  periodType: BenchmarkPeriodType;
  onClose: () => void;
}

export function CapabilityLeaderboardDrawer({ capKey, periodType, onClose }: CapabilityLeaderboardDrawerProps) {
  const navigate = useNavigate();
  const { data, isLoading } = useCapabilityLeaderboard(capKey, periodType);

  if (!capKey) return null;

  const label = CAPABILITIES[capKey]?.label ?? capKey;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 className="text-base font-semibold text-slate-900">{label}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
          {data && (
            <div className="space-y-2">
              {data.leaderboard.map((entry) => (
                <button
                  key={entry.company_id}
                  onClick={() => { navigate(`/competitors/${entry.slug}`); onClose(); }}
                  className="w-full text-left rounded-lg border border-slate-100 bg-slate-50 hover:bg-slate-100 px-4 py-3 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 font-mono w-5">#{entry.rank}</span>
                      <span className="text-sm font-medium text-slate-900">{entry.company_name}</span>
                    </div>
                    <span className="text-base font-bold text-slate-700">{entry.score}</span>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <TierBadge tier={entry.tier} size="sm" />
                    <ConfidenceIndicator confidence={entry.confidence} />
                    <StrengthDeltaIndicator delta={entry.strength_delta} />
                    <span className="text-xs text-slate-400">momentum {entry.momentum_score}/5</span>
                  </div>
                  {entry.summary_reason && (
                    <p className="mt-2 text-xs text-slate-500 line-clamp-2">{entry.summary_reason}</p>
                  )}
                </button>
              ))}
              {data.leaderboard.length === 0 && (
                <p className="text-sm text-slate-400 text-center py-8">No benchmark data for this capability yet.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}