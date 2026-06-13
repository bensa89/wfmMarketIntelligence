import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { EventCalendarResponse } from '../types/intelligence';

export function useEventCalendar() {
  return useQuery<EventCalendarResponse>({
    queryKey: ['intelligence', 'events'],
    queryFn: () => apiGet<EventCalendarResponse>('/intelligence/events'),
    staleTime: 5 * 60 * 1000,
  });
}
