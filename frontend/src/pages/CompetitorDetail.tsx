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
import { ArrowLeft, Merge, X, CheckCircle2, AlertCircle } from 'lucide-react';

export default function CompetitorDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: company, isLoading: companyLoading } = useCompany(slug!);
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);

  const { data: signals, isLoading: signalsLoading } = useSignals(
    company
      ? {
          company_id: company.id,
          signal_type: signalType || undefined,
          min_relevance: minRelevance || undefined,
        }
      : undefined,
  );

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const deduplicate = useDeduplicate();
  const [dedupResult, setDedupResult] = useState<DedupResult | null>(null);
  const [showDedupPanel, setShowDedupPanel] = useState(false);

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
      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
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
