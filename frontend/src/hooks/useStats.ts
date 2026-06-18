import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { LastCrawlSummary } from '../types';

export function useLastCrawlSummary() {
  return useQuery<LastCrawlSummary>({
    queryKey: ['stats', 'lastCrawlSummary'],
    queryFn: () => apiGet<LastCrawlSummary>('/stats/last-crawl-summary'),
  });
}
