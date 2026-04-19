import { useState, useMemo } from 'react';
import { Search, CheckCircle, XCircle, ExternalLink, ChevronDown, ChevronRight, Filter } from 'lucide-react';
import {
  useRunSearchAll,
  useSearchRuns,
  useSearchResults,
  useSourceCandidates,
  useApproveCandidate,
  useRejectCandidate,
} from '../hooks/useSearch';
import { useCompanies } from '../hooks/useCompanies';
import type { SearchRun, SourceCandidate, SourceType } from '../types';

type Tab = 'runs' | 'candidates';

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    done: 'bg-green-900/40 text-green-400',
    running: 'bg-yellow-900/40 text-yellow-400',
    error: 'bg-red-900/40 text-red-400',
    pending: 'bg-app-card text-ink-muted',
    fetched: 'bg-blue-900/40 text-blue-400',
    skipped: 'bg-app-card text-ink-muted',
    candidate: 'bg-yellow-900/40 text-yellow-400',
    approved: 'bg-green-900/40 text-green-400',
    rejected: 'bg-red-900/40 text-red-400',
    monitored: 'bg-blue-900/40 text-blue-400',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${colors[status] ?? 'bg-app-card text-ink-muted'}`}>
      {status}
    </span>
  );
}

function RelevanceBadge({ score }: { score: number | null }) {
  if (score == null) return null;
  const percentage = Math.round(score * 100);
  let colorClass = 'bg-app-card text-ink-muted';
  if (percentage >= 80) colorClass = 'bg-green-900/40 text-green-400';
  else if (percentage >= 60) colorClass = 'bg-yellow-900/40 text-yellow-400';
  else if (percentage >= 40) colorClass = 'bg-orange-900/40 text-orange-400';

  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${colorClass}`}>
      {percentage}%
    </span>
  );
}

