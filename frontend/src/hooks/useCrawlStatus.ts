import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type { CrawlStatusResponse, CrawlStatusRun, CrawlStatusQueuedRun, CrawlPhase } from '../types';

const DISMISSED_KEY = 'crawlStatus.dismissedRunId';

export function useCrawlStatus() {
  const qc = useQueryClient();
  const dismissedRef = useRef(false);
  const [dismissed, setDismissed] = useState(false);
  const prevStatusRef = useRef<string | undefined>(undefined);

  const { data } = useQuery<CrawlStatusResponse>({
    queryKey: ['crawlStatus'],
    queryFn: () => apiGet<CrawlStatusResponse>('/crawl/status'),
    refetchInterval: (query) => {
      if (dismissedRef.current) return false;
      const status = query.state.data?.active_run?.status;
      if (status === 'running') return 2000;
      if (query.state.data?.active_run) return 10000;
      return false;
    },
    refetchOnMount: true,
    staleTime: 0,
  });

  useEffect(() => {
    const status = data?.active_run?.status;
    if (prevStatusRef.current === 'running' && status !== 'running') {
      qc.invalidateQueries({ queryKey: ['sources'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['crawlRuns'] });
      qc.invalidateQueries({ queryKey: ['activeCrawlRun'] });
      qc.invalidateQueries({ queryKey: ['discoveredPagesStats'] });
      qc.invalidateQueries({ queryKey: ['signalsOverTime'] });
      qc.invalidateQueries({ queryKey: ['signalDistribution'] });
      qc.invalidateQueries({ queryKey: ['sourceCandidates'] });
    }
    if (status === 'running') {
      localStorage.removeItem(DISMISSED_KEY);
      dismissedRef.current = false;
      setDismissed(false);
    }
    prevStatusRef.current = status;
  }, [data, qc]);

  const start = useCallback(
    async (sourceId?: string) => {
      localStorage.removeItem(DISMISSED_KEY);
      dismissedRef.current = false;
      setDismissed(false);
      const path = sourceId ? `/crawl/start/${sourceId}` : '/crawl/start';
      try {
        await apiPost(path);
      } catch {
        // error handled by caller or ignored
      }
      qc.invalidateQueries({ queryKey: ['crawlStatus'] });
    },
    [qc],
  );

  const startCompany = useCallback(
    async (companySlug: string) => {
      localStorage.removeItem(DISMISSED_KEY);
      dismissedRef.current = false;
      setDismissed(false);
      try {
        await apiPost(`/crawl/start/company/${companySlug}`);
      } catch {
        // error handled by caller or ignored
      }
      qc.invalidateQueries({ queryKey: ['crawlStatus'] });
    },
    [qc],
  );

  const cancel = useCallback(async () => {
    try {
      await apiPost('/crawl/cancel');
    } catch {
      // ignore
    }
    qc.invalidateQueries({ queryKey: ['crawlStatus'] });
  }, [qc]);

  const run: CrawlStatusRun | null = data?.active_run ?? null;
  const queuedRun: CrawlStatusQueuedRun | null = data?.queued_run ?? null;

  const dismiss = useCallback(() => {
    if (run?.id) localStorage.setItem(DISMISSED_KEY, run.id);
    dismissedRef.current = true;
    setDismissed(true);
  }, [run]);

  const phase = useMemo((): CrawlPhase => {
    if (!run) return 'idle';
    const persistedDismissedId = localStorage.getItem(DISMISSED_KEY);
    if (dismissed || persistedDismissedId === run.id) return 'idle';
    if (run.status === 'running') {
      return run.sources.some((s) => s.status === 'analysing') ? 'analysing' : 'crawling';
    }
    if (run.status === 'completed') return 'done';
    return 'idle';
  }, [run, dismissed]);

  const isRunning = run?.status === 'running';

  return { run, queuedRun, phase, isRunning, start, startCompany, cancel, dismiss };
}
