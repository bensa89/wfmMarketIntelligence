import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useCrawlStatus } from '../hooks/useCrawlStatus';
import { useLastCompletedCrawl } from '../hooks/useCrawlRuns';
import { useActiveCrawlRun } from '../hooks/useActiveCrawlRun';
import { useSignalsOverTime, useSignalDistribution } from '../hooks/useSignalStats';
import { useDocument } from '../hooks/useDocuments';
import { useOverview } from '../hooks/useOverview';

import TopSignalsPanel from '../components/dashboard/TopSignalsPanel';
import SignalsOverTimeChart from '../components/dashboard/SignalsOverTimeChart';
import SignalTypeDistribution from '../components/dashboard/SignalTypeDistribution';
import CompanySignalHeatmap from '../components/dashboard/CompanySignalHeatmap';
import SignalFeedTable from '../components/dashboard/SignalFeedTable';
import FilterBar from '../components/FilterBar';
import MarkdownViewer from '../components/MarkdownViewer';

import IntelligenceBriefingPanel from '../components/overview/IntelligenceBriefingPanel';
import OverviewKPIBar from '../components/overview/OverviewKPIBar';
import TopMoversList from '../components/overview/TopMoversList';
import CapabilityHeatmapV2 from '../components/overview/CapabilityHeatmapV2';
import MarketShapingFeed from '../components/overview/MarketShapingFeed';
import RisksOpportunitiesPanel from '../components/overview/RisksOpportunitiesPanel';
import EventTimelinePanel from '../components/overview/EventTimelinePanel';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import { ScorecardSignalDrawer } from '../components/scorecard/ScorecardSignalDrawer';

import { Play, Loader2 } from 'lucide-react';
import type { SignalType, Signal } from '../types';
import type { SignalFeedItem } from '../types/intelligence';
import { formatPublishedAt } from '../utils/dates';

