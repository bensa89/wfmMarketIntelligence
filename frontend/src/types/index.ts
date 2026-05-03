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
export type CrawlStatus = 'new' | 'known' | 'changed';

export interface Source {
  id: string;
  company_id: string;
  url: string;
  label: string | null;
  source_type: SourceType;
  is_active: boolean;
  crawl_status: CrawlStatus;
  content_hash: string | null;
  last_crawled_at: string | null;
  last_changed_at: string | null;
  created_at: string;
  discovered_pages_summary: Record<string, number>;
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
}

export interface DigestSignal {
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

export interface Digest {
  id: string;
  week_start: string;
  week_end: string;
  summary: string | null;
  key_signals: DigestSignal[];
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
  last_signal_relevance: number | null;
}

export type CrawlStep = 'fetching' | 'extracting' | 'analysing' | 'discovering';

export interface CrawlStartEvent {
  type: 'crawl_start';
  crawl_run_id: string;
  total: number;
}
export interface CrawlSourceStartEvent {
  type: 'source_start';
  crawl_run_id: string;
  source_id: string;
  url: string;
  index: number;
  total: number;
}
export interface CrawlStepEvent {
  type: 'step';
  crawl_run_id: string;
  source_id: string;
  step: CrawlStep;
}
export interface CrawlSourceDoneEvent {
  type: 'source_done';
  crawl_run_id: string;
  source_id: string;
  new_documents: number;
  skipped: number;
  errors: number;
}
export interface CrawlDoneEvent {
  type: 'crawl_done';
  crawl_run_id: string;
  sources_processed: number;
  total_new: number;
  total_errors: number;
}
export interface CrawlErrorEvent {
  type: 'error';
  crawl_run_id?: string;
  source_id: string | null;
  message: string;
}
export interface CrawlInitialStateEvent {
  type: 'initial_state';
  crawl_run_id: string;
  total: number;
  sources: CrawlRunSourceState[];
}
export interface CrawlReconnectCompleteEvent {
  type: 'reconnect_complete';
}
export interface CrawlNoActiveRunEvent {
  type: 'no_active_run';
}
export type CrawlEvent =
  | CrawlStartEvent
  | CrawlSourceStartEvent
  | CrawlStepEvent
  | CrawlSourceDoneEvent
  | CrawlDoneEvent
  | CrawlErrorEvent
  | CrawlInitialStateEvent
  | CrawlReconnectCompleteEvent
  | CrawlNoActiveRunEvent;

export interface CrawlRunSourceState {
  source_id: string;
  url: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  current_step?: string;
  new_documents: number;
  skipped: number;
  errors: number;
  error_message?: string;
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
}

export interface CrawlRun extends CrawlRunList {
  sources: CrawlRunSourceState[];
}

export interface SourceCrawlState {
  source_id: string;
  url: string;
  status: 'waiting' | 'running' | 'done' | 'error';
  currentStep?: CrawlStep;
  result?: { new_documents: number; skipped: number; errors: number };
  errorMessage?: string;
}

export interface CrawlStreamSummary {
  sources_processed: number;
  total_new: number;
  total_errors: number;
}

// --- Search / Source Candidates ---

export type SearchRunStatus = 'pending' | 'running' | 'done' | 'error';
export type SearchResultStatus = 'pending' | 'fetched' | 'skipped' | 'error';
export type SourceCandidateStatus = 'candidate' | 'approved' | 'rejected' | 'monitored';

export interface SearchQuery {
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

export interface SignalOverTimePoint {
  date: string;
  company_id: string;
  company_name: string;
  count: number;
}

export interface SignalTypeCount {
  signal_type: string;
  count: number;
}

export interface CompanySignalTypeCount {
  company_id: string;
  company_name: string;
  signal_type: string;
  count: number;
}

export interface SignalDistribution {
  by_type: SignalTypeCount[];
  by_company_and_type: CompanySignalTypeCount[];
}

export interface DedupResult {
  merged_count: number;
  removed_ids: string[];
  kept_signals: { id: string; title: string; relevance_score: number | null }[];
}

export interface DiscoveredPagesStats {
  total: number;
  new: number;
  changed: number;
  known: number;
}

export interface CrawlBriefing {
  id: string;
  crawl_run_id: string | null;
  content: string;
  generated_at: string;
}

export * from './benchmark';
