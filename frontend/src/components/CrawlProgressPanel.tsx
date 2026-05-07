import { X, Check, AlertCircle, Loader2, Minus } from 'lucide-react';
import type { CrawlStatusRun, CrawlStatusSource, CrawlStatusQueuedRun, CrawlPhase } from '../types';

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function SourceRow({ source }: { source: CrawlStatusSource }) {
  const isRunning = source.status === 'running' || source.status === 'analysing';
  const isDone = source.status === 'completed';
  const isError = source.status === 'failed';

  let detail = 'Waiting...';
  if (source.status === 'analysing') {
    detail = source.analyse_docs_total > 0
      ? `Analysiere ${source.analyse_docs_done}/${source.analyse_docs_total}${source.analyse_current_url ? ` — ${source.analyse_current_url}` : ''}`
      : 'Analysiere...';
  } else if (source.status === 'running' && source.current_step) {
    const labels: Record<string, string> = {
      fetching: 'Fetching...',
      extracting: 'Extracting...',
      discovering: source.discover_pages_crawled != null
        ? `Discovering ${source.discover_pages_crawled} Seiten`
        : 'Discovering...',
    };
    detail = labels[source.current_step] ?? source.current_step;
  } else if (isDone) {
    const parts: string[] = [];
    if (source.fetch_ms) parts.push(`fetch ${formatMs(source.fetch_ms)}`);
    if (source.extract_ms) parts.push(`extract ${formatMs(source.extract_ms)}`);
    if (source.discover_ms) parts.push(`discover ${formatMs(source.discover_ms)}`);
    if (source.analyse_ms) parts.push(`analyse ${formatMs(source.analyse_ms)}`);
    detail = parts.length > 0
      ? parts.join(' · ')
      : `${source.new_documents} new · ${source.skipped} skipped`;
  } else if (isError) {
    detail = source.error_message ?? 'Error';
  }

  return (
    <div className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0">
      <span className="w-4 flex-shrink-0 flex justify-center">
        {isDone ? (
          <Check className="w-3.5 h-3.5 text-signal-high" />
        ) : isError ? (
          <AlertCircle className="w-3.5 h-3.5 text-signal-low" />
        ) : isRunning ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-blue" />
        ) : (
          <Minus className="w-3.5 h-3.5 text-ink-muted" />
        )}
      </span>
      <span className="flex-1 truncate text-ink" title={source.url}>{source.url}</span>
      <span className="text-xs text-ink-muted flex-shrink-0 max-w-xs truncate" title={detail}>
        {detail}
      </span>
    </div>
  );
}

interface Props {
  phase: CrawlPhase;
  run: CrawlStatusRun | null;
  queuedRun?: CrawlStatusQueuedRun | null;
  onCancel: () => void;
  onDismiss: () => void;
}

export function CrawlProgressPanel({ phase, run, queuedRun, onCancel, onDismiss }: Props) {
  if (phase === 'idle' || !run) return null;

  const sources = run.sources;
  const doneCount = sources.filter((s) => s.status === 'completed' || s.status === 'failed').length;
  const total = run.total_sources;
  const hasErrors = run.total_errors > 0;
  const isActive = phase === 'crawling' || phase === 'analysing';
  const hasQueue = (queuedRun?.sources.length ?? 0) > 0;

  const analysingSource = sources.find((s) => s.status === 'analysing');
  const analysisTotal = analysingSource?.analyse_docs_total ?? 0;
  const analysisDone = analysingSource?.analyse_docs_done ?? 0;

  const borderColor = hasErrors
    ? 'border-signal-low/40'
    : phase === 'done'
      ? 'border-signal-high/40'
      : 'border-accent-blue/40';

  const queueSuffix = hasQueue ? ' (1/2)' : '';
  const headerText =
    phase === 'crawling'
      ? `Crawl läuft…${queueSuffix} (${doneCount}/${total})`
      : phase === 'analysing'
        ? analysisTotal > 0
          ? `Analyse läuft… (${analysisDone}/${analysisTotal} Docs)`
          : 'Analyse läuft…'
        : hasErrors
          ? `Fertig — ${total} Sources, ${run.total_new} neue Docs, ${run.total_errors} Fehler`
          : `Fertig — ${run.total_new} neue Docs`;

  return (
    <div className={`mb-6 rounded-lg border ${borderColor} bg-app-card overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-app-border/30">
        <span className="text-sm font-medium text-ink">{headerText}</span>
        {isActive ? (
          <button onClick={onCancel} className="text-xs text-ink-muted hover:text-ink px-2 py-0.5 rounded">
            Cancel
          </button>
        ) : (
          <button onClick={onDismiss} className="text-ink-muted hover:text-ink" aria-label="Dismiss">
            <X size={16} />
          </button>
        )}
      </div>
      <div>
        {sources.map((s) => (
          <SourceRow key={s.source_id} source={s} />
        ))}
      </div>
      {hasQueue && queuedRun && (
        <>
          <div className="px-4 py-1.5 border-t border-app-border/30 bg-app-bg/40">
            <span className="text-xs text-ink-muted font-medium">Queued (startet danach)</span>
          </div>
          <div>
            {queuedRun.sources.map((s) => (
              <div key={s.source_id} className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0 opacity-60">
                <Minus className="w-3.5 h-3.5 text-ink-muted flex-shrink-0" />
                <span className="flex-1 truncate text-ink" title={s.url}>{s.url}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
