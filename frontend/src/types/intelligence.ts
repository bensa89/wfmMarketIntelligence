// frontend/src/types/intelligence.ts
import type { SignalType } from './index';

export type MovementStrength = 'weak' | 'relevant' | 'strong' | 'market_shaping';
export type VisibilityImpact = 'low' | 'medium' | 'high';
export type PeriodType = '7d' | '30d' | '90d' | 'quarter';
export type SignalClass =
  | 'product_capability_move'
  | 'positioning_move'
  | 'ecosystem_move'
  | 'thought_leadership_signal'
  | 'hiring_signal'
  | 'weak_signal'
  | 'market_expansion_move';

export interface SignalAssessment {
  id: string;
  signal_id: string;
  company_id: string;
  capability_primary: string | null;
  capability_secondary: string[];
  signal_class: SignalClass | null;
  evidence_strength: number | null;
  visibility_impact: VisibilityImpact | null;
  strategic_weight: number | null;
  movement_score: number | null;
  movement_strength: MovementStrength | null;
  confidence: number | null;
  strategic_intent_guess: string | null;
  gameplay_tags: string[];
  assessment_summary: string | null;
  implication_for_us: string | null;
  watch_items: string[];
  created_at: string;
  updated_at: string;
}

export interface SignalFeedItem {
  id: string;
  title: string;
  signal_type: SignalType;
  topic: string | null;
  summary: string | null;
  why_it_matters: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  published_at: string | null;
  created_at: string;
  company_id: string;
  company_name: string | null;
  company_slug: string | null;
  source_url: string | null;
  document_id: string;
  document_title: string | null;
  assessment: SignalAssessment | null;
}

export interface CompetitorMover {
  company_id: string;
  company_name: string;
  company_slug: string;
  avg_movement_score: number;
  signal_count: number;
  top_capability: string | null;
}

export interface HeatmapRow {
  company_id: string;
  company_name: string;
  capabilities: Record<string, number>;
}

export interface OverviewResponse {
  top_movers_7d: CompetitorMover[];
  top_movers_30d: CompetitorMover[];
  capability_heatmap: HeatmapRow[];
  recent_market_shaping: SignalFeedItem[];
  emerging_risks: string[];
  emerging_opportunities: string[];
}

export interface CapabilityCount {
  capability_key: string;
  count: number;
  avg_movement_score: number;
}

export interface TimelineEntry {
  signal_id: string;
  title: string;
  signal_type: SignalType;
  published_at: string | null;
  created_at: string;
  movement_strength: MovementStrength | null;
  movement_score: number | null;
  capability_primary: string | null;
}

export interface CompetitorSummary {
  id: string;
  company_id: string;
  period_type: PeriodType;
  period_start: string;
  period_end: string;
  strategic_posture: string | null;
  positioning_summary: string | null;
  top_capabilities: string[];
  capability_assessment: Array<{ key: string; label: string; activity_level: string; notes: string }>;
  top_risks: string[];
  top_opportunities: string[];
  watchpoints: string[];
  avg_movement_score: number | null;
  signal_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceResponse {
  competitor_profile: {
    id: string;
    name: string;
    slug: string;
    type: string;
    description: string | null;
    website: string | null;
    created_at: string;
  };
  summary_30d: CompetitorSummary | null;
  summary_90d: CompetitorSummary | null;
  recent_assessments: SignalFeedItem[];
  capability_distribution: CapabilityCount[];
  timeline_of_moves: TimelineEntry[];
}

export interface SignalsFeedResponse {
  items: SignalFeedItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SignalsFeedFilters {
  company_id?: string;
  capability?: string;
  signal_type?: string;
  movement_strength?: MovementStrength;
  min_confidence?: number;
  from_date?: string;
  to_date?: string;
  sort_by?: 'published_at' | 'movement_score' | 'confidence';
  page?: number;
  page_size?: number;
}
