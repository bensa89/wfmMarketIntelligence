import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
export function useAnalyseSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => apiPost<{ source_id: string; analysed: number; errors: number; analyse_ms: number }>(`/crawl/analyse/${sourceId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sources'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}
