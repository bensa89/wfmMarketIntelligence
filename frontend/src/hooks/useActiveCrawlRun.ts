import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRunList } from '../types';

export function useActiveCrawlRun() {
  const { data, isLoading } = useQuery({
    queryKey: ['activeCrawlRun'],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/', { status: 'running' }),
    refetchInterval: 5000,
    select: (runs) => (runs && runs.length > 0 ? runs[0] : null),
  });

  return { activeRun: data ?? null, isLoading };
}