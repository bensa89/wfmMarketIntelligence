import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SignalsFeedResponse, SignalsFeedFilters, SignalFeedItem } from '../types/intelligence';

export function useSignalsFeed(filters: SignalsFeedFilters = {}) {
  const params: Record<string, string> = {};
  if (filters.company_id) params.company_id = filters.company_id;
  if (filters.capability) params.capability = filters.capability;
  if (filters.signal_type) params.signal_type = filters.signal_type;
  if (filters.movement_strength) params.movement_strength = filters.movement_strength;
  if (filters.min_confidence !== undefined) params.min_confidence = String(filters.min_confidence);
  if (filters.from_date) params.from_date = filters.from_date;
  if (filters.to_date) params.to_date = filters.to_date;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.page) params.page = String(filters.page);
  if (filters.page_size) params.page_size = String(filters.page_size);

  return useQuery<SignalsFeedResponse>({
    queryKey: ['intelligence', 'signals-feed', params],
    queryFn: () => apiGet<SignalsFeedResponse>('/intelligence/signals/feed', params),
    staleTime: 60 * 1000,
  });
}

export function useSignalFeedItem(id: string | null) {
  return useQuery<SignalFeedItem>({
    queryKey: ['intelligence', 'signal', id],
    queryFn: () => apiGet<SignalFeedItem>(`/intelligence/signals/${id}`),
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}
