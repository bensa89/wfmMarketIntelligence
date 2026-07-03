export type CompanyType = 'competitor' | 'market_source' | 'own_company';

export interface ExternalCompanyView {
  id: string;
  summary: string | null;
  key_messages: string[];
  observed_capabilities: string[];
  observed_differentiators: string[];
  observed_target_markets: string[];
  tone_and_positioning: string | null;
  signal_count_used: number;
  generated_at: string | null;
  updated_at: string | null;
}

interface OwnCompanySignalItem {
  signal_id: string;
  title: string;
  topic: string;
  summary: string;
  why_it_matters: string;
  signal_type: string | null;
  relevance_score: number | null;
  source_url: string | null;
  source_domain: string | null;
  source_title: string | null;
  published_at: string | null;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  type: CompanyType;
  description: string | null;
  website: string | null;
  logo_path: string | null;
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
  type?: CompanyType;
  description?: string | null;
  website?: string | null;
}

export type SourceType = 'news' | 'blog' | 'product' | 'press' | 'jobs' | 'events';
export type CrawlStatus = 'new' | 'known' | 'changed';

export interface Source {
  id: string;
  company_id: string;
  url: string;
  label: string | null;
  source_type: SourceType;
  is_active: boolean;
  respect_robots_txt: boolean;
  discovery_depth: number | null;
  crawl_status: CrawlStatus;
  content_hash: string | null;
  last_crawled_at: string | null;
  last_changed_at: string | null;
  created_at: string;
  discovered_pages_summary: Record<string, number>;
  analysis_status: 'pending' | 'analysing' | 'analysed' | 'analysis_failed' | null;
}

export interface SourceCreate {
  company_id: string;
  url: string;
  label?: string | null;
  source_type: SourceType;
  is_active?: boolean;
  respect_robots_txt?: boolean;
}

export interface SourceUpdate {
  label?: string | null;
  source_type?: SourceType;
  is_active?: boolean;
  respect_robots_txt?: boolean;
  discovery_depth?: number | null;
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
  from_search: boolean;
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
  source_url: string | null;
  published_at: string | null;
  created_at: string;
  from_search: boolean;
  event_name: string | null;
  event_type: string | null;
}

interface DigestSignal {
  id: string;
  title: string;
  signal_type: SignalType;
  topic: string | null;
  summary: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  source_url: string | null;
  company_name: string | null;
}

export interface DigestSectionItem {
  signal_id: string;
  company: string | null;
  title: string;
  narrative: string | null;
  implication_for_us: string | null;
  movement_strength: 'weak' | 'relevant' | 'strong' | 'market_shaping' | null;
  source_url: string | null;
  source_domain: string | null;
  source_title: string | null;
  // own_company_communication fields
  topic?: string | null;
  summary?: string | null;
  why_it_matters?: string | null;
  signal_type?: string | null;
  relevance_score?: number | null;
  published_at?: string | null;
}

export interface EventCalendarItem {
  signal_id: string;
  event_name: string | null;
  event_date: string | null;
  event_location: string | null;
  event_type: string | null;
  company: string;
  source_url: string | null;
  is_new: boolean;
}

interface DigestSection {
  key: string;
  title: string;
  items: DigestSectionItem[];
  upcoming?: EventCalendarItem[];
  newly_discovered?: EventCalendarItem[];
  own_company_items?: OwnCompanySignalItem[];
}

export interface Digest {
  id: string;
  week_start: string;
  week_end: string;
  summary: string | null;
  key_signals: DigestSignal[];
  sections: DigestSection[];
  risks: import('./intelligence').RiskItem[];
  opportunities: import('./intelligence').RiskItem[];
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

type DiscoveredPageStatus = 'new' | 'known' | 'changed' | 'ignored';

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
  last_signal_relevance: number | null;
  analysis_status: string | null;
}

export interface SourceSearchResult {
  source: Source;
  matching_subsites: string[];
}

export type CrawlPhase = 'idle' | 'crawling' | 'analysing' | 'done';

export interface CrawlRunSourceState {
  source_id: string;
  url: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  current_step?: string;
  new_documents: number;
  skipped: number;
  errors: number;
  error_message?: string;
  fetch_ms?: number;
  extract_ms?: number;
  analyse_ms?: number;
  discover_ms?: number;
  discover_pages_crawled?: number;
  discover_pages_found?: number;
}

export interface CrawlRunList {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_sources: number;
  total_new: number;
  total_skipped: number;
  total_errors: number;
  total_analysis_errors: number;
}

export interface CrawlRun extends CrawlRunList {
  sources: CrawlRunSourceState[];
}

export interface CrawlStatusSource {
  id: string;
  crawl_run_id: string;
  source_id: string;
  url: string;
  status: 'pending' | 'running' | 'analysing' | 'completed' | 'failed' | 'skipped';
  current_step: string | null;
  new_documents: number;
  skipped: number;
  errors: number;
  error_message: string | null;
  fetch_ms: number | null;
  extract_ms: number | null;
  analyse_ms: number | null;
  discover_ms: number | null;
  discover_pages_crawled: number | null;
  discover_pages_found: number | null;
  analyse_docs_done: number;
  analyse_docs_total: number;
  analyse_current_url: string | null;
}

export interface CrawlStatusRun {
  id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  finished_at: string | null;
  total_sources: number;
  total_new: number;
  total_skipped: number;
  total_errors: number;
  total_analysis_errors: number;
  sources: CrawlStatusSource[];
}

export interface CrawlStatusQueuedRun {
  id: string;
  sources: { source_id: string; url: string }[];
}

export interface CrawlStatusResponse {
  active_run: CrawlStatusRun | null;
  queued_run: CrawlStatusQueuedRun | null;
}

// --- Search / Source Candidates ---

type SearchRunStatus = 'pending' | 'running' | 'done' | 'error';
type SearchResultStatus = 'pending' | 'fetched' | 'skipped' | 'error';
type SourceCandidateStatus = 'candidate' | 'approved' | 'rejected' | 'monitored';

interface SearchQuery {
  id: string;
  query_text: string;
  company_id: string | null;
  topic: string | null;
  search_intent: string;
  generated_at: string;
}

export interface SearchRun {
  id: string;
  search_query_id: string;
  executed_at: string;
  status: SearchRunStatus;
  result_count: number | null;
  error_message: string | null;
  query: SearchQuery | null;
}

export interface SearchResult {
  id: string;
  search_run_id: string;
  title: string | null;
  url: string;
  domain: string | null;
  snippet: string | null;
  discovered_at: string;
  relevance_score: number | null;
  processing_status: SearchResultStatus;
  linked_document_id: string | null;
}

export interface SourceCandidate {
  id: string;
  url: string;
  domain: string;
  title: string | null;
  snippet: string | null;
  found_via_query: string | null;
  company_id: string | null;
  source_type_guess: SourceType | null;
  relevance_score: number | null;
  status: SourceCandidateStatus;
  created_at: string;
}

export interface SourceCandidateApprove {
  label?: string;
  source_type: SourceType;
}

export interface SearchRunResult {
  companies_searched: number;
  results: unknown[];
}

// --- Stats ---

interface LastCrawlRunInfo {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_sources: number;
  total_errors: number;
  total_analysis_errors: number;
}

export interface LastCrawlSummary {
  crawl_run: LastCrawlRunInfo | null;
  new_signals: number;
  new_documents: number;
  high_relevance_signals: number;
  unanalysed_backlog: number;
}

export * from './benchmark';
