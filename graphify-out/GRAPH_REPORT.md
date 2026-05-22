# Graph Report - .  (2026-05-22)

## Corpus Check
- 377 files · ~255,945 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1736 nodes · 2822 edges · 154 communities (143 shown, 11 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 439 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Scorecard Builder & KPI Engine|Scorecard Builder & KPI Engine]]
- [[_COMMUNITY_Capability Benchmark Aggregation|Capability Benchmark Aggregation]]
- [[_COMMUNITY_LLM Assessment Parser|LLM Assessment Parser]]
- [[_COMMUNITY_Multi-LLM Client Layer|Multi-LLM Client Layer]]
- [[_COMMUNITY_Weekly Digest Pipeline|Weekly Digest Pipeline]]
- [[_COMMUNITY_Web Discovery & Crawl Engine|Web Discovery & Crawl Engine]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_Intelligence Briefing Layer|Intelligence Briefing Layer]]
- [[_COMMUNITY_Crawl UI & Hooks|Crawl UI & Hooks]]
- [[_COMMUNITY_Scorecard UI Components|Scorecard UI Components]]
- [[_COMMUNITY_Signal Analysis Engine|Signal Analysis Engine]]
- [[_COMMUNITY_Project Docs & Infrastructure|Project Docs & Infrastructure]]
- [[_COMMUNITY_Signal Feed UI|Signal Feed UI]]
- [[_COMMUNITY_Benchmark Query Service|Benchmark Query Service]]
- [[_COMMUNITY_Product Concepts & Design Specs|Product Concepts & Design Specs]]
- [[_COMMUNITY_Module Cluster 15|Module Cluster 15]]
- [[_COMMUNITY_Module Cluster 16|Module Cluster 16]]
- [[_COMMUNITY_Module Cluster 17|Module Cluster 17]]
- [[_COMMUNITY_Module Cluster 18|Module Cluster 18]]
- [[_COMMUNITY_Module Cluster 19|Module Cluster 19]]
- [[_COMMUNITY_Module Cluster 20|Module Cluster 20]]
- [[_COMMUNITY_Module Cluster 21|Module Cluster 21]]
- [[_COMMUNITY_Module Cluster 22|Module Cluster 22]]
- [[_COMMUNITY_Module Cluster 23|Module Cluster 23]]
- [[_COMMUNITY_Module Cluster 24|Module Cluster 24]]
- [[_COMMUNITY_Module Cluster 25|Module Cluster 25]]
- [[_COMMUNITY_Module Cluster 26|Module Cluster 26]]
- [[_COMMUNITY_Module Cluster 27|Module Cluster 27]]
- [[_COMMUNITY_Module Cluster 28|Module Cluster 28]]
- [[_COMMUNITY_Module Cluster 29|Module Cluster 29]]
- [[_COMMUNITY_Module Cluster 30|Module Cluster 30]]
- [[_COMMUNITY_Module Cluster 31|Module Cluster 31]]
- [[_COMMUNITY_Module Cluster 32|Module Cluster 32]]
- [[_COMMUNITY_Module Cluster 33|Module Cluster 33]]
- [[_COMMUNITY_Module Cluster 34|Module Cluster 34]]
- [[_COMMUNITY_Module Cluster 35|Module Cluster 35]]
- [[_COMMUNITY_Module Cluster 37|Module Cluster 37]]
- [[_COMMUNITY_Module Cluster 38|Module Cluster 38]]
- [[_COMMUNITY_Module Cluster 39|Module Cluster 39]]
- [[_COMMUNITY_Module Cluster 40|Module Cluster 40]]
- [[_COMMUNITY_Module Cluster 41|Module Cluster 41]]
- [[_COMMUNITY_Module Cluster 42|Module Cluster 42]]
- [[_COMMUNITY_Module Cluster 43|Module Cluster 43]]
- [[_COMMUNITY_Module Cluster 44|Module Cluster 44]]
- [[_COMMUNITY_Module Cluster 45|Module Cluster 45]]
- [[_COMMUNITY_Module Cluster 46|Module Cluster 46]]
- [[_COMMUNITY_Module Cluster 47|Module Cluster 47]]
- [[_COMMUNITY_Module Cluster 48|Module Cluster 48]]
- [[_COMMUNITY_Module Cluster 50|Module Cluster 50]]
- [[_COMMUNITY_Module Cluster 51|Module Cluster 51]]
- [[_COMMUNITY_Module Cluster 52|Module Cluster 52]]
- [[_COMMUNITY_Module Cluster 54|Module Cluster 54]]
- [[_COMMUNITY_Module Cluster 55|Module Cluster 55]]
- [[_COMMUNITY_Module Cluster 56|Module Cluster 56]]
- [[_COMMUNITY_Module Cluster 57|Module Cluster 57]]
- [[_COMMUNITY_Module Cluster 58|Module Cluster 58]]
- [[_COMMUNITY_Module Cluster 59|Module Cluster 59]]
- [[_COMMUNITY_Module Cluster 63|Module Cluster 63]]
- [[_COMMUNITY_Module Cluster 64|Module Cluster 64]]
- [[_COMMUNITY_Module Cluster 65|Module Cluster 65]]
- [[_COMMUNITY_Module Cluster 66|Module Cluster 66]]
- [[_COMMUNITY_Module Cluster 68|Module Cluster 68]]
- [[_COMMUNITY_Module Cluster 73|Module Cluster 73]]
- [[_COMMUNITY_Module Cluster 74|Module Cluster 74]]
- [[_COMMUNITY_Module Cluster 75|Module Cluster 75]]
- [[_COMMUNITY_Module Cluster 85|Module Cluster 85]]
- [[_COMMUNITY_Module Cluster 86|Module Cluster 86]]
- [[_COMMUNITY_Module Cluster 87|Module Cluster 87]]
- [[_COMMUNITY_Module Cluster 88|Module Cluster 88]]
- [[_COMMUNITY_Module Cluster 90|Module Cluster 90]]
- [[_COMMUNITY_Module Cluster 108|Module Cluster 108]]
- [[_COMMUNITY_Module Cluster 109|Module Cluster 109]]
- [[_COMMUNITY_Module Cluster 110|Module Cluster 110]]
- [[_COMMUNITY_Module Cluster 111|Module Cluster 111]]
- [[_COMMUNITY_Module Cluster 112|Module Cluster 112]]
- [[_COMMUNITY_Module Cluster 114|Module Cluster 114]]
- [[_COMMUNITY_Module Cluster 116|Module Cluster 116]]
- [[_COMMUNITY_Module Cluster 127|Module Cluster 127]]
- [[_COMMUNITY_Module Cluster 128|Module Cluster 128]]
- [[_COMMUNITY_Module Cluster 129|Module Cluster 129]]
- [[_COMMUNITY_Module Cluster 130|Module Cluster 130]]
- [[_COMMUNITY_Module Cluster 131|Module Cluster 131]]
- [[_COMMUNITY_Module Cluster 153|Module Cluster 153]]

