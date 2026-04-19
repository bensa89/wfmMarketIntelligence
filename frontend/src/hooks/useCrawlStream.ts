import { useState, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type {
  CrawlEvent,
  CrawlStreamSummary,
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

export function useCrawlStream() {
  const qc = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const isRunningRef = useRef(false);
  const [sourceStates, setSourceStates] = useState<SourceCrawlState[]>([]);
  const [summary, setSummary] = useState<CrawlStreamSummary | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [crawlTotal, setCrawlTotal] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback(
    (event: CrawlEvent) => {
      switch (event.type) {
        case 'crawl_start':
          setCrawlTotal(event.total);
          break;
        case 'source_start':
          setSourceStates((prev) => [
            ...prev,
            {
              source_id: event.source_id,
              url: event.url,
              status: 'running',
            },
          ]);
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
          break;
      }
    },
    [qc],
  );

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
  }, []);

  return { start, cancel, reset, isRunning, sourceStates, summary, connectionError, crawlTotal };
}
