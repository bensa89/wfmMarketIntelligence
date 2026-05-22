import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useCompany } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useDocument } from '../hooks/useDocuments';
import { useDeduplicate } from '../hooks/useDeduplicate';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import MarkdownViewer from '../components/MarkdownViewer';
import type { DedupResult, SignalType } from '../types';
import { ArrowLeft, Merge, X, CheckCircle2, AlertCircle, RefreshCw as RefreshCwIcon } from 'lucide-react';
import { useScorecard, useScorecardExplain, useRecomputeScorecard } from '../hooks/useScorecard';
import { useCrawlStatus } from '../hooks/useCrawlStatus';
import { DimensionScoreGrid } from '../components/scorecard/DimensionScoreGrid';
import { CapabilityStrengthPanel } from '../components/scorecard/CapabilityStrengthPanel';
import { TopMovesTimeline } from '../components/scorecard/TopMovesTimeline';
import { RiskFlagsPanel } from '../components/scorecard/RiskFlagsPanel';
import { WatchpointsPanel } from '../components/scorecard/WatchpointsPanel';
import { ExplainabilityDrawer } from '../components/scorecard/ExplainabilityDrawer';
import type { ScorecardPeriodType } from '../types/scorecard';
import { RefreshCw, HelpCircle } from 'lucide-react';

