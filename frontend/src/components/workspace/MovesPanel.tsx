import { useState } from 'react';
import type { SignalFeedItem } from '../../types/intelligence';
import type { ScorecardTopMove } from '../../types/scorecard';
import MovementBadge from '../signals/MovementBadge';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

const CLASS_LABELS: Record<string, string> = {
  product_capability_move: 'Product',
  positioning_move: 'Positioning',
  ecosystem_move: 'Ecosystem',
  thought_leadership_signal: 'Thought Leadership',
  hiring_signal: 'Hiring',
  market_expansion_move: 'Expansion',
  weak_signal: 'Weak Signal',
};

function ScoreBadge({ score }: { score: number }) {
  const { bg, text, dot } =
    score >= 70
      ? { bg: 'rgba(139,92,246,0.15)', text: '#a78bfa', dot: '#8b5cf6' }
      : score >= 40
      ? { bg: 'rgba(59,130,246,0.15)', text: '#60a5fa', dot: '#3b82f6' }
      : { bg: 'rgba(100,116,139,0.15)', text: '#94a3b8', dot: '#64748b' };
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full font-medium px-2 py-0.5 text-[11px] flex-shrink-0"
      style={{ background: bg, color: text }}
    >
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: dot }} />
      {score}
    </span>
  );
}

interface Props {
  recentAssessments: SignalFeedItem[];
  topMoves: ScorecardTopMove[] | null | undefined;
  loading?: boolean;
  onSelectSignal: (signalId: string) => void;
  onSelectRecentSignal: (item: SignalFeedItem) => void;
}

export function MovesPanel({ recentAssessments, topMoves, loading, onSelectSignal, onSelectRecentSignal }: Props) {
  const [activeTab, setActiveTab] = useState<'recent' | 'top'>('recent');

  const sortedRecent = [...recentAssessments].sort((a, b) => {
    const da = new Date(a.published_at ?? a.created_at).getTime();
    const db = new Date(b.published_at ?? b.created_at).getTime();
    return db - da;
  });

  const newIds = new Set(sortedRecent.slice(0, 3).map((a) => a.id));

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex border-b border-slate-100 mb-3 -mx-1 flex-shrink-0">
        {(['recent', 'top'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 text-[12px] font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab
                ? 'border-indigo-500 text-indigo-700'
                : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {tab === 'recent' ? 'Recent Moves' : 'Top Moves'}
          </button>
        ))}
      </div>

      {/* Scrollable content — stays within sibling grid height */}
      <div className="flex-1 overflow-y-auto min-h-0">

      {/* Recent Moves tab */}
      {activeTab === 'recent' && (
        <>
          {sortedRecent.length === 0 ? (
            <p className="text-slate-400 text-[12px]">No recent moves</p>
          ) : (
            <ul className="space-y-3">
              {sortedRecent.slice(0, 15).map((item) => (
                <li
                  key={item.id}
                  className="cursor-pointer hover:bg-slate-50 -mx-2 px-2 py-1.5 rounded-lg transition-colors"
                  onClick={() => onSelectRecentSignal(item)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        {newIds.has(item.id) && (
                          <span className="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-600 border border-emerald-200 flex-shrink-0">
                            New
                          </span>
                        )}
                        <p className="text-[12px] text-slate-800 font-medium leading-snug line-clamp-2">
                          {item.title}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        {item.assessment?.capability_primary && (
                          <span className="text-[11px] text-slate-500">
                            {getCapabilityLabel(item.assessment.capability_primary)}
                          </span>
                        )}
                        <span className="text-[11px] text-slate-400">
                          {formatDistanceToNow(item.published_at ?? item.created_at)}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1 flex-shrink-0">
                      <MovementBadge strength={item.assessment?.movement_strength} size="sm" />
                      {item.assessment?.movement_score != null && (
                        <ScoreBadge score={item.assessment.movement_score} />
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {/* Top Moves tab */}
      {activeTab === 'top' && (
        <>
          {loading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-10 bg-slate-100 rounded" />
              ))}
            </div>
          ) : !topMoves || topMoves.length === 0 ? (
            <p className="text-slate-400 text-[12px]">No top moves recorded in this period.</p>
          ) : (
            <ul className="space-y-3">
              {topMoves.map((move) => (
                <li
                  key={move.assessment_id}
                  onClick={() => onSelectSignal(move.signal_id)}
                  className="cursor-pointer hover:bg-slate-50 -mx-2 px-2 py-1.5 rounded-lg transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-slate-800 font-medium leading-snug line-clamp-2">
                        {move.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[11px] text-slate-500">
                          {CLASS_LABELS[move.signal_class] ?? move.signal_class}
                        </span>
                        {move.assessed_at && (
                          <>
                            <span className="text-[11px] text-slate-300">·</span>
                            <span
                              className="text-[11px] text-slate-400"
                              title={new Date(move.assessed_at).toLocaleString('de-DE')}
                            >
                              bewertet {formatDistanceToNow(move.assessed_at)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <ScoreBadge score={move.movement_score} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      </div>
    </div>
  );
}
