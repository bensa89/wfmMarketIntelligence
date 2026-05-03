import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchBenchmarkOverview,
  fetchCompetitorBenchmark,
  fetchCapabilityLeaderboard,
  recomputeAllBenchmarks,
  recomputeCompanyBenchmark,
} from '../api/benchmark';
import type { BenchmarkPeriodType } from '../types/benchmark';

export function useBenchmarkOverview(periodType: BenchmarkPeriodType = '30d') {
  return useQuery({
    queryKey: ['benchmark', 'overview', periodType],
    queryFn: () => fetchBenchmarkOverview(periodType),
  });
}

export function useCompetitorBenchmark(slug: string, periodType: BenchmarkPeriodType = '30d') {
  return useQuery({
    queryKey: ['benchmark', 'competitor', slug, periodType],
    queryFn: () => fetchCompetitorBenchmark(slug, periodType),
    enabled: Boolean(slug),
  });
}

export function useCapabilityLeaderboard(capKey: string | null, periodType: BenchmarkPeriodType = '30d') {
  return useQuery({
    queryKey: ['benchmark', 'leaderboard', capKey, periodType],
    queryFn: () => fetchCapabilityLeaderboard(capKey!, periodType),
    enabled: Boolean(capKey),
  });
}

export function useRecomputeBenchmarks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (periodType: BenchmarkPeriodType = '30d') => recomputeAllBenchmarks(periodType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmark'] });
    },
  });
}

export function useRecomputeCompanyBenchmark() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ companyId, periodType = '30d' }: { companyId: string; periodType?: BenchmarkPeriodType }) =>
      recomputeCompanyBenchmark(companyId, periodType),
    onSuccess: (_data, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['benchmark'] });
    },
  });
}