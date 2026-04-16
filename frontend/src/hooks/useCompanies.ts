import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut } from '../api/client';
import type { Company, CompanyCreate, CompanyUpdate } from '../types';

export function useCompanies() {
  return useQuery<Company[]>({
    queryKey: ['companies'],
    queryFn: () => apiGet<Company[]>('/companies'),
  });
}

export function useCompany(slug: string) {
  return useQuery<Company>({
    queryKey: ['companies', slug],
    queryFn: () => apiGet<Company>(`/companies/${slug}`),
    enabled: !!slug,
  });
}

export function useCreateCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CompanyCreate) => apiPost<Company>('/companies', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  });
}

export function useUpdateCompany(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CompanyUpdate) => apiPut<Company>(`/companies/${slug}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['companies'] });
      qc.invalidateQueries({ queryKey: ['companies', slug] });
    },
  });
}
