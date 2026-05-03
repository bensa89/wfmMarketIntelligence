import { apiGet, apiPost } from './client';
import type {
  BenchmarkOverviewResponse,
  CompetitorBenchmarkResponse,
  CapabilityLeaderboardResponse,
  BenchmarkPeriodType,
} from '../types/benchmark';

export function fetchBenchmarkOverview(periodType: BenchmarkPeriodType = '30d') {
  return apiGet<BenchmarkOverviewResponse>('/benchmark/overview', { period_type: periodType });
}

export function fetchCompetitorBenchmark(slug: string, periodType: BenchmarkPeriodType = '30d') {
  return apiGet<CompetitorBenchmarkResponse>(`/benchmark/competitors/${slug}`, { period_type: periodType });
}

export function fetchCapabilityLeaderboard(capKey: string, periodType: BenchmarkPeriodType = '30d') {
  return apiGet<CapabilityLeaderboardResponse>(`/benchmark/capabilities/${capKey}`, { period_type: periodType });
}

export function recomputeAllBenchmarks(periodType: BenchmarkPeriodType = '30d') {
  return apiPost<{ recomputed: number; period_type: string }>('/benchmark/recompute', null);
}

export function recomputeCompanyBenchmark(companyId: string, periodType: BenchmarkPeriodType = '30d') {
  return apiPost<{ recomputed: number; company_id: string; period_type: string }>(
    `/benchmark/recompute/${companyId}`,
    null,
  );
}