## God Nodes (most connected - your core abstractions)
1. `apiGet()` - 32 edges
2. `BenchmarkQueryService` - 30 edges
3. `ScorecardBuilder` - 25 edges
4. `discover_and_crawl()` - 22 edges
5. `BenchmarkAggregationService` - 20 edges
6. `Crawl Pipeline — fetcher → extractor → dedup → analyser → signals` - 20 edges
7. `run_crawl_source()` - 19 edges
8. `apiPost()` - 18 edges
9. `_inp()` - 18 edges
10. `compilerOptions` - 17 edges

## Surprising Connections (you probably didn't know these)
- `assess_signal()` --calls--> `type`  [INFERRED]
  backend/app/assessor/pipeline.py → frontend/package.json
- `Scorecard — Competitor Scorecard Specification` --conceptually_related_to--> `Fachliche Anforderung — Competitor Scorecard WFM Intelligence Tool`  [INFERRED]
  scorecard.md → # Fachliche Anforderung zur Umsetzung ei.md
- `Respect robots.txt Per-Source Toggle Plan (2026-05-05)` --references--> `Crawl Pipeline — fetcher → extractor → dedup → analyser → signals`  [INFERRED]
  docs/superpowers/plans/2026-05-05-respect-robots-txt-per-source.md → CLAUDE.md
