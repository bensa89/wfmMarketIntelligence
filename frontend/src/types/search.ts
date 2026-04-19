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
  query?: SearchQuery;
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
  source_type_guess: import('./index').SourceType | null;
  relevance_score: number | null;
  status: SourceCandidateStatus;
  created_at: string;
}

export interface SearchRunAllResult {
  companies_searched: number;
  results: Array<{
    company_id: string;
    queries_generated: number;
    results_found: number;
    documents_created: number;
  }>;
}

export interface SearchRunCompanyResult {
  company_id: string;
  queries_generated: number;
  results_found: number;
  documents_created: number;
}
