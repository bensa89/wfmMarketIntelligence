import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { SourceSearchResult } from '../types';

export function useSourceSearch(query: string) {
  return useQuery<SourceSearchResult[]>({
    queryKey: ['sourceSearch', query],
    queryFn: () => apiGet<SourceSearchResult[]>('/sources/search', { q: query }),
    enabled: query.length >= 2,
  });
}