- `SignalAssessment — LLM-based assessment of signals with capability mapping` --shares_data_with--> `Crawl Pipeline — fetcher → extractor → dedup → analyser → signals`  [INFERRED]
  DashboardsV1.md → CLAUDE.md
- `Web Search Ingestion Implementation Plan` --conceptually_related_to--> `Crawl Pipeline — fetcher → extractor → dedup → analyser → signals`  [INFERRED]
  docs/superpowers/plans/2026-04-19-websearch-ingestion.md → CLAUDE.md

## Communities (154 total, 11 thin omitted)

### Community 0 - "Scorecard Builder & KPI Engine"
Cohesion: 0.06
Nodes (52): _get_company(), _get_current_scorecard(), get_scorecard(), get_scorecard_explain(), get_scorecard_history(), recompute_all(), recompute_scorecard(), ScorecardBuilder (+44 more)

### Community 1 - "Capability Benchmark Aggregation"
Cohesion: 0.06
Nodes (42): BenchmarkAggregationService, get_period_bounds(), Return (period_start, period_end) for a period_type string., _bin(), compute_confidence(), compute_relative_strength(), compute_sub_scores(), determine_tier() (+34 more)

### Community 2 - "LLM Assessment Parser"
Cohesion: 0.05
Nodes (42): AssessmentLLMOutput, _extract_json(), normalize_cited_items(), _normalize_items(), parse_assessment_response(), parse_summary_response(), SummaryLLMOutput, assess_signal() (+34 more)

### Community 3 - "Multi-LLM Client Layer"
Cohesion: 0.06
Nodes (36): _call_claude(), call_llm(), _call_ollama(), _call_opencode(), _get_anthropic_client(), _get_opencode_client(), _build_prompt(), generate_intelligence_briefing() (+28 more)

### Community 4 - "Weekly Digest Pipeline"
Cohesion: 0.07
Nodes (42): build_candidate_dict(), query_candidates(), curate_section(), generate_intro_summary(), get_prev_signal_index(), Returns {signal_id: item_dict} for all items in previous digest sections., True if signal is new OR has improved movement_strength since last digest., should_include() (+34 more)

### Community 5 - "Web Discovery & Crawl Engine"
Cohesion: 0.08
Nodes (47): discover_and_crawl(), _extract_internal_links(), _get_robot_parser(), _is_article_content(), _is_article_url(), _is_child_path(), _save_document_only(), _update_page_relevance() (+39 more)

### Community 6 - "Frontend Dependencies"
Cohesion: 0.05
Nodes (42): dependencies, lucide-react, react, react-dom, react-markdown, react-router-dom, recharts, remark-gfm (+34 more)

### Community 7 - "Intelligence Briefing Layer"
Cohesion: 0.07
Nodes (32): BaseModel, get_crawl_status(), CompetitorSummaryRead, ContextRead, ContextUpdate, CrawlBriefingCreate, CrawlBriefingRead, CrawlQueuedRunStatus (+24 more)

### Community 8 - "Crawl UI & Hooks"
Cohesion: 0.05
Nodes (33): useAnalyseSource(), CrawlAnalysisDoneEvent, CrawlAnalysisPhaseDoneEvent, CrawlAnalysisPhaseStartEvent, CrawlAnalysisProgressEvent, CrawlAnalysisStartEvent, CrawlDiscoveryProgressEvent, CrawlDoneEvent (+25 more)