export default function Dashboard() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [companyId, setCompanyId] = useState('');
  const [onlyNew, setOnlyNew] = useState(true);
  const [lastMonth, setLastMonth] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [selectedOverviewSignal, setSelectedOverviewSignal] = useState<SignalFeedItem | null>(null);
  const [selectedRiskSignalId, setSelectedRiskSignalId] = useState<string | null>(null);
  const { start: startCrawl, isRunning: isCrawlRunning, run: crawlRun, phase: crawlPhase } = useCrawlStatus();
  const { activeRun } = useActiveCrawlRun();
  const { lastCrawl } = useLastCompletedCrawl();
  const { data: allSignals } = useSignals({});
  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id: companyId || undefined,
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
    max_age_days: lastMonth ? 30 : undefined,
    q: searchQuery || undefined,
  });
  const { data: overTimeData } = useSignalsOverTime(14);
  const { data: distribution } = useSignalDistribution(companyId || undefined);
  const { data: overviewData } = useOverview();

  const lastCrawlTime = lastCrawl?.started_at ? new Date(lastCrawl.started_at) : null;

  const filteredSignals = onlyNew && lastCrawlTime
    ? signals?.filter((s) => new Date(s.created_at) >= lastCrawlTime!) ?? []
    : signals ?? [];

  const lastCrawlTimeStr = lastCrawl?.finished_at
    ? new Date(lastCrawl.finished_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : null;

  const showCrawlRunning = isCrawlRunning || activeRun !== null;

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-[12px] text-slate-500 mt-0.5">
            {allSignals?.length ?? '–'} Signale gesamt
            {lastCrawlTimeStr && ` · Letzter Crawl: ${lastCrawlTimeStr}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isCrawlRunning && (
            <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
              <Loader2 size={12} className="animate-spin" />
              Crawling...
            </span>
          )}
          <button
            onClick={() => startCrawl()}
            disabled={isCrawlRunning}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors flex items-center gap-1.5"
          >
            <Play size={12} />
            Crawl starten
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-5">
        {showCrawlRunning && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border bg-blue-50 text-blue-700 border-blue-200">
            <Link to="/admin/sources" className="underline hover:no-underline">Crawl läuft</Link>
            {' — '}{activeRun?.total_sources ?? '...'} Quellen werden verarbeitet
            {activeRun?.total_new != null && activeRun.total_new > 0 && ` · ${activeRun.total_new} neue Dokumente`}
          </div>
        )}
        {crawlPhase === 'done' && crawlRun && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border bg-emerald-50 text-emerald-700 border-emerald-200">
            Crawl abgeschlossen: {crawlRun.total_sources} Quellen verarbeitet
            {crawlRun.total_new > 0 && ` · ${crawlRun.total_new} neue Dokumente`}
          </div>
        )}

        {/* Zone 1: Übersicht */}
        <IntelligenceBriefingPanel />
        {overviewData && <OverviewKPIBar data={overviewData} />}

        {overviewData && (
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="col-span-1">
              <TopMoversList movers7d={overviewData.top_movers_7d} movers30d={overviewData.top_movers_30d} />
            </div>
            <div className="col-span-2">
              <CapabilityHeatmapV2 rows={overviewData.capability_heatmap} />
            </div>
          </div>
        )}

        {overviewData && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <MarketShapingFeed signals={overviewData.recent_market_shaping} onSelect={setSelectedOverviewSignal} />
            <RisksOpportunitiesPanel
              risks={overviewData.emerging_risks}
              opportunities={overviewData.emerging_opportunities}
              watchpoints={overviewData.emerging_watchpoints}
              onSelectSignal={setSelectedRiskSignalId}
            />
          </div>
        )}

        <div className="mb-4">
          <EventTimelinePanel />
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3 my-6">
          <div className="flex-1 border-t-2 border-dashed border-slate-200" />
          <span className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Signal Details & Analyse</span>
          <div className="flex-1 border-t-2 border-dashed border-slate-200" />
        </div>

        {/* Zone 2: Signal Details */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          <TopSignalsPanel
            signals={allSignals ?? []}
            lastCrawl={lastCrawl ?? null}
            maxItems={5}
            onSignalClick={setSelectedSignal}
          />
          <div className="space-y-4">
            {overTimeData && overTimeData.length > 0 && (
              <SignalsOverTimeChart data={overTimeData} />
            )}
            {distribution && <SignalTypeDistribution byType={distribution.by_type} />}
          </div>
        </div>

        {distribution && companies && (
          <div className="mb-4">
            <CompanySignalHeatmap data={distribution.by_company_and_type} companies={companies} />
          </div>
        )}

        <div className="mt-2">
          <FilterBar
            signalType={signalType}
            onSignalTypeChange={setSignalType}
            minRelevance={minRelevance}
            onMinRelevanceChange={setMinRelevance}
            companyId={companyId}
            onCompanyChange={setCompanyId}
            companies={companies}
            onlyNew={onlyNew}
            onOnlyNewChange={setOnlyNew}
            lastMonth={lastMonth}
            onLastMonthChange={setLastMonth}
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
          />
          {signalsLoading || companiesLoading ? (
            <div className="flex items-center gap-2 text-slate-400 text-[13px]">
              <Loader2 size={14} className="animate-spin" />
              Lade Signale...
            </div>
          ) : (
            <SignalFeedTable
              signals={filteredSignals}
              companies={companies ?? []}
              lastCrawl={lastCrawl ?? null}
              onSignalClick={setSelectedSignal}
            />
          )}
        </div>

        {selectedOverviewSignal && (
          <SignalDetailDrawer item={selectedOverviewSignal} onClose={() => setSelectedOverviewSignal(null)} />
        )}
        <ScorecardSignalDrawer signalId={selectedRiskSignalId} onClose={() => setSelectedRiskSignalId(null)} />
        {selectedSignal && (
          <SignalDocumentModal signal={selectedSignal} onClose={() => setSelectedSignal(null)} />
        )}
      </div>
    </div>
  );
}

function SignalDocumentModal({ signal, onClose }: { signal: Signal; onClose: () => void }) {
  const { data: doc, isLoading } = useDocument(signal.document_id);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="min-w-0 flex-1 mr-4">
            <h3 className="font-semibold text-slate-900 truncate">{signal.title}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {(() => {
                const { label, isUnknown } = formatPublishedAt(signal.published_at);
                return (
                  <span className={isUnknown ? 'italic text-slate-300' : ''}>{label}</span>
                );
              })()}
              {signal.source_url && (
                <> · <a href={signal.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Quelle</a></>
              )}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">
              Erfasst: {new Date(signal.created_at).toLocaleDateString('de-DE')}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-sm font-medium shrink-0">Schließen</button>
        </div>
        <div className="px-6 py-4">
          {isLoading ? (
            <p className="text-slate-400 text-sm">Dokument wird geladen...</p>
          ) : doc?.content_markdown ? (
            <MarkdownViewer content={doc.content_markdown} />
          ) : (
            <p className="text-slate-400 text-sm">Kein Dokumentinhalt verfügbar.</p>
          )}
        </div>
      </div>
    </div>
  );
}
