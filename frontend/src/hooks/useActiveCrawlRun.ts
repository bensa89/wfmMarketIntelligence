import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRunList } from '../types';

export function useActiveCrawlRun() {
  const query = useQuery({
    queryKey: ['activeCrawlRun'],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/', { status: 'running' }),
    refetchInterval: 5000,
    select: (runs: CrawlRunList[]): CrawlRunList | null =>
      runs && runs.length > 0 ? runs[0] : null,
  });

  return { activeRun: query.data ?? null, isLoading: query.isLoading };
}