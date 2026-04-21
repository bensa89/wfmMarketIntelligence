// src/hooks/useBriefing.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, ApiError } from '../api/client';
import type { CrawlBriefing } from '../types';

export function useLatestBriefing() {
  return useQuery<CrawlBriefing | null>({
    queryKey: ['briefing', 'latest'],
    queryFn: async () => {
      try {
        return await apiGet<CrawlBriefing>('/briefings/latest');
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
}

export function useGenerateBriefing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<CrawlBriefing>('/briefings/generate', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['briefing', 'latest'] });
    },
  });
}
