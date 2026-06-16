import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut, apiPost } from '../api/client';
import type { Context, ContextUpdate, ExternalCompanyView } from '../types';

export function useContextData() {
  return useQuery<Context>({
    queryKey: ['context'],
    queryFn: () => apiGet<Context>('/context'),
  });
}

export function useUpdateContext() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ContextUpdate) => apiPut<Context>('/context', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['context'] }),
  });
}

export function useExternalView() {
  return useQuery<ExternalCompanyView | null>({
    queryKey: ['external-view'],
    queryFn: () => apiGet<ExternalCompanyView>('/context/external-view').catch((e) => {
      if (e?.status === 404) return null;
      throw e;
    }),
  });
}

export function useSynthesizeExternalView() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<ExternalCompanyView>('/context/synthesize-external-view', {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['external-view'] }),
  });
}
