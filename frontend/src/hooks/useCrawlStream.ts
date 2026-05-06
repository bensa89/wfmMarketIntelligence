import { useState, useRef, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type {
  CrawlEvent,
  CrawlPhase,
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
  const [phase, setPhase] = useState<CrawlPhase>('idle');
  const phaseRef = useRef<CrawlPhase>('idle');
  const [analysisDocsTotal, setAnalysisDocsTotal] = useState(0);
  const [analysisDocsDone, setAnalysisDocsDone] = useState(0);
  const isRunningRef = useRef(false);
  const [crawlRunId, setCrawlRunId] = useState<string | null>(null);
  const [sourceStates, setSourceStates] = useState<SourceCrawlState[]>([]);
  const [summary, setSummary] = useState<CrawlStreamSummary | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [crawlTotal, setCrawlTotal] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  // Queue state
  const [queuedSources, setQueuedSources] = useState<{ source_id: string; url: string }[]>([]);
  const queuedRunIdRef = useRef<string | null>(null);
  const startQueuedStreamRef = useRef<() => Promise<void>>(() => Promise.resolve());

  const setPhaseSync = useCallback((p: CrawlPhase) => {
    phaseRef.current = p;
    setPhase(p);
  }, []);

  const handleEvent = useCallback(
    (event: CrawlEvent) => {
      switch (event.type) {
        case 'crawl_start':
          setCrawlRunId(event.crawl_run_id);
          setCrawlTotal(event.total);
          setQueuedSources([]);
          queuedRunIdRef.current = null;
          setAnalysisDocsTotal(0);
          setAnalysisDocsDone(0);
          setPhaseSync('crawling');
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
              stepTimings: s.fetch_ms != null ? {
                fetching: s.fetch_ms!,
                extracting: s.extract_ms!,
                analysing: s.analyse_ms!,
                discovering: s.discover_ms!,
              } : undefined,
              discoveryProgress:
                s.current_step === 'discovering' && s.discover_pages_crawled != null
                  ? {
                      pages_found: s.discover_pages_found ?? s.discover_pages_crawled,
                      pages_crawled: s.discover_pages_crawled,
                      max_pages: 50,
                    }
                  : undefined,
            })),
          );
          setPhaseSync(event.analysis_phase_active ? 'analysing' : 'crawling');
          break;
        case 'reconnect_complete':
          break;
        case 'no_active_run':
          setPhaseSync('idle');
          break;
        case 'queued_state':
          setQueuedSources(event.sources);
          queuedRunIdRef.current = event.crawl_run_id;
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
        case 'discovery_progress':
          setSourceStates((prev) =>
            prev.map((s) => {
              if (s.source_id !== event.source_id) return s;
              const existing = s.discoveredUrls ?? [];
              const updated =
                event.current_url && !existing.includes(event.current_url)
                  ? [...existing, event.current_url]
                  : existing;
              return {
                ...s,
                discoveryProgress: {
                  pages_found: event.pages_found,
                  pages_crawled: event.pages_crawled,
                  max_pages: event.max_pages,
                },
                discoveredUrls: updated,
              };
            }),
          );
          break;
        case 'step_timing':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    stepTimings: {
                      ...s.stepTimings,
                      [event.step]: event.duration_ms,
                    },
                  }
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
                    stepTimings: event.timings
                      ? {
                          fetching: event.timings.fetch_ms,
                          extracting: event.timings.extract_ms,
                          analysing: event.timings.analyse_ms,
                          discovering: event.timings.discover_ms,
                        }
                      : s.stepTimings,
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
          setAnalysisDocsTotal(event.docs_to_analyse);
          qc.invalidateQueries({ queryKey: ['documents'] });
          qc.invalidateQueries({ queryKey: ['signals'] });
          qc.invalidateQueries({ queryKey: ['sources'] });
          qc.invalidateQueries({ queryKey: ['crawlRuns'] });
          qc.invalidateQueries({ queryKey: ['activeCrawlRun'] });
          qc.invalidateQueries({ queryKey: ['discoveredPagesStats'] });
          qc.invalidateQueries({ queryKey: ['signalsOverTime'] });
          qc.invalidateQueries({ queryKey: ['signalDistribution'] });
          qc.invalidateQueries({ queryKey: ['sourceCandidates'] });
          if (event.analysis_pending) {
            setPhaseSync('analysing');
          } else {
            setPhaseSync('done');
            isRunningRef.current = false;
            if (queuedRunIdRef.current) {
              setTimeout(() => startQueuedStreamRef.current(), 300);
            }
          }
          break;
        case 'analysis_phase_start':
          setPhaseSync('analysing');
          break;
        case 'analysis_start':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? { ...s, currentStep: 'analysing', status: 'running' }
                : s
            ),
          );
          qc.invalidateQueries({ queryKey: ['sources'] });
          break;
        case 'analysis_progress':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    analysisProgress: {
                      current: event.current,
                      total: event.total,
                      currentUrl: event.url,
                    },
                  }
                : s
            ),
          );
          break;
        case 'analysis_done':
          setSourceStates((prev) =>
            prev.map((s) =>
              s.source_id === event.source_id
                ? {
                    ...s,
                    status: 'done',
                    currentStep: undefined,
                    analysisProgress: undefined,
                    stepTimings: {
                      ...s.stepTimings,
                      analysing: event.analyse_ms,
                    },
                  }
                : s
            ),
          );
          setAnalysisDocsDone((n) => n + event.analysed);
          qc.invalidateQueries({ queryKey: ['sources'] });
          break;
        case 'analysis_phase_done':
          setPhaseSync('done');
          isRunningRef.current = false;
          if (queuedRunIdRef.current) {
            setTimeout(() => startQueuedStreamRef.current(), 300);
          }
          break;
      }
    },
    [qc, setPhaseSync],
  );

  const startQueuedStream = useCallback(async () => {
    if (isRunningRef.current) return;
    isRunningRef.current = true;
    setPhaseSync('crawling');
    setSourceStates([]);
    setSummary(null);
    setConnectionError(null);
    setCrawlTotal(0);
    setAnalysisDocsTotal(0);
    setAnalysisDocsDone(0);

    abortRef.current = new AbortController();

    try {
      const res = await fetch('/api/crawl/stream/queued', {
        headers: getAuthHeader(),
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        if (res.status === 404) {
          queuedRunIdRef.current = null;
          setQueuedSources([]);
        } else {
          setConnectionError(`Request failed: ${res.status}`);
        }
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
      // phase is set by events, not here
    }
  }, [handleEvent, setPhaseSync]);

  // Keep the ref in sync so handleEvent can call it without a direct dependency
  startQueuedStreamRef.current = startQueuedStream;

  useEffect(() => {
    (async () => {
      try {
        const runs = await apiGet<CrawlRunList[]>('/crawl-runs/', {
          status: 'running',
        });
        if (runs.length === 0) {
          // No active run — check if there's a queued run we should start
          if (queuedRunIdRef.current && !isRunningRef.current) {
            await startQueuedStream();
          }
          return;
        }

        const run = runs[0];
        setCrawlRunId(run.id);
        setCrawlTotal(run.total_sources);
        setPhaseSync('crawling');
        isRunningRef.current = true;

        abortRef.current = new AbortController();
        const res = await fetch('/api/crawl/reconnect', {
          headers: getAuthHeader(),
          signal: abortRef.current.signal,
        });
        if (!res.ok || !res.body) {
          isRunningRef.current = false;
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
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
                if (event.type === 'initial_state') {
                  Promise.all(
                    event.sources.map((s) =>
                      apiGet<{ url: string }[]>('/discovered-pages', { source_id: s.source_id })
                        .then((pages) => ({ source_id: s.source_id, urls: pages.map((p) => p.url) }))
                        .catch(() => ({ source_id: s.source_id, urls: [] as string[] })),
                    ),
                  ).then((results) => {
                    setSourceStates((prev) =>
                      prev.map((s) => {
                        const r = results.find((r) => r.source_id === s.source_id);
                        return r && r.urls.length > 0 ? { ...s, discoveredUrls: r.urls } : s;
                      }),
                    );
                  });
                }
              } catch {
                // ignore malformed lines
              }
            }
          }
        } catch (err) {
          if (err instanceof Error && err.name !== 'AbortError') throw err;
        } finally {
          isRunningRef.current = false;
        }
      } catch {
        // no active run or reconnect failed — that's fine
        isRunningRef.current = false;
      }
    })();
  }, [handleEvent, startQueuedStream, setPhaseSync]);

  const start = useCallback(
    async (sourceId?: string) => {
      // If a crawl is already running, enqueue the source instead
      if (isRunningRef.current && sourceId) {
        try {
          const res = await fetch(`/api/crawl/enqueue/${sourceId}`, {
            method: 'POST',
            headers: getAuthHeader(),
          });
          if (res.ok) {
            const data = await res.json();
            queuedRunIdRef.current = data.crawl_run_id;
            // Re-fetch queue state via reconnect to get the URL for display
            const reconnectRes = await fetch('/api/crawl/reconnect', { headers: getAuthHeader() });
            if (reconnectRes.ok && reconnectRes.body) {
              const reader = reconnectRes.body.getReader();
              const decoder = new TextDecoder();
              let buf = '';
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buf += decoder.decode(value, { stream: true });
                const lines = buf.split('\n');
                buf = lines.pop()!;
                for (const line of lines) {
                  if (!line.startsWith('data: ')) continue;
                  try {
                    const event: CrawlEvent = JSON.parse(line.slice(6));
                    if (event.type === 'queued_state') { handleEvent(event); reader.cancel(); break; }
                  } catch { /* ignore */ }
                }
              }
            }
          }
        } catch {
          // enqueue failed silently — user can retry
        }
        return;
      }

      if (isRunningRef.current) return;
      isRunningRef.current = true;
      setPhaseSync('crawling');
      setAnalysisDocsTotal(0);
      setAnalysisDocsDone(0);

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
        // phase is set by events; AbortError (cancel) is handled by cancel() setting 'idle'
      }
    },
    [handleEvent, setPhaseSync],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    apiPost('/crawl/cancel').catch(() => {});
    isRunningRef.current = false;
    setPhaseSync('idle');
  }, [setPhaseSync]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSourceStates([]);
    setSummary(null);
    setConnectionError(null);
    setCrawlTotal(0);
    setCrawlRunId(null);
    setAnalysisDocsTotal(0);
    setAnalysisDocsDone(0);
    setPhaseSync('idle');
  }, [setPhaseSync]);

  const isRunning = phase === 'crawling' || phase === 'analysing';
  const isAnalysing = phase === 'analysing';
  return {
    phase,
    analysisDocsTotal,
    analysisDocsDone,
    isRunning,
    isAnalysing,
    start,
    cancel,
    reset,
    crawlRunId,
    sourceStates,
    summary,
    connectionError,
    crawlTotal,
    queuedSources,
  };
}
