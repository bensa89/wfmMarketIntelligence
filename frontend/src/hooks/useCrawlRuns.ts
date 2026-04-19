import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRunList } from '../types';

export function useCrawlRuns(status?: string, limit: number = 1) {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  params.limit = String(limit);

  return useQuery<CrawlRunList[]>({
    queryKey: ['crawlRuns', params],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/', params),
  });
}

export function useLastCompletedCrawl() {
  const query = useQuery({
    queryKey: ['crawlRuns', { status: 'completed', limit: '1' }],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/', { status: 'completed', limit: '1' }),
    select: (runs: CrawlRunList[]): CrawlRunList | null =>
      runs && runs.length > 0 ? runs[0] : null,
  });
  return { lastCrawl: query.data ?? null, isLoading: query.isLoading };
}