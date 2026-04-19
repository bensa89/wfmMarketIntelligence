import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SourceCandidate } from '../types';

export function useSourceCandidates(status?: string) {
  const params = status ? { status } : undefined;
  return useQuery<SourceCandidate[]>({
    queryKey: ['sourceCandidates', params],
    queryFn: () => apiGet<SourceCandidate[]>('/source-candidates/', params),
  });
}