export default function CompetitorDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: company, isLoading: companyLoading } = useCompany(slug!);
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: signals, isLoading: signalsLoading } = useSignals(
    company
      ? {
          company_id: company.id,
          signal_type: signalType || undefined,
          min_relevance: minRelevance || undefined,
          q: searchQuery || undefined,
        }
      : undefined,
  );

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const deduplicate = useDeduplicate();
  const [dedupResult, setDedupResult] = useState<DedupResult | null>(null);
  const [showDedupPanel, setShowDedupPanel] = useState(false);
  const [activeTab, setActiveTab] = useState<'signals' | 'scorecard'>('signals');
  const [scorecardPeriod, setScorecardPeriod] = useState<ScorecardPeriodType>('30d');
  const [explainOpen, setExplainOpen] = useState(false);

  const { data: scorecard, isLoading: scorecardLoading } = useScorecard(slug!, scorecardPeriod);
  const {
    data: explain,
    isLoading: explainLoading,
    isError: explainError,
  } = useScorecardExplain(slug!, scorecardPeriod, explainOpen);
  const recompute = useRecomputeScorecard(slug!);
  const crawl = useCrawlStatus();

  function handleDeduplicate() {
    if (!company) return;
    setDedupResult(null);
    setShowDedupPanel(true);
    deduplicate.mutate(
      { companyId: company.id },
      {
        onSuccess: (result) => {
          setDedupResult(result);
        },
        onError: () => {
          setShowDedupPanel(true);
        },
      },
    );
  }

  if (companyLoading) return <p className="text-ink-muted p-6">Loading...</p>;
  if (!company) return <p className="text-signal-low p-6">Company not found.</p>;

  return (
    <div className="p-6">
      <Link to="/competitors" className="text-sm text-accent-blue hover:underline flex items-center gap-1 mb-4">
        <ArrowLeft size={14} /> Back to list
      </Link>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">{company.name}</h1>
          <p className="text-sm text-ink-muted">
            {company.type === 'competitor' ? 'Competitor' : 'Market Source'}
            {company.website && ` · ${company.website}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => crawl.startCompany(slug!)}
            disabled={crawl.isRunning}
            className="btn-secondary flex items-center gap-2 disabled:opacity-40"
            title="Alle aktiven Sources crawlen"
          >
            <RefreshCwIcon size={16} className={crawl.isRunning ? 'animate-spin' : ''} />
            {crawl.isRunning ? 'Crawling...' : 'Refresh Sources'}
          </button>
          <button
            onClick={handleDeduplicate}
            disabled={deduplicate.isPending}
            className="btn-secondary flex items-center gap-2"
            title="Find and merge duplicate signals using AI"
          >
            <Merge size={16} />
            {deduplicate.isPending ? 'Analyzing...' : 'Deduplicate'}
          </button>
        </div>
      </div>
      {company.description && (
        <p className="text-sm text-ink-muted max-w-md mb-4">{company.description}</p>
      )}

      {showDedupPanel && (
        <div className="card mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Merge size={16} />
              Deduplicate Results
            </h3>
            <button onClick={() => setShowDedupPanel(false)} className="text-ink-muted hover:text-ink">
              <X size={16} />
            </button>
          </div>

          {deduplicate.isPending && (
            <div className="flex items-center gap-3 py-4">
              <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
              <div>
                <p className="text-sm font-medium">Analyzing signals for duplicates...</p>
                <p className="text-xs text-ink-muted mt-0.5">
                  The LLM is comparing all signals for {company.name}. This may take a moment.
                </p>
              </div>
            </div>
          )}

          {deduplicate.isError && (
            <div className="flex items-start gap-2 py-2">
              <AlertCircle size={18} className="text-signal-low shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-signal-low font-medium">Deduplication failed</p>
                <p className="text-xs text-ink-muted mt-0.5">{deduplicate.error.message}</p>
              </div>
            </div>
          )}

          {dedupResult && (
            <div>
              {dedupResult.merged_count === 0 ? (
                <div className="flex items-center gap-2 py-2">
                  <CheckCircle2 size={18} className="text-signal-high" />
                  <p className="text-sm">No duplicate signals found. All signals are unique.</p>
                </div>
              ) : (
                <div>
                  <div className="flex items-center gap-2 py-2">
                    <CheckCircle2 size={18} className="text-signal-high" />
                    <p className="text-sm font-medium">
                      Merged {dedupResult.merged_count} group{dedupResult.merged_count > 1 ? 's' : ''},
                      removed {dedupResult.removed_ids.length} duplicate{dedupResult.removed_ids.length > 1 ? 's' : ''}
                    </p>
                  </div>
                  {dedupResult.kept_signals.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-ink-muted mb-2">Kept signals:</p>
                      <div className="space-y-1.5">
                        {dedupResult.kept_signals.map((s) => (
                          <div key={s.id} className="flex items-center justify-between bg-app-bg/50 rounded px-3 py-1.5 text-sm">
                            <span className="truncate mr-3">{s.title}</span>
                            {s.relevance_score != null && (
                              <span className="text-xs text-ink-muted shrink-0">
                                relevance: {(s.relevance_score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {/* Tab bar */}
      <div className="flex border-b border-gray-200 mb-4">
        <button
          onClick={() => setActiveTab('signals')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'signals'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Signals
        </button>
        <button
          onClick={() => setActiveTab('scorecard')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'scorecard'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Scorecard
        </button>
      </div>

      {activeTab === 'signals' && (
        <>
          <FilterBar
            signalType={signalType}
            onSignalTypeChange={setSignalType}
            minRelevance={minRelevance}
            onMinRelevanceChange={setMinRelevance}
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
          />
          {signalsLoading ? (
            <p className="text-ink-muted">Loading signals...</p>
          ) : (
            <div className="space-y-4">
              {signals?.map((signal) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  onClick={signal.document_id ? () => setSelectedDocId(signal.document_id) : undefined}
                />
              ))}
              {signals?.length === 0 && (
                <p className="text-ink-muted">No signals found for this company.</p>
              )}
            </div>
          )}
        </>
      )}

      {activeTab === 'scorecard' && (
        <div>
          {/* Top bar */}
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            {/* Period selector */}
            <div className="flex items-center gap-2">
              {(['30d', '90d', '180d'] as ScorecardPeriodType[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setScorecardPeriod(p)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    scorecardPeriod === p
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              {scorecard && (
                <span className="text-xs text-gray-400">
                  Last updated {new Date(scorecard.generated_at).toLocaleDateString()}
                </span>
              )}
              <button
                onClick={() => setExplainOpen(true)}
                disabled={!scorecard}
                className="flex items-center gap-1 px-3 py-1.5 text-sm rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-40"
              >
                <HelpCircle className="w-4 h-4" />
                Why this score?
              </button>
              <button
                onClick={() => recompute.mutate()}
                disabled={recompute.isPending}
                className="flex items-center gap-1 px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                <RefreshCw className={`w-4 h-4 ${recompute.isPending ? 'animate-spin' : ''}`} />
                {recompute.isPending ? 'Recomputing…' : 'Recompute'}
              </button>
            </div>
          </div>

          {/* No scorecard state */}
          {!scorecardLoading && !scorecard && (
            <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
              <p className="text-sm text-gray-500">
                No scorecard available for this period. Scorecards are generated automatically when new
                signals are analysed. You can also trigger a manual recompute above.
              </p>
            </div>
          )}

          {/* Scorecard content */}
          {(scorecardLoading || scorecard) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left column */}
              <div className="space-y-4">
                <DimensionScoreGrid
                  dimensionScores={scorecard?.dimension_scores}
                  loading={scorecardLoading}
                />
                <RiskFlagsPanel flags={scorecard?.risk_flags} loading={scorecardLoading} />
              </div>

              {/* Right column */}
              <div className="space-y-4">
                <CapabilityStrengthPanel scorecard={scorecard} loading={scorecardLoading} />
                <TopMovesTimeline moves={scorecard?.top_moves} loading={scorecardLoading} />
                <WatchpointsPanel watchpoints={scorecard?.watchpoints} loading={scorecardLoading} />
              </div>
            </div>
          )}

          {/* Explainability drawer */}
          <ExplainabilityDrawer
            open={explainOpen}
            onClose={() => setExplainOpen(false)}
            explain={explain}
            loading={explainLoading}
            error={explainError}
          />
        </div>
      )}

      {selectedDocId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={() => setSelectedDocId(null)}>
          <div className="card max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Source Document</h3>
              <button onClick={() => setSelectedDocId(null)} className="text-ink-muted hover:text-ink">Close</button>
            </div>
            <DocumentViewer documentId={selectedDocId} />
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentViewer({ documentId }: { documentId: string }) {
  const { data: doc, isLoading } = useDocument(documentId);
  if (isLoading) return <p className="text-ink-muted">Loading document...</p>;
  if (!doc) return <p className="text-signal-low">Document not found.</p>;

  return (
    <div>
      <h4 className="font-medium mb-2">{doc.title || 'Untitled'}</h4>
      <p className="text-xs text-ink-muted mb-4">
        Crawled: {new Date(doc.crawled_at).toLocaleDateString('de-DE')} ·{' '}
        <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-accent-blue hover:underline">Original URL</a>
      </p>
      {doc.content_markdown ? (
        <MarkdownViewer content={doc.content_markdown} />
      ) : (
        <p className="text-ink-muted">No markdown content available.</p>
      )}
    </div>
  );
}