### Community 9 - "Scorecard UI Components"
Cohesion: 0.08
Nodes (25): Props, getCapabilityLabel(), useAssessSignal(), useSignalsFeed(), DEFAULT_FILTERS, SignalsFeedPage(), Props, CONFIG (+17 more)

### Community 10 - "Signal Analysis Engine"
Cohesion: 0.08
Nodes (31): _is_unable_to_analyze(), parse_llm_response(), SignalData, analyse_document(), _build_context_dict(), build_analysis_prompt(), _analyse_doc_worker(), _make_ctx() (+23 more)

### Community 11 - "Project Docs & Infrastructure"
Cohesion: 0.09
Nodes (35): backend/requirements.txt — Python Dependencies, Crawl Pipeline — fetcher → extractor → dedup → analyser → signals, CrawlRunSource Timing Columns, Decouple Analysis from Crawl — two-phase crawl+analysis separation pattern, Per-Source Discovery Depth Override, Proxmox LXC + GitHub Actions Deployment, respect_robots_txt — per-source toggle for robots.txt compliance, Server-Sent Events (SSE) for Crawl Progress (+27 more)

### Community 12 - "Signal Feed UI"
Cohesion: 0.09
Nodes (21): FilterBarProps, relevanceLevels, signalTypes, CrawlSummaryCardProps, ACCENT_COLORS, DeltaKpiCardProps, useActiveCrawlRun(), useCompanies() (+13 more)

### Community 13 - "Benchmark Query Service"
Cohesion: 0.10
Nodes (22): BenchmarkQueryService, get_capability_assessments(), get_capability_leaderboard(), get_competitor_strengths(), get_overview(), recompute_all(), recompute_company(), BenchmarkMatrixCell (+14 more)

### Community 14 - "Product Concepts & Design Specs"
Cohesion: 0.09
Nodes (31): Capability Benchmark, CapabilityDefinition — WFM capability dimensions used for competitor scoring, CompetitorScorecard — aggregated scorecard with dimension scores, top moves, risk flags, Competitor Workspace — V1 dashboard view for per-competitor deep-dive, Executive Overview — V1 dashboard view for high-level intelligence, Explainability / Auditierbarkeit — principle of traceable score contributions, IntelligenceBriefing — LLM-generated briefing summarising recent signal changes, IntelligenceBriefingPanel Component (+23 more)

### Community 15 - "Module Cluster 15"
Cohesion: 0.12
Nodes (19): apiDelete(), ApiError, apiPatch(), apiPut(), authHeader(), clearCredentials(), getCredentials(), hasCredentials() (+11 more)

### Community 16 - "Module Cluster 16"
Cohesion: 0.12
Nodes (21): useCreateCompany(), useDeleteCompany(), useUpdateCompanyDynamic(), useDeleteDiscoveredPage(), useToggleDiscoveredPage(), useCreateSource(), useDeleteSource(), useSources() (+13 more)

### Community 17 - "Module Cluster 17"
Cohesion: 0.08
Nodes (24): DIM_LABELS, DimensionScoreCard(), Props, DIMENSIONS, DimensionScoreGrid(), Props, Props, RiskFlagsPanel() (+16 more)

### Community 18 - "Module Cluster 18"
Cohesion: 0.08
Nodes (12): CrawlRunSource, enqueue_source(), Enqueue a source when no queued run exists — creates one., Enqueueing a second source appends to the existing queued run., Enqueueing a source already in the queue returns current position., test_crawl_run_source_has_analyse_progress_fields(), test_crawl_run_source_read_schema_has_analyse_progress(), test_crawl_status_running_run() (+4 more)

### Community 19 - "Module Cluster 19"
Cohesion: 0.10
Nodes (15): RelevanceBadgeProps, SignalCard(), SignalCardProps, chipStyles, iconMap, labelMap, SignalTypeIconProps, SignalFeedTableProps (+7 more)

