import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRun, CrawlRunSourceState } from '../types';

function formatMs(ms: number | undefined): string {
  if (ms == null) return '\u2014';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

function TimingBar({ timings }: { timings: Record<string, number | undefined> }) {
  const steps = [
    { key: 'fetch_ms', label: 'Fetch', color: 'bg-blue-400' },
    { key: 'extract_ms', label: 'Extract', color: 'bg-green-400' },
    { key: 'analyse_ms', label: 'Analyse', color: 'bg-purple-400' },
    { key: 'discover_ms', label: 'Discover', color: 'bg-yellow-400' },
  ];

  const total = steps.reduce((s, st) => s + (timings[st.key] ?? 0), 0);
  if (total === 0) return null;

  return (
    <div className="flex h-4 rounded overflow-hidden bg-app-card">
      {steps.map((st) => {
        const ms = timings[st.key] ?? 0;
        const pct = total > 0 ? (ms / total) * 100 : 0;
        return pct > 0.5 ? (
          <div
            key={st.key}
            className={`${st.color} flex items-center justify-center text-[10px] text-white font-medium`}
            style={{ width: `${pct}%` }}
            title={`${st.label}: ${formatMs(ms)}`}
          >
            {pct > 12 ? formatMs(ms) : ''}
          </div>
        ) : null;
      })}
    </div>
  );
}

export default function CrawlRunDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: crawlRun, isLoading, error } = useQuery({
    queryKey: ['crawlRuns', id],
    queryFn: () => apiGet<CrawlRun>(`/crawl-runs/${id}`),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-6 text-ink-muted">Loading...</div>;
  if (error) return <div className="p-6 text-red-400">Error: {error.message}</div>;
  if (!crawlRun) return <div className="p-6 text-ink-muted">Crawl run not found</div>;

  const statusColors: Record<string, string> = {
    running: 'bg-blue-500/20 text-blue-400',
    completed: 'bg-green-500/20 text-green-400',
    failed: 'bg-red-500/20 text-red-400',
    cancelled: 'bg-gray-500/20 text-gray-400',
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold text-ink mb-4">Crawl Run Detail</h1>

      <div className="bg-app-card rounded-lg p-4 mb-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-ink-muted">Status</span>
          <div>
            <span className={`px-1.5 py-0.5 rounded text-xs ${statusColors[crawlRun.status] ?? ''}`}>
              {crawlRun.status}
            </span>
          </div>
        </div>
        <div>
          <span className="text-ink-muted">Started</span>
          <div>{new Date(crawlRun.started_at).toLocaleString()}</div>
        </div>
        <div>
          <span className="text-ink-muted">New / Skipped</span>
          <div>{crawlRun.total_new} / {crawlRun.total_skipped}</div>
        </div>
        <div>
          <span className="text-ink-muted">Errors</span>
          <div>{crawlRun.total_errors}</div>
        </div>
      </div>

      <h2 className="text-lg font-medium text-ink mb-3">Sources</h2>
      <div className="space-y-2">
        {crawlRun.sources.map((src: CrawlRunSourceState) => {
          const timings: Record<string, number | undefined> = {
            fetch_ms: src.fetch_ms ?? undefined,
            extract_ms: src.extract_ms ?? undefined,
            analyse_ms: src.analyse_ms ?? undefined,
            discover_ms: src.discover_ms ?? undefined,
          };
          const totalMs = (src.fetch_ms ?? 0) + (src.extract_ms ?? 0) + (src.analyse_ms ?? 0) + (src.discover_ms ?? 0);
          return (
            <div key={src.source_id} className="bg-app-card rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-ink truncate" title={src.url}>
                  {(() => { try { return new URL(src.url).hostname; } catch { return src.url; } })()}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${statusColors[src.status] ?? ''}`}>
                  {src.status}
                </span>
              </div>
              {totalMs > 0 && <TimingBar timings={timings} />}
              <div className="flex gap-4 text-xs text-ink-muted mt-2">
                {src.fetch_ms != null && <span>Fetch {formatMs(src.fetch_ms)}</span>}
                {src.extract_ms != null && <span>Extract {formatMs(src.extract_ms)}</span>}
                {src.analyse_ms != null && <span>Analyse {formatMs(src.analyse_ms)}</span>}
                {src.discover_ms != null && <span>Discover {formatMs(src.discover_ms)}</span>}
                {totalMs > 0 && <span>Total {formatMs(totalMs)}</span>}
              </div>
              <div className="flex gap-3 text-xs text-ink-muted mt-1">
                <span>{src.new_documents} new</span>
                <span>{src.skipped} skipped</span>
                {src.errors > 0 && <span className="text-red-400">{src.errors} errors</span>}
                {src.error_message && <span className="text-red-400 truncate" title={src.error_message}>{src.error_message}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}