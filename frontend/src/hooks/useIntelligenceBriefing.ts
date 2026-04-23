import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, ApiError } from '../api/client';
import type { IntelligenceBriefing } from '../types/intelligence';

export function useLatestIntelligenceBriefing() {
  return useQuery<IntelligenceBriefing | null>({
    queryKey: ['intelligence', 'briefing', 'latest'],
    queryFn: async () => {
      try {
        return await apiGet<IntelligenceBriefing>('/intelligence/briefing/latest');
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
}

export function useGenerateIntelligenceBriefing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<IntelligenceBriefing>('/intelligence/briefing/generate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'briefing', 'latest'] });
    },
  });
}
