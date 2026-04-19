import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SignalOverTimePoint, SignalDistribution } from '../types';

export function useSignalsOverTime(days: number = 14) {
  return useQuery<SignalOverTimePoint[]>({
    queryKey: ['signalsOverTime', days],
    queryFn: () => apiGet<SignalOverTimePoint[]>('/stats/signals/over-time', { days: String(days) }),
  });
}

export function useSignalDistribution(companyId?: string) {
  const params = companyId ? { company_id: companyId } : undefined;
  return useQuery<SignalDistribution>({
    queryKey: ['signalDistribution', params],
    queryFn: () => apiGet<SignalDistribution>('/stats/signals/distribution', params),
  });
}