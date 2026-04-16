import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut } from '../api/client';
import type { Context, ContextUpdate } from '../types';

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
