import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { Signal, SignalType } from '../types';

export interface SignalsFilters {
  company_id?: string;
  signal_type?: SignalType;
  min_relevance?: number;
  min_confidence?: number;
  max_age_days?: number;
  q?: string;
}

export function useSignals(filters?: SignalsFilters) {
  const params: Record<string, string> = {};
  if (filters?.company_id) params.company_id = filters.company_id;
  if (filters?.signal_type) params.signal_type = filters.signal_type;
  if (filters?.min_relevance !== undefined) params.min_relevance = String(filters.min_relevance);
  if (filters?.min_confidence !== undefined) params.min_confidence = String(filters.min_confidence);
  if (filters?.max_age_days !== undefined) params.max_age_days = String(filters.max_age_days);
  if (filters?.q) params.q = filters.q;

  return useQuery<Signal[]>({
    queryKey: ['signals', params],
    queryFn: () => apiGet<Signal[]>('/signals', params),
    select: (data) =>
      [...data].sort((a, b) => {
        if (filters?.q) return 0;
        const dateA = a.published_at ? new Date(a.published_at).getTime() : new Date(a.created_at).getTime();
        const dateB = b.published_at ? new Date(b.published_at).getTime() : new Date(b.created_at).getTime();
        return dateB - dateA;
      }),
  });
}

export function useSignal(id: string) {
  return useQuery<Signal>({
    queryKey: ['signals', id],
    queryFn: () => apiGet<Signal>(`/signals/${id}`),
    enabled: !!id,
  });
}
