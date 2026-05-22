import { apiGet, apiPost } from './client';
import type {
  BenchmarkOverviewResponse,
  CompetitorBenchmarkResponse,
  CapabilityLeaderboardResponse,
  CapabilityAssessmentsResponse,
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

export function recomputeAllBenchmarks(_periodType: BenchmarkPeriodType = '30d') {
  return apiPost<{ recomputed: number; period_type: string }>('/benchmark/recompute', null);
}

export function recomputeCompanyBenchmark(companyId: string, _periodType: BenchmarkPeriodType = '30d') {
  return apiPost<{ recomputed: number; company_id: string; period_type: string }>(
    `/benchmark/recompute/${companyId}`,
    null,
  );
}

export function fetchCapabilityAssessments(
  slug: string,
  capKey: string,
  periodType: BenchmarkPeriodType = '30d',
) {
  return apiGet<CapabilityAssessmentsResponse>(
    `/benchmark/competitors/${slug}/capabilities/${capKey}/assessments`,
    { period_type: periodType },
  );
}