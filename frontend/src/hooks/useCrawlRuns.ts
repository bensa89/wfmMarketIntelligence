import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { CrawlRunList } from '../types';

export function useLastCompletedCrawl() {
  const query = useQuery({
    queryKey: ['crawlRuns', { status: 'completed', limit: '1' }],
    queryFn: () => apiGet<CrawlRunList[]>('/crawl-runs/', { status: 'completed', limit: '1' }),
    select: (runs: CrawlRunList[]): CrawlRunList | null =>
      runs && runs.length > 0 ? runs[0] : null,
  });
  return { lastCrawl: query.data ?? null, isLoading: query.isLoading };
}