### Community 20 - "Module Cluster 20"
Cohesion: 0.13
Nodes (18): useApproveCandidate(), useRejectCandidate(), useRunSearchAll(), useSearchResults(), useSearchRuns(), useSourceCandidates(), useSourceCandidates(), ApproveCandidateDialog() (+10 more)

### Community 21 - "Module Cluster 21"
Cohesion: 0.13
Nodes (17): useCompany(), useDeduplicate(), useDocument(), useRecomputeScorecard(), CompetitorDetail(), DocumentViewer(), SignalDocumentModal(), CapabilityStrengthPanel() (+9 more)

### Community 22 - "Module Cluster 22"
Cohesion: 0.22
Nodes (16): SearchResultStatus, SearchRunStatus, AnalysisStatus, SourceCandidate, SourceCandidateStatus, CrawlStatus, Source, SourceType (+8 more)

### Community 23 - "Module Cluster 23"
Cohesion: 0.14
Nodes (15): CapabilityStrengthMatrixProps, MatrixCellProps, TIER_BG, TIER_TEXT, TIER_CONFIG, TierBadge(), TierBadgeProps, BenchmarkMatrixCell (+7 more)

### Community 24 - "Module Cluster 24"
Cohesion: 0.15
Nodes (10): DateWithTooltip(), Props, Props, CLASS_LABELS, Props, TopMovesTimeline(), ScorecardTopMove, formatAbsolute() (+2 more)

### Community 25 - "Module Cluster 25"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 26 - "Module Cluster 26"
Cohesion: 0.19
Nodes (18): extract_content(), run_crawl_source(), Test that crawl_status is set to 'changed' when content changes.      Note: This, test_extract_content_from_html(), test_extract_content_published_at_none_when_missing(), test_extract_content_sets_published_at(), test_extract_same_content_same_hash(), test_extract_sets_hash_based_on_content() (+10 more)

### Community 27 - "Module Cluster 27"
Cohesion: 0.18
Nodes (15): build_dedup_prompt(), _content_excerpt(), deduplicate_signals(), _hash_dedup(), _llm_dedup_batched(), _merge_group(), _parse_merge_groups(), deduplicate() (+7 more)

### Community 28 - "Module Cluster 28"
Cohesion: 0.11
Nodes (10): Base, CompetitorScorecard, CrawlBriefing, WeeklyDigest, Document, IntelligenceBriefing, SearchQuery, SearchResult (+2 more)

### Community 29 - "Module Cluster 29"
Cohesion: 0.18
Nodes (13): useCompetitorWorkspace(), useScorecard(), useScorecardExplain(), useSignalFeedItem(), useSummarizeCompetitor(), CompetitorWorkspacePage(), Period, Props (+5 more)

### Community 30 - "Module Cluster 30"
Cohesion: 0.15
Nodes (15): AllNewDocsSection(), CrawlProgressPanel(), DiscoveredPagesExpander(), formatMs(), Props, SourceRow(), useDiscoveredPages(), useDocuments() (+7 more)

### Community 31 - "Module Cluster 31"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 32 - "Module Cluster 32"
Cohesion: 0.15
Nodes (11): ExpandablePanel(), Props, PipelineFlow(), PipelineStep, Props, PipelineSection(), Props, STEPS (+3 more)

### Community 33 - "Module Cluster 33"
Cohesion: 0.15
Nodes (17): POST /api/crawl/enqueue/{source_id} Endpoint, CrawlProgressPanel Component, Crawl Progress & Performance Design, Crawl Queue Design, crawl_run_sources Table, crawl_runs Table, GET /api/crawl/status Endpoint, Polling-Based Crawl/Analyse Status System (+9 more)

### Community 34 - "Module Cluster 34"
Cohesion: 0.15
Nodes (15): analyse_unanalysed_for_source(), analyse_source(), _cancel_running_crawl_runs(), crawl_all_sources(), crawl_single_source(), _crawl_source_worker(), _create_crawl_run(), start_crawl_background() (+7 more)

