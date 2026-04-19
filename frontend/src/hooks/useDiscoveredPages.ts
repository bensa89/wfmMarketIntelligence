import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch, apiDelete } from '../api/client';
import type { DiscoveredPage, DiscoveredPagesStats } from '../types';

export function useDiscoveredPages(sourceId: string | null) {
  return useQuery<DiscoveredPage[]>({
    queryKey: ['discovered-pages', sourceId],
    queryFn: () => apiGet<DiscoveredPage[]>('/discovered-pages', { source_id: sourceId! }),
    enabled: !!sourceId,
  });
}

export function useDiscoveredPagesStats() {
  return useQuery<DiscoveredPagesStats>({
    queryKey: ['discoveredPagesStats'],
    queryFn: () => apiGet<DiscoveredPagesStats>('/discovered-pages/stats'),
  });
}

export function useToggleDiscoveredPage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ pageId, isActive }: { pageId: string; isActive: boolean }) =>
      apiPatch<DiscoveredPage>(`/discovered-pages/${pageId}`, { is_active: isActive }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['discovered-pages', data.source_id] });
    },
  });
}

export function useDeleteDiscoveredPage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ pageId, sourceId }: { pageId: string; sourceId: string }) =>
      apiDelete(`/discovered-pages/${pageId}`).then(() => ({ pageId, sourceId })),
    onSuccess: ({ sourceId }) => {
      qc.invalidateQueries({ queryKey: ['discovered-pages', sourceId] });
    },
  });
}