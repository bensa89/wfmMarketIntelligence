import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type { Digest } from '../types';

export function useDigests() {
  return useQuery<Digest[]>({
    queryKey: ['digests'],
    queryFn: () => apiGet<Digest[]>('/digests'),
  });
}

export function useDigest(id: string) {
  return useQuery<Digest>({
    queryKey: ['digests', id],
    queryFn: () => apiGet<Digest>(`/digests/${id}`),
    enabled: !!id,
  });
}

export function useGenerateDigest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<Digest>('/digests/generate'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['digests'] }),
  });
}
