import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ExternalLink, RefreshCw, HelpCircle } from 'lucide-react';
import { useCompetitorWorkspace } from '../hooks/useCompetitorWorkspace';
import { useSummarizeCompetitor } from '../hooks/useSummarizeCompetitor';
import { ApiError } from '../api/client';
import StrategicPostureCard from '../components/workspace/StrategicPostureCard';
import CapabilityRadar from '../components/workspace/CapabilityRadar';
import { RelativeCapabilityStrengthPanel } from '../components/workspace/RelativeCapabilityStrengthPanel';
import RecentMovesTimeline from '../components/workspace/RecentMovesTimeline';
import RisksOpportunitiesCards from '../components/workspace/RisksOpportunitiesCards';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import type { SignalFeedItem } from '../types/intelligence';
import { useScorecard, useScorecardExplain, useRecomputeScorecard } from '../hooks/useScorecard';
import { DimensionScoreGrid } from '../components/scorecard/DimensionScoreGrid';
import { TopMovesTimeline } from '../components/scorecard/TopMovesTimeline';
import { ExplainabilityDrawer } from '../components/scorecard/ExplainabilityDrawer';
import { ScorecardSignalDrawer } from '../components/scorecard/ScorecardSignalDrawer';

type Period = '30d' | '90d';

export default function CompetitorWorkspacePage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, isLoading, error } = useCompetitorWorkspace(slug ?? '');
  const [activePeriod, setActivePeriod] = useState<Period>('30d');
  const [selectedSignal, setSelectedSignal] = useState<SignalFeedItem | null>(null);
  const [selectedScorecardSignalId, setSelectedScorecardSignalId] = useState<string | null>(null);
  const [explainOpen, setExplainOpen] = useState(false);

  const summarize = useSummarizeCompetitor(data?.competitor_profile.id ?? '');
  const { data: scorecard, isLoading: scorecardLoading } = useScorecard(slug ?? '', activePeriod);
  const { data: explain, isLoading: explainLoading, isError: explainError } = useScorecardExplain(slug ?? '', activePeriod, explainOpen);
  const recompute = useRecomputeScorecard(slug ?? '');

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-slate-500 text-sm">Loading competitor workspace…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-red-400 text-sm">Competitor not found or failed to load.</span>
      </div>
    );
  }

  const activeSummary = activePeriod === '30d' ? data.summary_30d : data.summary_90d;

  function handleSignalSelect(signalId: string) {
    setSelectedScorecardSignalId(signalId);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">{data.competitor_profile.name}</h1>
            {data.competitor_profile.description && (
              <p className="text-[12px] text-slate-500 mt-0.5">{data.competitor_profile.description}</p>
            )}
            {data.competitor_profile.website && (
              <a
                href={data.competitor_profile.website}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700 mt-1 transition-colors"
              >
                <ExternalLink size={10} />
                {data.competitor_profile.website}
              </a>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
            {/* Period selector */}
            {(['30d', '90d'] as Period[]).map((p) => (
              <button
                key={p}
                onClick={() => setActivePeriod(p)}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors border ${
                  activePeriod === p
                    ? 'bg-blue-50 text-blue-700 border-blue-200'
                    : 'text-slate-500 hover:text-slate-700 border-transparent'
                }`}
              >
                {p === '30d' ? '30 Days' : '90 Days'}
                {p === '30d' && !data.summary_30d && <span className="text-[10px] text-slate-400 ml-1">(no data)</span>}
                {p === '90d' && !data.summary_90d && <span className="text-[10px] text-slate-400 ml-1">(no data)</span>}
              </button>
            ))}

            <div className="w-px h-5 bg-slate-200" />

            {scorecard && (
              <span className="text-[11px] text-slate-400">
                Updated {new Date(scorecard.generated_at).toLocaleDateString()}
              </span>
            )}

            <button
              onClick={() => { summarize.mutate(activePeriod); recompute.mutate(); }}
              disabled={summarize.isPending || recompute.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-white border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={13} className={(summarize.isPending || recompute.isPending) ? 'animate-spin' : ''} />
              Refresh
            </button>

          </div>
        </div>

        {(summarize.isError || summarize.isSuccess) && (
          <div className="mt-1.5">
            {summarize.isError && (
              <span className="text-[11px] text-red-500">
                {summarize.error instanceof ApiError ? summarize.error.message : 'Summary generation failed'}
              </span>
            )}
            {summarize.isSuccess && (
              <span className="text-[11px] text-green-600">Summary updated</span>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto px-6 py-5 space-y-5">

        {/* Row 1: Strategic posture + Dimension scores (KPIs) */}
        <div className="grid grid-cols-2 gap-4">
          <StrategicPostureCard summary={activeSummary} />
          <div className="space-y-3">
            <DimensionScoreGrid
              dimensionScores={scorecard?.dimension_scores}
              loading={scorecardLoading}
              slot={
                <button
                  onClick={() => setExplainOpen(true)}
                  disabled={!scorecard}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-white border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-40 w-full justify-center"
                >
                  <HelpCircle size={12} />
                  Why this score?
                </button>
              }
            />
          </div>
        </div>

        {/* Row 2: Relative capability strength + Capability activity */}
        <div className="grid grid-cols-2 gap-4">
          <RelativeCapabilityStrengthPanel slug={slug ?? ''} />
          <CapabilityRadar distribution={data.capability_distribution} />
        </div>

        {/* Row 3: Risks, Opportunities, Watchpoints */}
        <RisksOpportunitiesCards
          summary={activeSummary}
          scorecardWatchpoints={scorecard?.watchpoints}
          onSelectSignal={handleSignalSelect}
        />

        {/* Row 4: Top moves (scorecard) */}
        <TopMovesTimeline moves={scorecard?.top_moves} loading={scorecardLoading} onSelect={handleSignalSelect} />

        {/* Row 5: Recent signal timeline */}
        <RecentMovesTimeline
          assessments={data.recent_assessments}
          onSelectSignal={setSelectedSignal}
        />

      </div>

      {/* Drawers */}
      <ExplainabilityDrawer
        open={explainOpen}
        onClose={() => setExplainOpen(false)}
        explain={explain}
        loading={explainLoading}
        error={explainError}
      />
      <ScorecardSignalDrawer
        signalId={selectedScorecardSignalId}
        onClose={() => setSelectedScorecardSignalId(null)}
      />
      {selectedSignal && (
        <SignalDetailDrawer
          item={selectedSignal}
          onClose={() => setSelectedSignal(null)}
        />
      )}
    </div>
  );
}
