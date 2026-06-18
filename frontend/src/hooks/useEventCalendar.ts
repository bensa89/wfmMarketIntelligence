import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { EventCalendarResponse } from '../types/intelligence';

export function useEventCalendar(full = false) {
  return useQuery<EventCalendarResponse>({
    queryKey: ['intelligence', 'events', full],
    queryFn: () => apiGet<EventCalendarResponse>(`/intelligence/events${full ? '?full=true' : ''}`),
    staleTime: 5 * 60 * 1000,
  });
}
