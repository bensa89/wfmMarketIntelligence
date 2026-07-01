import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SignalStatsResponse } from '../types/intelligence';

export function useCompetitorSignalStats(slug: string, days: 30 | 90) {
  return useQuery<SignalStatsResponse>({
    queryKey: ['intelligence', 'signal-stats', slug, days],
    queryFn: () =>
      apiGet<SignalStatsResponse>(`/intelligence/competitors/${slug}/signals/stats`, {
        days: String(days),
      }),
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  });
}
