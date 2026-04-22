import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { OverviewResponse } from '../types/intelligence';

export function useOverview() {
  return useQuery<OverviewResponse>({
    queryKey: ['intelligence', 'overview'],
    queryFn: () => apiGet<OverviewResponse>('/intelligence/overview'),
    staleTime: 5 * 60 * 1000,
  });
}