### Community 35 - "Module Cluster 35"
Cohesion: 0.14
Nodes (5): InternalCompanyContext, get_context(), _get_or_create_context(), update_context(), test_context_singleton_fields()

### Community 37 - "Module Cluster 37"
Cohesion: 0.14
Nodes (9): CompetitorSummary, RiskItem, CitedListProps, Props, postureColor(), postureLabel(), Props, StrategicPostureCard() (+1 more)

### Community 38 - "Module Cluster 38"
Cohesion: 0.14
Nodes (9): colorMap, COMPANY_COLORS, getCompanyColor(), CompanySignalHeatmapProps, TYPE_KEYS, DAY_OPTIONS, SignalsOverTimeChartProps, CompanySignalTypeCount (+1 more)

### Community 39 - "Module Cluster 39"
Cohesion: 0.20
Nodes (10): DiscoveredPage, DiscoveredPageStatus, _attach_summary(), list_sources(), search_sources(), SourceSearchResult, update_source(), DiscoveredPageRead (+2 more)

### Community 40 - "Module Cluster 40"
Cohesion: 0.16
Nodes (7): useOverview(), Props, Props, Props, OverviewPage(), CompetitorMover, OverviewResponse

### Community 41 - "Module Cluster 41"
Cohesion: 0.16
Nodes (8): useCompetitorBenchmark(), CapabilityCount, InfoTooltip(), Props, COLUMN_TOOLTIPS, PERIOD_OPTIONS, RelativeCapabilityStrengthPanel(), RelativeCapabilityStrengthPanelProps

### Community 42 - "Module Cluster 42"
Cohesion: 0.21
Nodes (10): CompetitorSummary, PeriodType, CrawlRun, CrawlRunSourceStatus, CrawlRunStatus, CrawlRunStep, MovementStrength, SignalClass (+2 more)

### Community 43 - "Module Cluster 43"
Cohesion: 0.27
Nodes (10): fetchBenchmarkOverview(), fetchCapabilityAssessments(), fetchCapabilityLeaderboard(), fetchCompetitorBenchmark(), recomputeAllBenchmarks(), recomputeCompanyBenchmark(), apiPost(), CapabilityAssessmentsResponse (+2 more)

### Community 44 - "Module Cluster 44"
Cohesion: 0.19
Nodes (9): useCapabilityAssessments(), CapabilityExplainDrawer(), CapabilityExplainDrawerProps, CapabilityModeContent(), CapabilityModeContentProps, getMomentumColor(), getMomentumLabel(), PERIOD_LABELS (+1 more)

### Community 45 - "Module Cluster 45"
Cohesion: 0.24
Nodes (8): useDigests(), useGenerateDigest(), formatDateDE(), getISOWeek(), MOVEMENT_COLOURS, WeeklyDigest(), Digest, DigestSectionItem

### Community 46 - "Module Cluster 46"
Cohesion: 0.28
Nodes (12): _a(), Build a minimal assessment-like object for routing tests., test_high_visibility_adds_market_impact_kpis(), test_hiring_overrides_base_activity_weight(), test_hiring_signal_routes_to_activity_and_momentum_with_correct_modifiers(), test_market_expansion_with_strong_evidence_adds_capability_at_reduced_weight(), test_market_expansion_without_strong_evidence_no_capability(), test_product_capability_move_routes_to_capability_and_market() (+4 more)

### Community 47 - "Module Cluster 47"
Cohesion: 0.18
Nodes (10): _extract_published_at(), ExtractionResult, _parse_date_str(), Parse an ISO-8601 date string into a naive UTC datetime., main(), One-off backfill: extract published_at from stored HTML for all Documents, then, test_extract_published_at_from_json_ld(), test_extract_published_at_from_og_meta() (+2 more)

