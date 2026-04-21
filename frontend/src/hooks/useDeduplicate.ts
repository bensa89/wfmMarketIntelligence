import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
import type { DedupResult } from '../types';

export function useDeduplicate() {
  const queryClient = useQueryClient();

  return useMutation<DedupResult, Error, { companyId: string; maxAgeDays?: number }>({
    mutationFn: ({ companyId, maxAgeDays }) => {
      const params: Record<string, string> = { company_id: companyId };
      if (maxAgeDays !== undefined) params.max_age_days = String(maxAgeDays);
      return apiPost<DedupResult>(`/signals/deduplicate?${new URLSearchParams(params).toString()}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}