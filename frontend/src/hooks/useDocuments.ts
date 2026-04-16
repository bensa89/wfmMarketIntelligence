import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { Document } from '../types';

export function useDocuments(sourceId?: string) {
  const params = sourceId ? { source_id: sourceId } : undefined;
  return useQuery<Document[]>({
    queryKey: ['documents', params],
    queryFn: () => apiGet<Document[]>('/documents', params),
  });
}

export function useDocument(id: string) {
  return useQuery<Document>({
    queryKey: ['documents', id],
    queryFn: () => apiGet<Document>(`/documents/${id}`),
    enabled: !!id,
  });
}
