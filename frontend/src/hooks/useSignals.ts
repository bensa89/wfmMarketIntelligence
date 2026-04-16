import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { Signal, SignalType } from '../types';

export interface SignalsFilters {
  company_id?: string;
  signal_type?: SignalType;
  min_relevance?: number;
}

export function useSignals(filters?: SignalsFilters) {
  const params: Record<string, string> = {};
  if (filters?.company_id) params.company_id = filters.company_id;
  if (filters?.signal_type) params.signal_type = filters.signal_type;
  if (filters?.min_relevance !== undefined) params.min_relevance = String(filters.min_relevance);

  return useQuery<Signal[]>({
    queryKey: ['signals', params],
    queryFn: () => apiGet<Signal[]>('/signals', params),
  });
}

export function useSignal(id: string) {
  return useQuery<Signal>({
    queryKey: ['signals', id],
    queryFn: () => apiGet<Signal>(`/signals/${id}`),
    enabled: !!id,
  });
}
