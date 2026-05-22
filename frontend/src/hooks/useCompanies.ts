import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiDelete, apiPostFormData } from '../api/client';
import type { Company, CompanyCreate, CompanyUpdate } from '../types';

export function useCompanies() {
  return useQuery<Company[]>({
    queryKey: ['companies'],
    queryFn: async () => {
      const data = await apiGet<Company[]>('/companies');
      console.log('useCompanies fetched:', data);
      return data;
    },
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
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['companies'] });
      await qc.refetchQueries({ queryKey: ['companies'] });
    },
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

export function useUpdateCompanyDynamic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, data }: { slug: string; data: CompanyUpdate }) => 
      apiPut<Company>(`/companies/${slug}`, data),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['companies'] });
      qc.invalidateQueries({ queryKey: ['companies', variables.slug] });
    },
  });
}

export function useDeleteCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => apiDelete(`/companies/${slug}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  });
}

export function useUploadCompanyLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, file }: { slug: string; file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiPostFormData<Company>(`/companies/${slug}/logo`, formData);
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['companies'] });
      qc.invalidateQueries({ queryKey: ['companies', variables.slug] });
    },
  });
}
