import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchScorecard, fetchScorecardHistory, fetchScorecardExplain,
  recomputeScorecard, fetchBenchmarkScorecard,
} from '../api/scorecard';
import type { ScorecardPeriodType } from '../types/scorecard';

export function useScorecard(slug: string, periodType: ScorecardPeriodType) {
  return useQuery({
    queryKey: ['scorecard', slug, periodType],
    queryFn: () => fetchScorecard(slug, periodType),
    enabled: Boolean(slug),
    retry: false,         // 404 is valid — competitor has no scorecard yet
  });
}

export function useScorecardHistory(slug: string, periodType: ScorecardPeriodType) {
  return useQuery({
    queryKey: ['scorecard', 'history', slug, periodType],
    queryFn: () => fetchScorecardHistory(slug, periodType),
    enabled: Boolean(slug),
  });
}

export function useScorecardExplain(slug: string, periodType: ScorecardPeriodType, enabled: boolean) {
  return useQuery({
    queryKey: ['scorecard', 'explain', slug, periodType],
    queryFn: () => fetchScorecardExplain(slug, periodType),
    enabled: Boolean(slug) && enabled,  // lazy — only fetch when drawer opens
    retry: false,
  });
}

export function useRecomputeScorecard(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => recomputeScorecard(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scorecard', slug] });
    },
  });
}

export function useBenchmarkScorecard(periodType: ScorecardPeriodType, page = 1) {
  return useQuery({
    queryKey: ['scorecard', 'benchmark', periodType, page],
    queryFn: () => fetchBenchmarkScorecard(periodType, page),
  });
}
