import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
import type { PeriodType } from '../types/intelligence';

export function useSummarizeCompetitor(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (period_type: PeriodType) =>
      apiPost(`/intelligence/competitors/${companyId}/summarize?period_type=${period_type}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'workspace'] });
    },
  });
}
