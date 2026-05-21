export type ScorecardPeriodType = '30d' | '90d' | '180d';
export const SCORECARD_PERIOD_TYPES: ScorecardPeriodType[] = ['30d', '90d', '180d'];

export interface ScorecardKPIValue {
  value: number | null;
  contributing_ids: string[];
}

export interface ScorecardDimension {
  score: number | null;
  trend: 'rising' | 'stable' | 'declining' | null;
  kpis: Record<string, ScorecardKPIValue>;
}

export interface ScorecardTopMove {
  assessment_id: string;
  signal_id: string;
  title: string;
  movement_score: number;
  signal_class: string;
  published_at: string | null;
}

export interface ScorecardRiskFlag {
  assessment_id: string;
  signal_id: string;
  capability_key: string;
  movement_strength: string;
  title: string;
}

export interface ScorecardBenchmarkPosition {
  rank: number;
  percentile: number;
  total_competitors: number;
}

export interface CompetitorScorecard {
  id: string;
  company_id: string;
  period_type: ScorecardPeriodType;
  period_start: string;
  period_end: string;
  generated_at: string;
  overall_score: number | null;
  overall_trend: 'rising' | 'stable' | 'declining' | null;
  dimension_scores: Record<string, ScorecardDimension>;
  top_capabilities: Array<{ capability_key: string; score: number | null }>;
  top_moves: ScorecardTopMove[];
  risk_flags: ScorecardRiskFlag[];
  watchpoints: string[];
  benchmark_position: ScorecardBenchmarkPosition | null;
  contributing_assessment_ids: string[];
  is_current: boolean;
  scorecard_version: string | null;
  routing_version: string | null;
}

export interface ScorecardHistoryItem {
  id: string;
  overall_score: number | null;
  overall_trend: 'rising' | 'stable' | 'declining' | null;
  generated_at: string;
  scorecard_version: string | null;
}

export interface ScorecardExplainAssessment {
  assessment_id: string;
  signal_id: string;
  title: string;
  movement_score: number;
  signal_class: string;
}

export interface ScorecardExplainDimension {
  dimension: string;
  score: number | null;
  dimension_weight: number;
  effective_weight: number;
  weighted_contribution: number | null;
  assessment_count: number;
  top_contributing_assessments: ScorecardExplainAssessment[];
  kpi_detail: Record<string, ScorecardKPIValue>;
}

export interface ScorecardExplain {
  overall_score: number | null;
  dimension_breakdown: ScorecardExplainDimension[];
  null_dimensions: string[];
  score_formula: string;
  routing_version: string | null;
  scorecard_version: string | null;
}

export interface BenchmarkScorecardItem {
  company_id: string;
  slug: string;
  name: string;
  overall_score: number | null;
  rank: number;
  percentile: number;
  dimension_scores: Record<string, ScorecardDimension>;
  overall_trend: string | null;
  scorecard_version: string | null;
}

export interface BenchmarkScorecardView {
  items: BenchmarkScorecardItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  period_type: ScorecardPeriodType;
  capability_leaders: Record<string, { company_slug: string; score: number }>;
  highest_momentum: { company_slug: string; mom_period_delta: number } | null;
  threat_flags: Array<{ company_slug: string; capability: string; movement_strength: string }>;
}

export interface ScorecardRecomputeAck {
  status: string;
  company_slug: string;
  recomputed_periods: string[];
  scorecard_ids: Record<string, string>;
  generated_at: string;
}