### Community 48 - "Module Cluster 48"
Cohesion: 0.27
Nodes (9): _expand_key_signals(), generate_digest(), get_digest(), list_digests(), _to_digest_read(), DigestRead, DigestSection, DigestSectionItem (+1 more)

### Community 50 - "Module Cluster 50"
Cohesion: 0.24
Nodes (8): CapabilityLeaderboardDrawer(), CapabilityLeaderboardDrawerProps, ConfidenceIndicator(), ConfidenceIndicatorProps, StrengthDeltaIndicator(), StrengthDeltaIndicatorProps, useCapabilityLeaderboard(), BenchmarkPeriodType

### Community 51 - "Module Cluster 51"
Cohesion: 0.27
Nodes (7): TagListProps, useContextData(), useUpdateContext(), CompanyContext(), listFields, Context, ContextUpdate

### Community 52 - "Module Cluster 52"
Cohesion: 0.18
Nodes (10): dependencies, lucide-react, react-markdown, react-router-dom, @tanstack/react-query, devDependencies, autoprefixer, postcss (+2 more)

### Community 54 - "Module Cluster 54"
Cohesion: 0.22
Nodes (6): CAPABILITIES, CAPABILITY_KEYS, CapabilityMeta, Props, VISIBLE_CAPABILITIES, HeatmapRow

### Community 55 - "Module Cluster 55"
Cohesion: 0.42
Nodes (7): apiGet(), fetchBenchmarkScorecard(), fetchScorecard(), fetchScorecardExplain(), fetchScorecardHistory(), recomputeScorecard(), ScorecardPeriodType

### Community 56 - "Module Cluster 56"
Cohesion: 0.20
Nodes (9): SearchQuery, SearchResult, SearchResultStatus, SearchRun, SearchRunAllResult, SearchRunCompanyResult, SearchRunStatus, SourceCandidate (+1 more)

### Community 57 - "Module Cluster 57"
Cohesion: 0.31
Nodes (6): MarkdownViewerProps, BriefingPanel(), formatTimeAgo(), useGenerateBriefing(), useLatestBriefing(), CrawlBriefing

### Community 58 - "Module Cluster 58"
Cohesion: 0.20
Nodes (10): Crawl Priority by Source Recency, LLM Dashboard Briefing & Discovered Page Auto-Ignore, frontend/src/utils/dates.ts, Discovered Page Auto-Ignore Feature, last_signal_relevance Field on DiscoveredPage, LLM Dashboard Briefing Feature, published_at Extraction from HTML/LLM, Signal API Date Filter & Default Cutoff (+2 more)

### Community 59 - "Module Cluster 59"
Cohesion: 0.29
Nodes (5): _make_company_with_scorecard(), test_get_benchmark_returns_paginated(), test_get_history_returns_list(), test_get_scorecard_returns_scorecard(), test_recompute_returns_ack()

### Community 63 - "Module Cluster 63"
Cohesion: 0.39
Nodes (9): CapabilityExplainDrawer Component, DimensionScoreCard / DimensionScoreGrid Components, ScorecardBuilder, Scorecard Dimensions (capability_strength, market_impact, activity, customer_proof, momentum), Capability Benchmark Implementation Plan, Capability Strength Explainability & Panel Consolidation Plan, Competitor Logos Implementation Plan, Competitor Scorecard Backend Implementation Plan (+1 more)

### Community 64 - "Module Cluster 64"
Cohesion: 0.29
Nodes (5): Signal, SignalType, TSVectorType, DedupResult, SignalRead

### Community 65 - "Module Cluster 65"
Cohesion: 0.32
Nodes (6): fetch_url(), FetchResult, _check_playwright(), fetch_url_js(), test_fetch_url_returns_html_on_success(), test_fetch_url_returns_none_on_http_error()

### Community 66 - "Module Cluster 66"
Cohesion: 0.38
Nodes (5): Company, CompanyType, CompanyCreate, CompanyRead, CompanyUpdate

