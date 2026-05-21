import { apiGet, apiPost } from './client';
import type {
  CompetitorScorecard, ScorecardHistoryItem, ScorecardExplain,
  BenchmarkScorecardView, ScorecardRecomputeAck, ScorecardPeriodType,
} from '../types/scorecard';

export function fetchScorecard(slug: string, periodType: ScorecardPeriodType) {
  return apiGet<CompetitorScorecard>(`/scorecards/${slug}`, { period_type: periodType });
}

export function fetchScorecardHistory(slug: string, periodType: ScorecardPeriodType, limit = 10) {
  return apiGet<ScorecardHistoryItem[]>(`/scorecards/${slug}/history`, {
    period_type: periodType,
    limit: String(limit),
  });
}

export function fetchScorecardExplain(slug: string, periodType: ScorecardPeriodType) {
  return apiGet<ScorecardExplain>(`/scorecards/${slug}/explain`, { period_type: periodType });
}

export function recomputeScorecard(slug: string) {
  return apiPost<ScorecardRecomputeAck>(`/scorecards/${slug}/recompute`, {});
}

export function fetchBenchmarkScorecard(periodType: ScorecardPeriodType, page = 1, pageSize = 20) {
  return apiGet<BenchmarkScorecardView>('/scorecards/benchmark', {
    period_type: periodType,
    page: String(page),
    page_size: String(pageSize),
  });
}
