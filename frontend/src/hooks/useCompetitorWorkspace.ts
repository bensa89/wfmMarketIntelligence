import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { WorkspaceResponse } from '../types/intelligence';

export function useCompetitorWorkspace(slug: string) {
  return useQuery<WorkspaceResponse>({
    queryKey: ['intelligence', 'workspace', slug],
    queryFn: () => apiGet<WorkspaceResponse>(`/intelligence/competitors/${slug}/workspace`),
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  });
}
