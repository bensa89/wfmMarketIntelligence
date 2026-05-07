import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client';
import type { Source, SourceCreate, SourceUpdate } from '../types';

export function useSources(companyId?: string) {
  const params = companyId ? { company_id: companyId } : undefined;
  return useQuery<Source[]>({
    queryKey: ['sources', params],
    queryFn: () => apiGet<Source[]>('/sources', params),
    refetchInterval: (query) =>
      query.state.data?.some((s) => s.analysis_status === 'analysing') ? 3000 : false,
  });
}

export function useCreateSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SourceCreate) => apiPost<Source>('/sources', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });
}

export function useUpdateSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sourceId, data }: { sourceId: string; data: SourceUpdate }) =>
      apiPut<Source>(`/sources/${sourceId}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });
}

export function useDeleteSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => apiDelete(`/sources/${sourceId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });
}
