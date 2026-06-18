import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchBenchmarkOverview,
  fetchCompetitorBenchmark,
  fetchCapabilityLeaderboard,
  fetchCapabilityAssessments,
  recomputeAllBenchmarks,
} from '../api/benchmark';
import type { BenchmarkPeriodType, CapabilityAssessmentsResponse } from '../types/benchmark';

export function useBenchmarkOverview(periodType: BenchmarkPeriodType = '180d') {
  return useQuery({
    queryKey: ['benchmark', 'overview', periodType],
    queryFn: () => fetchBenchmarkOverview(periodType),
  });
}

export function useCompetitorBenchmark(slug: string, periodType: BenchmarkPeriodType = '180d') {
  return useQuery({
    queryKey: ['benchmark', 'competitor', slug, periodType],
    queryFn: () => fetchCompetitorBenchmark(slug, periodType),
    enabled: Boolean(slug),
  });
}

export function useCapabilityLeaderboard(capKey: string | null, periodType: BenchmarkPeriodType = '180d') {
  return useQuery({
    queryKey: ['benchmark', 'leaderboard', capKey, periodType],
    queryFn: () => fetchCapabilityLeaderboard(capKey!, periodType),
    enabled: Boolean(capKey),
  });
}

export function useRecomputeBenchmarks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (periodType: BenchmarkPeriodType = '180d') => recomputeAllBenchmarks(periodType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmark'] });
    },
  });
}

export function useCapabilityAssessments(
  slug: string,
  capKey: string | null,
  periodType: BenchmarkPeriodType,
  enabled: boolean,
) {
  return useQuery<CapabilityAssessmentsResponse>({
    queryKey: ['benchmark', 'capability-assessments', slug, capKey, periodType],
    queryFn: () => fetchCapabilityAssessments(slug, capKey!, periodType),
    enabled: enabled && Boolean(slug) && Boolean(capKey),
    staleTime: 5 * 60 * 1000,
  });
}