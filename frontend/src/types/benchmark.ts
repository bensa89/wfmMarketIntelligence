export type BenchmarkTier = 'leader' | 'strong' | 'emerging' | 'weakly_evidenced';
export type BenchmarkPeriodType = '30d' | '90d' | '180d';

export interface BenchmarkSubScores {
  capability_depth: number;
  execution_momentum: number;
  market_proof: number;
  strategic_focus: number;
  evidence_coverage: number;
}

export interface CompetitorBrief {
  id: string;
  name: string;
  slug: string;
}

export interface BenchmarkMatrixCell {
  score: number;
  tier: BenchmarkTier;
  confidence: number;
  rank: number | null;
  momentum_score: number;
}

export interface BenchmarkOverviewResponse {
  period_type: BenchmarkPeriodType;
  period_start: string;
  period_end: string;
  capabilities: string[];
  competitors: CompetitorBrief[];
  matrix: Record<string, Record<string, BenchmarkMatrixCell>>;
}

export interface CompetitorBenchmarkDetail {
  capability_key: string;
  label: string;
  relative_strength_score: number;
  prev_period_strength_score: number | null;
  strength_delta: number | null;
  tier: BenchmarkTier;
  peer_rank: number | null;
  peer_percentile: number | null;
  confidence: number;
  sub_scores: BenchmarkSubScores;
  source_signal_count: number;
  summary_reason: string | null;
}

export interface CompetitorBenchmarkResponse {
  competitor: CompetitorBrief;
  period_type: BenchmarkPeriodType;
  capabilities: CompetitorBenchmarkDetail[];
  strongest_capabilities: string[];
  weakest_evidenced_capabilities: string[];
}

export interface LeaderboardEntry {
  company_id: string;
  company_name: string;
  slug: string;
  score: number;
  tier: BenchmarkTier;
  confidence: number;
  rank: number;
  momentum_score: number;
  strength_delta: number | null;
  summary_reason: string | null;
}

export interface CapabilityLeaderboardResponse {
  capability_key: string;
  label: string;
  period_type: BenchmarkPeriodType;
  leaderboard: LeaderboardEntry[];
  strongest_competitor: LeaderboardEntry | null;
  fastest_riser: LeaderboardEntry | null;
}