### Community 68 - "Module Cluster 68"
Cohesion: 0.33
Nodes (4): _build_briefing_prompt(), generate_briefing_content(), generate_briefing(), _run_crawl_background()

### Community 73 - "Module Cluster 73"
Cohesion: 0.33
Nodes (6): Signal Deduplication via LLM Merge, Signal Full-Text Search, Signal Deduplication Implementation Plan, Signal Deduplication Design Spec, Signal Full-Text Search Design Spec, Signal Timestamps Display Design Spec

### Community 74 - "Module Cluster 74"
Cohesion: 0.53
Nodes (5): CapabilityStrengthMatrix(), useBenchmarkOverview(), useRecomputeBenchmarks(), useBenchmarkScorecard(), CompetitorList()

### Community 75 - "Module Cluster 75"
Cohesion: 0.33
Nodes (6): GET /api/benchmark/capability-assessments Backend Endpoint, CapabilityExplainDrawer, Capability Strength Explainability & Panel Consolidation, CapabilityRadar (Removed), InfoTooltip, RelativeCapabilityStrengthPanel

### Community 85 - "Module Cluster 85"
Cohesion: 0.83
Nodes (4): DiscoveredPage Model, Discovery Heuristics, Intelligent Crawling & Discovery Implementation Plan, Intelligent Discovery Design Spec

### Community 86 - "Module Cluster 86"
Cohesion: 0.67
Nodes (3): DimensionRouter, route(), RoutingResult

### Community 87 - "Module Cluster 87"
Cohesion: 0.67
Nodes (4): GitHub Actions Deploy Workflow, Proxmox LXC Hosting + GitHub Actions Deploy, Proxmox LXC Container Infrastructure, GitHub Actions Self-Hosted Runner

### Community 88 - "Module Cluster 88"
Cohesion: 0.50
Nodes (4): Frontend /search Page, query_generator.py (Searcher), backend/app/searcher/ Module, Web Search Ingestion Design

### Community 110 - "Module Cluster 110"
Cohesion: 1.00
Nodes (3): Two-Column Intelligence Dashboard Layout, Intelligence Dashboard Redesign Implementation Plan, Intelligence Dashboard Implementation Plan

### Community 111 - "Module Cluster 111"
Cohesion: 1.00
Nodes (3): WeeklyDigest, Clickable Digest Signals Design Spec, Weekly Digest Redesign Spec

### Community 114 - "Module Cluster 114"
Cohesion: 0.67
Nodes (3): Frontend Implementation Plan (v0), V1 Intelligence Backend Implementation Plan, V1 Intelligence Frontend Implementation Plan

## Knowledge Gaps
- **275 isolated node(s):** `@tanstack/react-query`, `lucide-react`, `react-markdown`, `react-router-dom`, `@tailwindcss/typography` (+270 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `assess_signal()` connect `LLM Assessment Parser` to `Scorecard Builder & KPI Engine`, `Capability Benchmark Aggregation`, `Multi-LLM Client Layer`, `Frontend Dependencies`, `Signal Analysis Engine`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `call_llm()` connect `Multi-LLM Client Layer` to `LLM Assessment Parser`, `Weekly Digest Pipeline`, `Module Cluster 68`, `Signal Analysis Engine`, `Module Cluster 27`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `analyse_document()` connect `Signal Analysis Engine` to `LLM Assessment Parser`, `Multi-LLM Client Layer`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `BenchmarkQueryService` (e.g. with `Company` and `CompetitorCapabilityBenchmark`) actually correct?**
  _`BenchmarkQueryService` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ScorecardBuilder` (e.g. with `CompetitorScorecard` and `SignalAssessment`) actually correct?**
  _`ScorecardBuilder` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@tanstack/react-query`, `lucide-react`, `react-markdown` to the rest of the system?**
  _298 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Scorecard Builder & KPI Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.06398390342052314 - nodes in this community are weakly interconnected._