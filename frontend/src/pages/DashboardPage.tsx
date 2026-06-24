import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useSignals } from '../hooks/useSignals';
import { useCrawlStatus } from '../hooks/useCrawlStatus';
import { useLastCompletedCrawl } from '../hooks/useCrawlRuns';
import { useActiveCrawlRun } from '../hooks/useActiveCrawlRun';
import { useOverview } from '../hooks/useOverview';
import { useLastCrawlSummary } from '../hooks/useStats';

import IntelligenceBriefingPanel from '../components/overview/IntelligenceBriefingPanel';
import DashboardKPIRow from '../components/overview/DashboardKPIRow';
import TopMoversList from '../components/overview/TopMoversList';
import CapabilityHeatmapV2 from '../components/overview/CapabilityHeatmapV2';
import MarketShapingFeed from '../components/overview/MarketShapingFeed';
import RisksOpportunitiesPanel from '../components/overview/RisksOpportunitiesPanel';
import EventTimelinePanel from '../components/overview/EventTimelinePanel';
import SignalDetailModal from '../components/signals/SignalDetailModal';
import { ScorecardSignalModal } from '../components/scorecard/ScorecardSignalModal';

import { Play, Loader2 } from 'lucide-react';
import type { SignalFeedItem } from '../types/intelligence';

export default function DashboardPage() {
  const [selectedOverviewSignal, setSelectedOverviewSignal] = useState<SignalFeedItem | null>(null);
  const [selectedRiskSignalId, setSelectedRiskSignalId] = useState<string | null>(null);
  const { start: startCrawl, isRunning: isCrawlRunning, run: crawlRun, phase: crawlPhase } = useCrawlStatus();
  const { activeRun } = useActiveCrawlRun();
  const { lastCrawl } = useLastCompletedCrawl();
  const { data: allSignals } = useSignals({});
  const { data: overviewData } = useOverview();
  const { data: lastCrawlSummary } = useLastCrawlSummary();

  const lastCrawlTimeStr = lastCrawl?.finished_at
    ? new Date(lastCrawl.finished_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : null;

  const showCrawlRunning = isCrawlRunning || activeRun !== null;

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <div className="bg-white border-b border-slate-200 px-4 md:px-6 py-3 flex items-center justify-between flex-shrink-0">
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

      <div className="flex-1 overflow-auto px-4 md:px-6 py-5">
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
        <IntelligenceBriefingPanel onSelectSignal={setSelectedRiskSignalId} />
        {overviewData && lastCrawlSummary && (
          <DashboardKPIRow overview={overviewData} lastCrawl={lastCrawlSummary} />
        )}

        {overviewData && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <MarketShapingFeed
              signals7d={overviewData.recent_market_shaping_7d}
              signals30d={overviewData.recent_market_shaping_30d}
              signals90d={overviewData.recent_market_shaping_90d}
              onSelect={setSelectedOverviewSignal}
            />
            <EventTimelinePanel />
          </div>
        )}

        {overviewData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="md:col-span-1">
              <TopMoversList movers7d={overviewData.top_movers_7d} movers30d={overviewData.top_movers_30d} />
            </div>
            {/* Capability Heatmap is a dense table visualization — not useful on a phone screen, hidden below md */}
            <div className="hidden md:block md:col-span-2">
              <CapabilityHeatmapV2 rows7d={overviewData.capability_heatmap_7d} rows30d={overviewData.capability_heatmap_30d} />
            </div>
          </div>
        )}

        {overviewData && (
          <div className="mb-4">
            <RisksOpportunitiesPanel
              risks={overviewData.emerging_risks}
              opportunities={overviewData.emerging_opportunities}
              watchpoints={overviewData.emerging_watchpoints}
              onSelectSignal={setSelectedRiskSignalId}
            />
          </div>
        )}

        {selectedOverviewSignal && (
          <SignalDetailModal item={selectedOverviewSignal} onClose={() => setSelectedOverviewSignal(null)} />
        )}
        <ScorecardSignalModal signalId={selectedRiskSignalId} onClose={() => setSelectedRiskSignalId(null)} />
      </div>
    </div>
  );
}
