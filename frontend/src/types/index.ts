export type CompanyType = 'competitor' | 'market_source';

export interface Company {
  id: string;
  name: string;
  slug: string;
  type: CompanyType;
  description: string | null;
  website: string | null;
  created_at: string;
}

export interface CompanyCreate {
  name: string;
  slug: string;
  type: CompanyType;
  description?: string | null;
  website?: string | null;
}

export interface CompanyUpdate {
  name?: string;
  description?: string | null;
  website?: string | null;
}

export type SourceType = 'news' | 'blog' | 'product' | 'press' | 'jobs';

export interface Source {
  id: string;
  company_id: string;
  url: string;
  label: string | null;
  source_type: SourceType;
  is_active: boolean;
  last_crawled_at: string | null;
  created_at: string;
}

export interface SourceCreate {
  company_id: string;
  url: string;
  label?: string | null;
  source_type: SourceType;
  is_active?: boolean;
}

export interface SourceUpdate {
  label?: string | null;
  source_type?: SourceType;
  is_active?: boolean;
}

export interface Document {
  id: string;
  source_id: string;
  url: string;
  title: string | null;
  content_markdown: string | null;
  published_at: string | null;
  crawled_at: string;
  content_hash: string | null;
  is_analysed: boolean;
}

export type SignalType =
  | 'product_update'
  | 'ai_announcement'
  | 'partnership'
  | 'positioning_change'
  | 'target_market_change'
  | 'event_or_thought_leadership'
  | 'hiring_signal'
  | 'other';

export interface Signal {
  id: string;
  document_id: string;
  company_id: string;
  title: string;
  signal_type: SignalType;
  topic: string | null;
  summary: string | null;
  why_it_matters: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  published_at: string | null;
  created_at: string;
}

export interface Digest {
  id: string;
  week_start: string;
  week_end: string;
  summary: string | null;
  key_signals: string[];
  generated_at: string;
  is_published: boolean;
}

export interface Context {
  id: string;
  company_name: string | null;
  short_description: string | null;
  target_industries: string[];
  target_segments: string[];
  core_capabilities: string[];
  strategic_priorities: string[];
  differentiators: string[];
  relevant_competitive_areas: string[];
  non_focus_areas: string[];
  updated_at: string;
}

export interface ContextUpdate {
  company_name?: string | null;
  short_description?: string | null;
  target_industries?: string[];
  target_segments?: string[];
  core_capabilities?: string[];
  strategic_priorities?: string[];
  differentiators?: string[];
  relevant_competitive_areas?: string[];
  non_focus_areas?: string[];
}

export interface CrawlResult {
  sources_processed: number;
  results: unknown[];
}

export interface CrawlSingleResult {
  source_id: string;
  document_id?: string;
  status: string;
}

export type DiscoveredPageStatus = 'new' | 'known' | 'changed' | 'ignored';

export interface DiscoveredPage {
  id: string;
  source_id: string;
  url: string;
  title: string | null;
  depth: number;
  status: DiscoveredPageStatus;
  is_active: boolean;
  content_hash: string | null;
  discovered_at: string;
  last_crawled_at: string | null;
  last_changed_at: string | null;
}
