import { X, Check, AlertCircle, Loader2, Minus } from 'lucide-react';
import type { SourceCrawlState, CrawlStreamSummary, CrawlStep } from '../types';

const STEP_LABELS: Record<CrawlStep, string> = {
  fetching: 'Fetching...',
  extracting: 'Extracting...',
  analysing: 'Analysing...',
  discovering: 'Discovering...',
};

function SourceRow({ state }: { state: SourceCrawlState }) {
  let domain: string;
  try {
    domain = new URL(state.url).hostname;
  } catch {
    domain = state.url;
  }

  return (
    <div className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-dark-border/20 last:border-0">
      <span className="w-4 flex-shrink-0 flex items-center justify-center">
        {state.status === 'done' && <Check size={13} className="text-signal-high" />}
        {state.status === 'error' && <AlertCircle size={13} className="text-signal-low" />}
        {state.status === 'running' && (
          <Loader2 size={13} className="text-dark-accent animate-spin" />
        )}
        {state.status === 'waiting' && <Minus size={13} className="text-dark-muted" />}
      </span>
      <span className="flex-1 text-dark-text truncate" title={state.url}>
        {domain}
      </span>
      <span className="text-dark-muted text-xs min-w-0 shrink-0">
        {state.status === 'done' && state.result
          ? `${state.result.new_documents} new · ${state.result.skipped} skipped`
          : state.status === 'error'
            ? (state.errorMessage ?? 'Error')
            : state.status === 'running' && state.currentStep
              ? STEP_LABELS[state.currentStep]
              : 'Waiting...'}
      </span>
    </div>
  );
}

interface Props {
  isRunning: boolean;
  sourceStates: SourceCrawlState[];
  summary: CrawlStreamSummary | null;
  connectionError: string | null;
  onCancel: () => void;
  onDismiss: () => void;
}

export function CrawlProgressPanel({
  isRunning,
  sourceStates,
  summary,
  connectionError,
  onCancel,
  onDismiss,
}: Props) {
  if (!isRunning && !summary && !connectionError) return null;

  const doneCount = sourceStates.filter(
    (s) => s.status === 'done' || s.status === 'error',
  ).length;
  const total = summary?.sources_processed ?? sourceStates.length;
  const hasErrors = (summary?.total_errors ?? 0) > 0 || connectionError != null;

  const borderColor = hasErrors
    ? 'border-signal-low/40'
    : summary
      ? 'border-signal-high/40'
      : 'border-dark-accent/40';

  const headerText = connectionError
    ? `Connection failed: ${connectionError}`
    : isRunning
      ? `Crawling... (${doneCount}/${total})`
      : hasErrors
        ? `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs, ${summary?.total_errors ?? 0} errors`
        : `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs`;

  return (
    <div
      className={`mb-6 rounded-lg border ${borderColor} bg-dark-card overflow-hidden`}
    >
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-dark-border/30">
        <span className="text-sm font-medium text-dark-text">{headerText}</span>
        {isRunning ? (
          <button
            onClick={onCancel}
            className="text-xs text-dark-muted hover:text-dark-text px-2 py-0.5 rounded"
          >
            Cancel
          </button>
        ) : (
          <button
            onClick={onDismiss}
            className="text-dark-muted hover:text-dark-text"
            aria-label="Dismiss"
          >
            <X size={16} />
          </button>
        )}
      </div>
      <div>
        {sourceStates.map((s) => (
          <SourceRow key={s.source_id} state={s} />
        ))}
      </div>
    </div>
  );
}
