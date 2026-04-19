import { useState, useRef, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type {
  CrawlEvent,
  CrawlStreamSummary,
  CrawlRunList,
  CrawlRunSourceState,
  SourceCrawlState,
} from '../types';

function getAuthHeader(): Record<string, string> {
  const stored = localStorage.getItem('wfm_credentials');
  if (!stored) return {};
  try {
    const { username, password } = JSON.parse(stored);
    return { Authorization: `Basic ${btoa(`${username}:${password}`)}` };
  } catch {
    return {};
  }
}

function mapSourceStatus(
  status: CrawlRunSourceState['status'],
): SourceCrawlState['status'] {
  switch (status) {
    case 'completed':
      return 'done';
    case 'failed':
      return 'error';
    case 'running':
      return 'running';
    case 'skipped':
      return 'done';
    case 'pending':
      return 'waiting';
    default:
      return 'waiting';
  }
}

export function useCrawlStream() {
  const qc = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const isRunningRef = useRef(false);
  const [crawlRunId, setCrawlRunId] = useState<string | null>(null);
  const [sourceStates, setSourceStates] = useState<SourceCrawlState[]>([]);
  const [summary, setSummary] = useState<CrawlStreamSummary | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [crawlTotal, setCrawlTotal] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback(
    (event: CrawlEvent) => {
      switch (event.type) {
        case 'crawl_start':
          setCrawlRunId(event.crawl_run_id);
          setCrawlTotal(event.total);
          break;
        case 'initial_state':
          setCrawlRunId(event.crawl_run_id);
          setCrawlTotal(event.total);
          setSourceStates(
            event.sources.map((s) => ({
              source_id: s.source_id,
              url: s.url,
              status: mapSourceStatus(s.status),
              currentStep: s.current_step as SourceCrawlState['currentStep'] | undefined,
              result:
                s.new_documents > 0 || s.skipped > 0 || s.errors > 0
                  ? { new_documents: s.new_documents, skipped: s.skipped, errors: s.errors }
                  : undefined,
              errorMessage: s.error_message,
            })),
          );
          setIsRunning(true);
          break;
        case 'reconnect_complete':
          break;
        case 'no_active_run':
          setIsRunning(false);
          break;
        case 'source_start':
          setSourceStates((prev) => {
            if (prev.some((s) => s.source_id === event.source_id)) return prev;
            return [
              ...prev,
              {
                source_id: event.source_id,
                url: event.url,
                status: 'running',
              },
            ];
          });
          break;
        case 'step':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? { ...s, currentStep: event.step }
                : s,
            ),
          );
          break;
        case 'source_done':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    status: event.errors > 0 ? 'error' : 'done',
                    currentStep: undefined,
                    errorMessage: event.errors > 0 ? s.errorMessage : undefined,
                    result: {
                      new_documents: event.new_documents,
                      skipped: event.skipped,
                      errors: event.errors,
                    },
                  }
                : s,
            ),
          );
          break;
        case 'error':
          if (event.source_id) {
            setSourceStates((prev) =>
              prev.map((s) =>
                s.source_id === event.source_id
                  ? { ...s, status: 'error', errorMessage: event.message }
                  : s,
              ),
            );
          } else {
            setConnectionError(event.message);
          }
          break;
        case 'crawl_done':
          setSummary({
            sources_processed: event.sources_processed,
            total_new: event.total_new,
            total_errors: event.total_errors,
          });
          qc.invalidateQueries({ queryKey: ['documents'] });
          qc.invalidateQueries({ queryKey: ['signals'] });
          qc.invalidateQueries({ queryKey: ['sources'] });
          qc.invalidateQueries({ queryKey: ['crawlRuns'] });
          qc.invalidateQueries({ queryKey: ['activeCrawlRun'] });
          qc.invalidateQueries({ queryKey: ['discoveredPagesStats'] });
          qc.invalidateQueries({ queryKey: ['signalsOverTime'] });
          qc.invalidateQueries({ queryKey: ['signalDistribution'] });
          qc.invalidateQueries({ queryKey: ['sourceCandidates'] });
          setIsRunning(false);
          break;
      }
    },
    [qc],
  );

  useEffect(() => {
    (async () => {
      try {
        const runs = await apiGet<CrawlRunList[]>('/crawl-runs/', {
          status: 'running',
        });
        if (runs.length === 0) return;

        const run = runs[0];
        setCrawlRunId(run.id);
        setCrawlTotal(run.total_sources);
        setIsRunning(true);
        isRunningRef.current = true;

        const res = await fetch('/api/crawl/reconnect', {
          headers: getAuthHeader(),
        });
        if (!res.ok || !res.body) return;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop()!;

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const event: CrawlEvent = JSON.parse(line.slice(6));
              handleEvent(event);
            } catch {
              // ignore malformed lines
            }
          }
        }
      } catch {
        // no active run or reconnect failed — that's fine
      }
    })();
  }, [handleEvent]);

  const start = useCallback(
    async (sourceId?: string) => {
      if (isRunningRef.current) return;
      isRunningRef.current = true;
      setIsRunning(true);

      abortRef.current = new AbortController();
      setSourceStates([]);
      setSummary(null);
      setConnectionError(null);
      setCrawlTotal(0);
      setCrawlRunId(null);

      const path = sourceId
        ? `/api/crawl/stream/${sourceId}`
        : '/api/crawl/stream';

      try {
        const res = await fetch(path, {
          headers: getAuthHeader(),
          signal: abortRef.current.signal,
        });

        if (!res.ok) {
          setConnectionError(`Request failed: ${res.status}`);
          return;
        }

        if (!res.body) {
          setConnectionError('Streaming not supported');
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop()!;

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const event: CrawlEvent = JSON.parse(line.slice(6));
              handleEvent(event);
            } catch {
              // ignore malformed lines
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setConnectionError(err.message);
        }
      } finally {
        isRunningRef.current = false;
        setIsRunning(false);
      }
    },
    [handleEvent],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSourceStates([]);
    setSummary(null);
    setConnectionError(null);
    setCrawlTotal(0);
    setCrawlRunId(null);
  }, []);

  return {
    start,
    cancel,
    reset,
    isRunning,
    crawlRunId,
    sourceStates,
    summary,
    connectionError,
    crawlTotal,
  };
}