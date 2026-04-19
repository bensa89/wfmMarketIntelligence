import { useState } from 'react';
import { Search, CheckCircle, XCircle, ExternalLink, ChevronDown, ChevronRight } from 'lucide-react';
import {
  useRunSearchAll,
  useSearchRuns,
  useSearchResults,
  useSourceCandidates,
  useApproveCandidate,
  useRejectCandidate,
} from '../hooks/useSearch';
import type { SearchRun, SourceCandidate, SourceType } from '../types';

type Tab = 'runs' | 'candidates';

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    done: 'bg-green-900/40 text-green-400',
    running: 'bg-yellow-900/40 text-yellow-400',
    error: 'bg-red-900/40 text-red-400',
    pending: 'bg-gray-700 text-gray-400',
    fetched: 'bg-blue-900/40 text-blue-400',
    skipped: 'bg-gray-700 text-gray-400',
    candidate: 'bg-yellow-900/40 text-yellow-400',
    approved: 'bg-green-900/40 text-green-400',
    rejected: 'bg-red-900/40 text-red-400',
    monitored: 'bg-blue-900/40 text-blue-400',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${colors[status] ?? 'bg-gray-700 text-gray-400'}`}>
      {status}
    </span>
  );
}

function SearchRunRow({ run }: { run: SearchRun }) {
  const [expanded, setExpanded] = useState(false);
  const { data: results } = useSearchResults(expanded ? run.id : undefined);

  return (
    <div className="border border-dark-border rounded mb-2">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-dark-bg transition-colors text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={16} className="text-dark-muted" /> : <ChevronRight size={16} className="text-dark-muted" />}
        <span className="text-sm text-dark-text flex-1">
          {run.query?.query_text ?? run.search_query_id}
        </span>
        <span className="text-xs text-dark-muted mr-3">
          {run.query?.search_intent}
        </span>
        <span className="text-xs text-dark-muted mr-3">
          {run.result_count ?? 0} results
        </span>
        <StatusBadge status={run.status} />
        <span className="text-xs text-dark-muted ml-3">
          {new Date(run.executed_at).toLocaleDateString()}
        </span>
      </button>

      {expanded && results && (
        <div className="border-t border-dark-border divide-y divide-dark-border">
          {results.length === 0 && (
            <p className="px-6 py-3 text-sm text-dark-muted">No results</p>
          )}
          {results.map(r => (
            <div key={r.id} className="px-6 py-2 flex items-start gap-4">
              <StatusBadge status={r.processing_status} />
              <div className="flex-1 min-w-0">
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-dark-accent hover:underline flex items-center gap-1"
                >
                  {r.title || r.url}
                  <ExternalLink size={12} />
                </a>
                {r.snippet && (
                  <p className="text-xs text-dark-muted mt-0.5 line-clamp-2">{r.snippet}</p>
                )}
              </div>
              {r.relevance_score != null && (
                <span className="text-xs text-dark-muted shrink-0">
                  {(r.relevance_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ApproveCandidateDialog({
  candidate,
  onClose,
}: {
  candidate: SourceCandidate;
  onClose: () => void;
}) {
  const [label, setLabel] = useState(candidate.title ?? candidate.domain);
  const [sourceType, setSourceType] = useState<SourceType>(
    (candidate.source_type_guess as SourceType) ?? 'news'
  );
  const approve = useApproveCandidate();

  function handleApprove() {
    approve.mutate(
      { id: candidate.id, body: { label, source_type: sourceType } },
      { onSuccess: onClose }
    );
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-dark-card border border-dark-border rounded-lg p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold text-dark-text mb-4">Approve Source Candidate</h2>
        <p className="text-sm text-dark-muted mb-4">{candidate.domain}</p>

        <div className="mb-4">
          <label className="block text-sm text-dark-muted mb-1">Label</label>
          <input
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-dark-text text-sm"
            value={label}
            onChange={e => setLabel(e.target.value)}
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm text-dark-muted mb-1">Source Type</label>
          <select
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-dark-text text-sm"
            value={sourceType}
            onChange={e => setSourceType(e.target.value as SourceType)}
          >
            {(['news', 'blog', 'product', 'press', 'jobs'] as SourceType[]).map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-dark-muted hover:text-dark-text transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            disabled={approve.isPending}
            className="px-4 py-2 text-sm bg-dark-accent text-white rounded hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {approve.isPending ? 'Approving…' : 'Approve & Add Source'}
          </button>
        </div>
      </div>
    </div>
  );
}

function CandidatesTab() {
  const [statusFilter, setStatusFilter] = useState<string>('candidate');
  const [approving, setApproving] = useState<SourceCandidate | null>(null);
  const { data: candidates, isLoading } = useSourceCandidates(statusFilter || undefined);
  const reject = useRejectCandidate();

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {['candidate', 'approved', 'rejected', ''].map(s => (
          <button
            key={s || 'all'}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              statusFilter === s
                ? 'bg-dark-accent/20 text-dark-accent border border-dark-accent/40'
                : 'text-dark-muted hover:text-dark-text border border-dark-border'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-dark-muted text-sm">Loading…</p>}
      {!isLoading && (!candidates || candidates.length === 0) && (
        <p className="text-dark-muted text-sm">No candidates found.</p>
      )}

      <div className="space-y-2">
        {candidates?.map(c => (
          <div key={c.id} className="bg-dark-card border border-dark-border rounded p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-dark-text">{c.domain}</span>
                  <StatusBadge status={c.status} />
                  {c.relevance_score != null && (
                    <span className="text-xs text-dark-muted">
                      {(c.relevance_score * 100).toFixed(0)}% relevance
                    </span>
                  )}
                </div>
                {c.title && <p className="text-xs text-dark-muted mb-1">{c.title}</p>}
                {c.snippet && (
                  <p className="text-xs text-dark-muted line-clamp-2">{c.snippet}</p>
                )}
                {c.found_via_query && (
                  <p className="text-xs text-dark-muted/60 mt-1">via: {c.found_via_query}</p>
                )}
              </div>
              {c.status === 'candidate' && (
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => setApproving(c)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-green-900/30 text-green-400 border border-green-800/50 rounded hover:bg-green-900/50 transition-colors"
                  >
                    <CheckCircle size={13} />
                    Approve
                  </button>
                  <button
                    onClick={() => reject.mutate(c.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-900/30 text-red-400 border border-red-800/50 rounded hover:bg-red-900/50 transition-colors"
                  >
                    <XCircle size={13} />
                    Reject
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {approving && (
        <ApproveCandidateDialog candidate={approving} onClose={() => setApproving(null)} />
      )}
    </div>
  );
}

export default function SearchPage() {
  const [tab, setTab] = useState<Tab>('runs');
  const runSearch = useRunSearchAll();
  const { data: runs, isLoading: runsLoading } = useSearchRuns();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-dark-text">Web Search</h1>
          <p className="text-dark-muted text-sm mt-1">AI-driven search for news, reports, and new sources</p>
        </div>
        <button
          onClick={() => runSearch.mutate()}
          disabled={runSearch.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-dark-accent text-white rounded hover:opacity-90 disabled:opacity-50 transition-opacity text-sm"
        >
          <Search size={16} />
          {runSearch.isPending ? 'Searching…' : 'Search Run starten'}
        </button>
      </div>

      <div className="flex gap-1 mb-6 border-b border-dark-border">
        {(['runs', 'candidates'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-dark-accent text-dark-accent'
                : 'border-transparent text-dark-muted hover:text-dark-text'
            }`}
          >
            {t === 'runs' ? 'Search Runs' : 'Source Candidates'}
          </button>
        ))}
      </div>

      {tab === 'runs' && (
        <div>
          {runsLoading && <p className="text-dark-muted text-sm">Loading…</p>}
          {!runsLoading && (!runs || runs.length === 0) && (
            <p className="text-dark-muted text-sm">No search runs yet. Click "Search Run starten" to begin.</p>
          )}
          {runs?.map(run => <SearchRunRow key={run.id} run={run} />)}
        </div>
      )}

      {tab === 'candidates' && <CandidatesTab />}
    </div>
  );
}
