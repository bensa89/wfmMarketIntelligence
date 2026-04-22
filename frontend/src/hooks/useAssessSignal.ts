import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
import type { SignalAssessment } from '../types/intelligence';

export function useAssessSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (signalId: string) =>
      apiPost<SignalAssessment>(`/intelligence/signals/${signalId}/assess`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'signals-feed'] });
      queryClient.invalidateQueries({ queryKey: ['intelligence', 'overview'] });
    },
  });
}