function SearchRunRow({ run }: { run: SearchRun }) {
  const [expanded, setExpanded] = useState(false);
  const { data: results } = useSearchResults(expanded ? run.id : undefined);

  return (
    <div className="border border-app-border rounded mb-2">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-app-bg transition-colors text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={16} className="text-ink-muted" /> : <ChevronRight size={16} className="text-ink-muted" />}
        <span className="text-sm text-ink flex-1">
          {run.query?.query_text ?? run.search_query_id}
        </span>
        <span className="text-xs text-ink-muted mr-3">
          {run.query?.search_intent}
        </span>
        <span className="text-xs text-ink-muted mr-3">
          {run.result_count ?? 0} results
        </span>
        <StatusBadge status={run.status} />
        <span className="text-xs text-ink-muted ml-3">
          {new Date(run.executed_at).toLocaleDateString()}
        </span>
      </button>

      {expanded && results && (
        <div className="border-t border-app-border divide-y divide-app-border">
          {results.length === 0 && (
            <p className="px-6 py-3 text-sm text-ink-muted">No results</p>
          )}
          {results.map(r => (
            <div key={r.id} className="px-6 py-2 flex items-start gap-4">
              <StatusBadge status={r.processing_status} />
              <div className="flex-1 min-w-0">
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-accent-blue hover:underline flex items-center gap-1"
                >
                  {r.title || r.url}
                  <ExternalLink size={12} />
                </a>
                {r.snippet && (
                  <p className="text-xs text-ink-muted mt-0.5 line-clamp-2">{r.snippet}</p>
                )}
              </div>
              {r.relevance_score != null && (
                <span className="text-xs text-ink-muted shrink-0">
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
      <div className="bg-app-card border border-app-border rounded-lg p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold text-ink mb-4">Approve Source Candidate</h2>
        <p className="text-sm text-ink-muted mb-4">{candidate.domain}</p>

        <div className="mb-4">
          <label className="block text-sm text-ink-muted mb-1">Label</label>
          <input
            className="w-full bg-app-bg border border-app-border rounded px-3 py-2 text-ink text-sm"
            value={label}
            onChange={e => setLabel(e.target.value)}
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm text-ink-muted mb-1">Source Type</label>
          <select
            className="w-full bg-app-bg border border-app-border rounded px-3 py-2 text-ink text-sm"
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
            className="px-4 py-2 text-sm text-ink-muted hover:text-ink transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            disabled={approve.isPending}
            className="px-4 py-2 text-sm bg-accent-blue text-ink rounded hover:opacity-90 disabled:opacity-50 transition-opacity"
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
  const [minRelevance, setMinRelevance] = useState<number>(0);
  const [approving, setApproving] = useState<SourceCandidate | null>(null);
  const [expandedCompanies, setExpandedCompanies] = useState<Set<string>>(new Set());

  const { data: candidates, isLoading } = useSourceCandidates(statusFilter || undefined);
  const { data: companies } = useCompanies();
  const reject = useRejectCandidate();

  // Group candidates by company and sort by relevance
  const groupedCandidates = useMemo(() => {
    if (!candidates) return [];

    // Filter by minimum relevance
    const filtered = candidates.filter(c =>
      (c.relevance_score ?? 0) >= minRelevance
    );

    // Sort by relevance descending
    const sorted = [...filtered].sort((a, b) =>
      (b.relevance_score ?? 0) - (a.relevance_score ?? 0)
    );

    // Group by company
    const groups = new Map<string, { companyName: string; candidates: SourceCandidate[] }>();

    sorted.forEach(candidate => {
      const companyId = candidate.company_id ?? 'unknown';
      const company = companies?.find(c => c.id === companyId);
      const companyName = company?.name ?? 'Unknown Company';

      if (!groups.has(companyId)) {
        groups.set(companyId, { companyName, candidates: [] });
      }
      groups.get(companyId)!.candidates.push(candidate);
    });

    // Sort groups by company name
    return Array.from(groups.entries())
      .sort(([, a], [, b]) => a.companyName.localeCompare(b.companyName));
  }, [candidates, companies, minRelevance]);

  const toggleCompany = (companyId: string) => {
    setExpandedCompanies(prev => {
      const next = new Set(prev);
      if (next.has(companyId)) {
        next.delete(companyId);
      } else {
        next.add(companyId);
      }
      return next;
    });
  };

  const totalCount = candidates?.length ?? 0;
  const filteredCount = groupedCandidates.reduce((sum, [, group]) => sum + group.candidates.length, 0);

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-app-bg rounded-lg border border-app-border">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-ink-muted" />
          <span className="text-sm text-ink-muted">Filters:</span>
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-ink-muted">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2 py-1 text-sm bg-app-card border border-app-border rounded text-ink"
          >
            <option value="candidate">Candidate</option>
            <option value="monitored">Monitored</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="">All</option>
          </select>
        </div>

        {/* Relevance Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-ink-muted">Min Relevance:</span>
          <select
            value={minRelevance}
            onChange={(e) => setMinRelevance(Number(e.target.value))}
            className="px-2 py-1 text-sm bg-app-card border border-app-border rounded text-ink"
          >
            <option value={0}>All</option>
            <option value={0.5}>50%</option>
            <option value={0.7}>70%</option>
            <option value={0.9}>90%</option>
          </select>
        </div>

        <div className="ml-auto text-xs text-ink-muted">
          Showing {filteredCount} of {totalCount}
        </div>
      </div>

      {isLoading && <p className="text-ink-muted text-sm">Loading…</p>}
      {!isLoading && groupedCandidates.length === 0 && (
        <p className="text-ink-muted text-sm">No candidates found.</p>
      )}

      {/* Grouped Candidates */}
      <div className="space-y-3">
        {groupedCandidates.map(([companyId, { companyName, candidates: companyCandidates }]) => (
          <div key={companyId} className="border border-app-border rounded-lg overflow-hidden">
            {/* Company Header */}
            <button
              onClick={() => toggleCompany(companyId)}
              className="w-full flex items-center gap-3 px-4 py-3 bg-app-bg/50 hover:bg-app-bg transition-colors text-left"
            >
              {expandedCompanies.has(companyId) ? (
                <ChevronDown size={18} className="text-ink-muted" />
              ) : (
                <ChevronRight size={18} className="text-ink-muted" />
              )}
              <span className="font-medium text-ink">{companyName}</span>
              <span className="text-xs text-ink-muted bg-app-card px-2 py-0.5 rounded-full">
                {companyCandidates.length}
              </span>
            </button>

            {/* Candidates List */}
            {expandedCompanies.has(companyId) && (
              <div className="divide-y divide-app-border">
                {companyCandidates.map(c => (
                  <div key={c.id} className="px-4 py-3 hover:bg-app-bg/30 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium text-ink">{c.domain}</span>
                          <StatusBadge status={c.status} />
                          <RelevanceBadge score={c.relevance_score} />
                        </div>
                        {c.title && <p className="text-xs text-ink-muted mb-1">{c.title}</p>}
                        {c.snippet && (
                          <p className="text-xs text-ink-muted line-clamp-2">{c.snippet}</p>
                        )}
                        {c.found_via_query && (
                          <p className="text-xs text-ink-muted/60 mt-1">via: {c.found_via_query}</p>
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
            )}
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
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink">Web Search</h1>
          <p className="text-ink-muted text-sm mt-1">AI-driven search for news, reports, and new sources</p>
        </div>
        <button
          onClick={() => runSearch.mutate()}
          disabled={runSearch.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-accent-blue text-ink rounded hover:opacity-90 disabled:opacity-50 transition-opacity text-sm"
        >
          <Search size={16} />
          {runSearch.isPending ? 'Searching…' : 'Search Run starten'}
        </button>
      </div>

      <div className="flex gap-1 mb-6 border-b border-app-border">
        {(['runs', 'candidates'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-accent-blue text-accent-blue'
                : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            {t === 'runs' ? 'Search Runs' : 'Source Candidates'}
          </button>
        ))}
      </div>

      {tab === 'runs' && (
        <div>
          {runsLoading && <p className="text-ink-muted text-sm">Loading…</p>}
          {!runsLoading && (!runs || runs.length === 0) && (
            <p className="text-ink-muted text-sm">No search runs yet. Click "Search Run starten" to begin.</p>
          )}
          {runs?.map(run => <SearchRunRow key={run.id} run={run} />)}
        </div>
      )}

      {tab === 'candidates' && <CandidatesTab />}
    </div>
  );
}
