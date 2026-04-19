import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type {
  SearchRun,
  SearchResult,
  SourceCandidate,
  SearchRunResult,
  SourceCandidateApprove,
  SourceType,
} from '../types';

export function useRunSearchAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<SearchRunResult>('/search/run'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-runs'] });
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useRunSearchForCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (companyId: string) => apiPost<SearchRunResult>(`/search/run/${companyId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-runs'] });
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
      qc.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}

export function useSearchRuns(companyId?: string) {
  return useQuery({
    queryKey: ['search-runs', companyId],
    queryFn: () => {
      const params = companyId ? `?company_id=${companyId}` : '';
      return apiGet<SearchRun[]>(`/search/runs${params}`);
    },
  });
}

export function useSearchResults(runId?: string) {
  return useQuery({
    queryKey: ['search-results', runId],
    queryFn: () => {
      const params = runId ? `?run_id=${runId}` : '';
      return apiGet<SearchResult[]>(`/search/results${params}`);
    },
    enabled: !!runId,
  });
}

export function useSourceCandidates(status?: string, companyId?: string) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (companyId) params.set('company_id', companyId);
  const query = params.toString();

  return useQuery({
    queryKey: ['source-candidates', status, companyId],
    queryFn: () => apiGet<SourceCandidate[]>(`/source-candidates/${query ? `?${query}` : ''}`),
  });
}

export function useApproveCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SourceCandidateApprove }) =>
      apiPost<{ status: string; source_id: string }>(`/source-candidates/${id}/approve/`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
      qc.invalidateQueries({ queryKey: ['sources'] });
    },
  });
}

export function useRejectCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiPost<{ status: string }>(`/source-candidates/${id}/reject/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-candidates'] });
    },
  });
}
