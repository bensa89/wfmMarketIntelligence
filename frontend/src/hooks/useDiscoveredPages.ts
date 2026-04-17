import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch } from '../api/client';
import type { DiscoveredPage } from '../types';

export function useDiscoveredPages(sourceId: string | null) {
  return useQuery<DiscoveredPage[]>({
    queryKey: ['discovered-pages', sourceId],
    queryFn: () => apiGet<DiscoveredPage[]>('/discovered-pages', { source_id: sourceId! }),
    enabled: !!sourceId,
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