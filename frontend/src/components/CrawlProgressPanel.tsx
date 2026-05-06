import { X, Check, AlertCircle, Loader2, Minus } from 'lucide-react';
import type { SourceCrawlState, CrawlStreamSummary, CrawlStep } from '../types';

const STEP_LABELS: Record<CrawlStep, string> = {
  fetching: 'Fetching...',
  extracting: 'Extracting...',
  analysing: 'Analysing...',
  discovering: 'Discovering...',
};

function formatMs(ms: number | undefined): string {
  if (ms == null) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function SourceRow({ state }: { state: SourceCrawlState }) {
  let domain: string;
  try {
    domain = new URL(state.url).hostname;
  } catch {
    domain = state.url;
  }

  const stepLabel =
    state.status === 'running' && state.currentStep
      ? state.currentStep === 'discovering' && state.discoveryProgress
        ? `Discovering ${state.discoveryProgress.pages_crawled}/${state.discoveryProgress.max_pages} Seiten`
        : STEP_LABELS[state.currentStep]
      : null;

  const timingsParts: string[] = [];
  if (state.stepTimings) {
    const order: CrawlStep[] = ['fetching', 'extracting', 'analysing', 'discovering'];
    for (const step of order) {
      const ms = state.stepTimings[step];
      if (ms != null) {
        const shortLabel = step === 'analysing' ? 'analyse' : step === 'discovering' ? 'discover' : step === 'extracting' ? 'extract' : 'fetch';
        timingsParts.push(`${shortLabel} ${formatMs(ms)}`);
      }
    }
  }

  return (
    <div className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0">
      <span className="w-4 flex-shrink-0 flex justify-center">
        {state.status === 'done' ? (
          <Check className="w-3.5 h-3.5 text-signal-high" />
        ) : state.status === 'error' ? (
          <AlertCircle className="w-3.5 h-3.5 text-signal-low" />
        ) : state.status === 'running' ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-blue" />
        ) : (
          <Minus className="w-3.5 h-3.5 text-ink-muted" />
        )}
      </span>
      <span className="flex-1 truncate text-ink" title={state.url}>{domain}</span>
      <span className="text-xs text-ink-muted flex-shrink-0">
        {state.status === 'done' && state.result
          ? timingsParts.length > 0
            ? timingsParts.join(' · ')
            : `${state.result.new_documents} new · ${state.result.skipped} skipped`
          : state.status === 'error'
            ? (state.errorMessage ?? 'Error')
            : state.status === 'running' && stepLabel
              ? stepLabel
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
  crawlTotal?: number;
  queuedSources?: { source_id: string; url: string }[];
  onCancel: () => void;
  onDismiss: () => void;
}

export function CrawlProgressPanel({
  isRunning,
  sourceStates,
  summary,
  connectionError,
  crawlTotal,
  queuedSources = [],
  onCancel,
  onDismiss,
}: Props) {
  if (!isRunning && !summary && !connectionError && sourceStates.length === 0 && queuedSources.length === 0) return null;

  const doneCount = sourceStates.filter(
    (s) => s.status === 'done' || s.status === 'error',
  ).length;
  const total = summary?.sources_processed ?? crawlTotal ?? sourceStates.length;
  const hasErrors = (summary?.total_errors ?? 0) > 0 || connectionError != null;
  const hasQueue = queuedSources.length > 0;

  const borderColor = hasErrors
    ? 'border-signal-low/40'
    : summary
      ? 'border-signal-high/40'
      : 'border-accent-blue/40';

  const runCounter = hasQueue ? ' (1/2)' : '';
  const headerText = connectionError
    ? `Connection failed: ${connectionError}`
    : isRunning
      ? `Crawling...${runCounter} (${doneCount}/${total})`
      : hasErrors
        ? `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs, ${summary?.total_errors ?? 0} errors`
        : `Crawl complete — ${total} sources, ${summary?.total_new ?? 0} new docs`;

  return (
    <div className={`mb-6 rounded-lg border ${borderColor} bg-app-card overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-app-border/30">
        <span className="text-sm font-medium text-ink">{headerText}</span>
        {isRunning ? (
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
        {sourceStates.map((s) => (
          <SourceRow key={s.source_id} state={s} />
        ))}
      </div>
      {hasQueue && (
        <>
          <div className="px-4 py-1.5 border-t border-app-border/30 bg-app-bg/40">
            <span className="text-xs text-ink-muted font-medium">Queued (startet danach)</span>
          </div>
          <div>
            {queuedSources.map((s) => {
              let domain: string;
              try { domain = new URL(s.url).hostname; } catch { domain = s.url; }
              return (
                <div key={s.source_id} className="flex items-center gap-3 py-1.5 px-4 text-sm border-b border-app-border/20 last:border-0 opacity-60">
                  <Minus className="w-3.5 h-3.5 text-ink-muted flex-shrink-0" />
                  <span className="flex-1 truncate text-ink">{domain}</span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
