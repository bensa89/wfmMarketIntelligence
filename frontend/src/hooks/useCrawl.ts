import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api/client';
import type { CrawlResult, CrawlSingleResult } from '../types';

export function useCrawlAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<CrawlResult>('/crawl/run'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['sources'] });
    },
  });
}

export function useCrawlSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => apiPost<CrawlSingleResult>(`/crawl/run/${sourceId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['sources'] });
    },
  });
}

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
