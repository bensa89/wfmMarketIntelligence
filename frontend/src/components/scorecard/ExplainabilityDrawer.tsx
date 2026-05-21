import { X } from 'lucide-react';
import type { ScorecardExplain } from '../../types/scorecard';

const DIM_LABELS: Record<string, string> = {
  capability_strength: 'Capability Strength',
  market_impact: 'Market Impact',
  activity: 'Activity',
  customer_proof: 'Customer Proof',
  momentum: 'Momentum',
};

interface Props {
  open: boolean;
  onClose: () => void;
  explain: ScorecardExplain | null | undefined;
  loading?: boolean;
  error?: boolean;
}

export function ExplainabilityDrawer({ open, onClose, explain, loading, error }: Props) {
  if (!open) return null;

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-800">Why this score?</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {loading && (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-gray-100 rounded" />
              ))}
            </div>
          )}

          {error && !loading && (
            <p className="text-sm text-gray-500 italic">Explainability data unavailable for this period.</p>
          )}

          {explain && !loading && (
            <>
              {/* Overall score */}
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-indigo-700">
                  {explain.overall_score != null ? Math.round(explain.overall_score) : '—'}
                </span>
                <p className="text-sm text-gray-500">{explain.score_formula}</p>
              </div>

              {/* Null dimensions notice */}
              {explain.null_dimensions.length > 0 && (
                <p className="text-xs text-gray-400 italic">
                  Dimensions with no data (excluded from score):{' '}
                  {explain.null_dimensions.map((d) => DIM_LABELS[d] ?? d).join(', ')}
                </p>
              )}

              {/* Dimension breakdown */}
              <div className="space-y-4">
                {explain.dimension_breakdown.map((dim) => (
                  <div key={dim.dimension} className="border border-gray-100 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-semibold text-gray-700">
                        {DIM_LABELS[dim.dimension] ?? dim.dimension}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span>Score: <strong className="text-gray-800">{dim.score != null ? Math.round(dim.score) : '—'}</strong></span>
                        <span>
                          Weight:{' '}
                          <strong className="text-gray-800">
                            {(dim.dimension_weight * 100).toFixed(0)}%
                          </strong>
                          {dim.score == null && (
                            <span className="ml-1 text-gray-400">(excluded — no data)</span>
                          )}
                          {dim.score != null && dim.effective_weight !== dim.dimension_weight && (
                            <span className="ml-1 text-gray-400">→ {(dim.effective_weight * 100).toFixed(1)}% effective</span>
                          )}
                        </span>
                        <span>Contribution: <strong className="text-gray-800">
                          {dim.weighted_contribution != null ? Math.round(dim.weighted_contribution * 10) / 10 : '—'}
                        </strong></span>
                      </div>
                    </div>

                    {dim.top_contributing_assessments.length > 0 ? (
                      <ul className="space-y-1.5 mt-2">
                        {dim.top_contributing_assessments.map((a) => (
                          <li key={a.assessment_id} className="flex items-center justify-between gap-2 text-xs">
                            <span className="text-gray-700 truncate">{a.title}</span>
                            <span className="flex-shrink-0 text-indigo-600 font-medium">{a.movement_score}</span>
                          </li>
                        ))}
                        {dim.assessment_count > 5 && (
                          <li className="text-xs text-gray-400 italic">
                            …and {dim.assessment_count - 5} more
                          </li>
                        )}
                      </ul>
                    ) : (
                      <p className="text-xs text-gray-400 italic mt-2">No contributing assessments.</p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {explain && (
          <div className="px-6 py-3 border-t border-gray-100 text-xs text-gray-400 flex gap-4">
            <span>Routing: {explain.routing_version ?? '—'}</span>
            <span>Scorecard: {explain.scorecard_version ?? '—'}</span>
          </div>
        )}
      </div>
    </>
  );
}
